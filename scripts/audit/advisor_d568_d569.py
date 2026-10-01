#!/usr/bin/env python3
"""حارسُ D568 · D569: حلولُ المستشار (البديلُ الأفضل، والتركيزُ على القيادية) وذاكرتُه ومراقبةُ شروطه —
بأرقامٍ معلومةِ الجواب.

    python3 scripts/audit/advisor_d568_d569.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import advisor_solutions as S
from app.services import advisor as A
from app.services import advisor_memory as M

ROWS = [
    {"symbol": "1111", "name": "ضعيفة", "sector": "الأغذية", "decision": "تجنّب", "finance_score": 45, "fair_value_upside_pct": -10, "dividend_yield": 1, "sharia": "COMPLIANT", "price": 20},
    {"symbol": "2222", "name": "قوية", "sector": "الأغذية", "decision": "شراء", "finance_score": 82, "fair_value_upside_pct": 15, "dividend_yield": 5, "sharia": "COMPLIANT", "price": 50},
    {"symbol": "3333", "name": "قوية غير شرعية", "sector": "الأغذية", "decision": "شراء", "finance_score": 90, "fair_value_upside_pct": 20, "dividend_yield": 6, "sharia": "NON_COMPLIANT", "price": 40},
    {"symbol": "4444", "name": "من قطاعٍ آخر", "sector": "البنوك", "decision": "شراء", "finance_score": 95, "fair_value_upside_pct": 25, "dividend_yield": 6, "sharia": "COMPLIANT", "price": 70},
]
alts = S.alternatives("1111", ROWS)
check([a["symbol"] for a in alts] == ["2222"] and alts[0]["vs"] > 8,
      "١ البديل: من القطاع نفسِه، شرعيٌّ لشركةٍ شرعية، و«شراء»، ودرجتُه أعلى بوضوح", str([(a["symbol"], a["quality"]) for a in alts]))
check(S.alternatives("2222", ROWS) == [], "٢ لا بديلَ أفضلَ لقويّةٍ — البقاءُ أحياناً هو الحلّ")
PEERS = [{"symbol": "4348", "premium": -38.7, "yield": 7.64, "nav_change": 1.7}, {"symbol": "4330", "premium": -52.4, "yield": 7.14, "nav_change": -5.9},
         {"symbol": "4342", "premium": -25.6, "yield": 9.2, "nav_change": -0.6}, {"symbol": "4340", "premium": -7.8, "yield": 6.92, "self": True}]
ra = S.reit_alternatives({"premium": -7.8, "yield": 6.92}, PEERS)
check([p["symbol"] for p in ra] == ["4348", "4342"], "٣ بديلُ الريت: أعمقُ خصماً بـ15 نقطة، بعائدٍ لا يقلّ، وصافي أصولٍ لم يهبط (الرياض ريت −5.9٪ يُستبعد)", str(ra))
check(S.wanted_count("أكتفي بثماني شركات") == 8 and S.wanted_count("قلّلها إلى 6") == 6 and S.wanted_count("قلل العدد", 10) == 10,
      "٤ العددُ المطلوب من السؤال")
ITEMS = [{"symbol": s, "name": s, "market_value": mv, "target_weight": tw, "current_weight": cw, "invested": inv, "cap": cap}
         for s, mv, tw, cw, inv, cap in (("2222", 9000, 10, 3, 8000, 50e9), ("1111", 1000, 3, 0.3, 1500, 1e9),
                                         ("3333", 2000, 5, 0.6, 1800, 2e9), ("4444", 9000, 12, 3, 7000, 90e9))]
plan = S.consolidate(ITEMS, ROWS, 2, 300000)
ex = [x["symbol"] for x in plan["exits"]]
keep = {k["symbol"]: k["new_target"] for k in plan["keep"]}
check(ex[0] == "3333" and set(ex) == {"3333", "1111"} and set(keep) == {"2222", "4444"}
      and abs(sum(keep.values()) - 30) < 0.05 and abs(plan["realized"] - ((1000 - 1500) + (2000 - 1800))) < 0.01,
      "٥ التركيز: غيرُ الشرعيّ يخرج أوّلاً ثمّ الأضعف، والقياديةُ تبقى، ومجموعُ الأوزان محفوظ، وما يُثبَّت محسوب",
      f"يخرج {ex} · يبقى {keep} · {plan['realized']}")
# الاستبدالُ حلٌّ في الموقف
F = {"symbol": "1111", "name": "ضعيفة", "held": True, "value": 1000, "price": 20, "decision": "تجنّب", "fin": 45,
     "target": 3, "remaining": 500, "capital": 300000, "alternatives": alts}
st = A.stance(F)
check(st["action"] == "استبدل" and st["replace_with"]["symbol"] == "2222" and st["swap"]["shares"] == 20,
      "٦ الحلُّ لا التحليلُ وحده: شركةٌ ضعيفةٌ لها بديلٌ أفضل ⇒ «استبدل» بالمبلغ والأسهم", str(st.get("swap")))
plan3 = S.consolidate(ITEMS, ROWS, 4, 300000, leaders_only=True)
check(plan3["after"] == 4 and not plan3["exits"], "٥ب وإن قلّت القياديةُ عن ثلاث لا تُفرَّغ المحفظة — يُعمل بالعدد",
      f"{plan3['before']} ⇒ {plan3['after']}")
ITEMS3 = ITEMS + [{"symbol": "6666", "name": "قيادية ثالثة", "market_value": 5000, "target_weight": 6, "invested": 4000, "cap": 40e9}]
ROWS3 = ROWS + [{"symbol": "6666", "name": "قيادية ثالثة", "sector": "الطاقة", "decision": "انتظار", "finance_score": 60, "sharia": "COMPLIANT", "price": 30}]
plan4 = S.consolidate(ITEMS3, ROWS3, 5, 300000, leaders_only=True)
check(plan4["after"] == 3 and {k["symbol"] for k in plan4["keep"]} == {"2222", "4444", "6666"},
      "٥ج «الاكتفاءُ بالقيادية»: تبقى القياديةُ الثلاث وحدها، ويخرج غيرُها", f"{plan4['before']} ⇒ {plan4['after']}")
src_a = (ROOT / "backend/app/services/advisor.py").read_text(encoding="utf-8")
check("لا تُخرج شركةً ليست في «يخرج»" in src_a and 'if float(it.get("market_value") or 0) > 0]' in src_a,
      "٥د النموذجُ لا يُخرج إلا من في الخطة، والمراكزُ المُغلقةُ لا تُعدّ قبل حساب العدد")
check('r["decision"] = dl' in src_a and "analyze_company(f\"{sym}.SR\"" in src_a,
      "٥هـ D570 قرارُ كلّ مركزٍ في الخطة من التحليل الحيّ لا من مخزن الفرز")
# مركزٌ مُغلقٌ (قيمته صفر) لا يُعدّ، والقياديةُ بحجمها لا بقرارها
plan2 = S.consolidate(ITEMS + [{"symbol": "5555", "name": "مغلق", "market_value": 0, "target_weight": 0, "cap": 1e9}], ROWS, 2, 300000)
check(plan2["before"] == 4 and all(x["symbol"] != "5555" for x in plan2["exits"]) and all(x.get("note") for x in plan2["exits"]),
      "٦ب المركزُ المُغلقُ لا يُعدّ، ولكلّ خارجٍ سببٌ مكتوب")
SADV = {"name": "سدافكو", "held": True, "value": 4045.8, "invested": 4904.9, "decision": "شراء",
        "alternatives": [{"symbol": "2286", "name": "المطاحن الرابعة", "quality": 91.2, "base_quality": 71.9, "decision": "شراء"}]}
v = S.swap_verdict(SADV, {"action": "انتظر الشرط ثمّ أضف على دفعات"}, {"2286", "2270"})
check(v["الحكم"].startswith("احتفظ الآن") and "خسارة 859" in v["كلفة التبديل"] and v["تملكه أصلاً"].startswith("نعم"),
      "٦ج حكمُ الاستبدال محسوب: فارقٌ 19 دون الحدّ وقرارُها شراء ⇒ احتفظ مع شرطٍ يقلبه، وكلفةُ التبديل، والبديلُ مملوكٌ أصلاً", v["الحكم"])
v2 = S.swap_verdict({**SADV, "decision": "تجنّب"}, {"action": "استبدل"}, set())
check(v2["الحكم"].startswith("استبدل"), "٦د الشركةُ الضعيفة ⇒ «استبدل» صريحاً")
check(A.portfolio_intent("أريد تقليل عدد الشركات والاكتفاء بالقيادية") and A.wants_alternatives("هل لها بديل أفضل؟")
      and A.intent("ما الشركات التي أتخلص منها؟"), "٧ نيّةُ الهيكلة والبدائل تصل المستشار")

# الذاكرةُ والمراقبة — سدافكو كما نُصح المالك
SAD = {"symbol": "2270", "name": "سدافكو", "held": True, "qty": 22, "value": 4045.8, "price": 183.9, "decision": "شراء",
       "rsi": 19.9, "trend": "هابط", "sma200": 216.05, "w52_low": 183.9, "eps_g": -24.9, "target": 3.5, "remaining": 7548.92,
       "capital": 331277.74, "results_due": "2026-10-30",
       "next_q": {"as_of": "2026-09-30", "net_income": 138.5e6, "mape": 17.2}}
st = A.stance(SAD)
a = M.fresh(SAD, st, 1)
check([t["status"] for t in a["tranches"]] == ["pending"] * 3 and all(t.get("cond") for t in a["tranches"]),
      "٨ تُحفظ النصيحةُ ولكلّ دفعةٍ شرطٌ آليّ")
a, ev = M.evaluate(a, {"price": 182, "qty": 22, "results": ["2026-06-30"]}, "2026-10-10")
check(not ev and a["tranches"][0]["status"] == "pending", "٩ لا شيءَ تغيّر ⇒ لا إزعاج")
a, ev = M.evaluate(a, {"price": 190, "qty": 22, "results": ["2026-06-30", "2026-09-30"], "ni_latest": 150e6}, "2026-10-28")
check(a["tranches"][0]["status"] == "met" and any("تحقّق شرطُ الدفعة 1" in e for e in ev),
      "١٠ صدرت النتائجُ فوق التوقّع ⇒ «تحقّق شرطُ الدفعة 1» بمبلغها وأسهمها بسعر اليوم", " | ".join(ev))
a, ev = M.evaluate(a, {"price": 190, "qty": 35, "results": ["2026-09-30"], "ni_latest": 150e6}, "2026-10-29")
check(a["tranches"][0]["status"] == "done" and any("نُفّذت الدفعة 1" in e for e in ev),
      "١١ اشترى المالكُ 13 سهماً ⇒ «نُفّذت الدفعة 1» — الخطةُ تتواكب مع ما فعله", " | ".join(ev))
b = M.fresh(SAD, st, 1)
b, ev = M.evaluate(b, {"price": 180, "qty": 22, "results": ["2026-09-30"], "ni_latest": 90e6}, "2026-10-28")
check(all(t["status"] == "paused" for t in b["tranches"]) and any("دون توقّع التطبيق" in e for e in ev),
      "١٢ نتائجُ دون التوقّع ⇒ تتوقّف الدفعاتُ المعلّقة ويُنبَّه المالك", " | ".join(ev))
c = M.fresh(SAD, st, 1)
c, ev = M.evaluate(c, {"price": 165, "qty": 22, "results": []}, "2026-10-05")
check(c["tranches"][2]["status"] == "met", "١٣ بلغ السعرُ مستوى الدفعة الثالثة (165.51) ⇒ تحقّق شرطُها")
R = {"symbol": "4340", "name": "الراجحي ريت", "held": True, "qty": 1007, "value": 7784, "price": 7.73, "decision": "شراء", "trend": "هابط",
     "target": 2.8, "remaining": 1491.67, "capital": 331277.74, "is_reit": True, "sma200": 8.08,
     "reit": {"nav": 8.385, "premium": -7.8, "trend": "صاعد", "nav_change": 2.6, "last_amount": 0.135}}
r = M.fresh(R, A.stance(R), 1)
check(r["tranches"][0]["status"] == "met", "١٤ دفعةُ «الآن» جاهزةٌ من يومها")
r, ev = M.evaluate(r, {"price": 7.7, "qty": 1007, "reit": {"last_amount": 0.12, "prev_amount": 0.135, "nav": 8.4}}, "2026-12-05")
check(all(t["status"] == "paused" for t in r["tranches"]) and any("خفّض التوزيع" in e for e in ev),
      "١٥ خفّض الريتُ توزيعَه ⇒ تتوقّف الدفعات ويُنبَّه المالك", " | ".join(ev))
old = M.fresh(SAD, st, 1); old["at"] = "2026-01-01"
old, ev = M.evaluate(old, {"price": 180, "qty": 22}, "2026-10-01")
check(old["status"] == "expired" and ev, "١٦ نصيحةٌ عمرُها أكثرُ من 200 يوم تنتهي ويُطلب سؤالٌ جديد")
M.remember(SAD, st, 1)
from app.services import lastgood
x = lastgood.load("advice:1:2270"); x["tranches"][0]["status"] = "done"; lastgood.save("advice:1:2270", x)
M.remember(SAD, st, 1)
check(lastgood.load("advice:1:2270")["tranches"][0]["status"] == "done", "١٧ سؤالٌ متكرّر لا يصفّر حالاتِ الدفعات — النصيحةُ تُتابَع")

# ‏D573: سعرٌ فوق متوسط 200 يوم أصلاً ⇒ لا شرطَ «ثبت فوقه»؛ والدفعةُ الثانية لا تسبق الأولى
INMA = {**SAD, "symbol": "1150", "name": "الإنماء", "price": 24.26, "sma200": 23.78, "decision": "انتظار", "eps_g": 2,
        "remaining": 13500, "next_q": {"as_of": "2026-09-30", "net_income": 1.5e9, "mape": 8}}
sti = A.stance(INMA)
check(all(c.get("k") != "reclaim" for t in sti["tranches"] for c in t.get("cond") or [])
      and all("متوسط 200" not in t["when"] for t in sti["tranches"]),
      "١٩ D573 السعرُ فوق متوسط 200 يوم ⇒ لا شرطَ «ثبت فوقه» (كان يتحقّق يومَ النصيحة)", str([t["when"] for t in sti["tranches"]]))
SAD_LOW = {**SAD, "price": 180, "sma200": 216.05}
d = M.fresh(SAD_LOW, A.stance(SAD_LOW), 1)
d, ev = M.evaluate(d, {"price": 220, "qty": 22, "results": []}, "2026-10-10")
check(d["tranches"][1]["status"] == "pending" and not any("الدفعة 2" in e for e in ev),
      "٢٠ D573 الدفعةُ الثانية لا تسبق الأولى وهي تنتظر النتائج — ولو تحقّق شرطُ السعر", " | ".join(ev))
check('k.count(":") < 2' in (ROOT / "backend/app/services/advisor_memory.py").read_text(encoding="utf-8")
      and M._key("2270", 1) == "advice:1:2270" and M._key("2270", 2) == "advice:2:2270", "٢١ D573 نصيحةٌ لكلّ محفظةٍ على حدة")
src = (ROOT / "backend/app/services/advisor.py").read_text(encoding="utf-8")
chat = (ROOT / "backend/app/services/ai_chat.py").read_text(encoding="utf-8")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mem = (ROOT / "backend/app/services/advisor_memory.py").read_text(encoding="utf-8")
check("قدّم حلاً لا تحليلاً فقط" in src and "remember(f, st, active_pid())" in src and "advisor.answer_portfolio(" in chat
      and 'id="advisor_watch_close"' in sch and 'id="advisor_watch_evening"' in sch and "bot.send(" in mem and "Notification(" in mem,
      "١٨ الربط: الميثاقُ يُلزم بالحلّ، والنصيحةُ تُحفظ، والهيكلةُ تصل صقر، والمراقبةُ مرّتين يومياً بإشعارٍ وتلغرام")
print(f"{'FAIL' if fail else 'PASS'} D568 · D569 — حلولُ المستشار وذاكرتُه")
sys.exit(fail)
