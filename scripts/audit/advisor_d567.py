#!/usr/bin/env python3
"""حارسُ D567: مستشارُ المحفظة — النيّةُ، والموقفُ المحسوبُ بالقواعد بأرقامٍ معلومةِ الجواب
(سدافكو والراجحي ريت كما حُلّلا للمالك)، والدفعاتُ المتواكبةُ مع المركز، والمقارنة، وموعدُ النتائج،
والربطُ بصقر.

    python3 scripts/audit/advisor_d567.py
"""
import os, sys, tempfile, pathlib
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

from app.services import advisor as A
Q = ["هل اضخ في الراجحي ريت في هذا المستوى؟", "ماذا عن سدافكو هل اغيره بشركة المراعي او انتظره",
     "ماذا افعل في سدافكو", "أحذفها أم أنتظر؟"]
check(all(A.intent(q) for q in Q) and not A.intent("كم النقد المتاح") and not A.intent("ما أداء محفظتي"),
      "١ النيّة: سؤالُ القرار يذهب للمستشار، وسؤالُ المعلومة لا")
check(all(A.asks(q) for q in Q) and not A.asks("بع لي سدافكو"), "٢ سؤالُ الرأي ليس أمرَ تنفيذ — «بِع لي» يبقى مرفوضاً")
check(A.results_due("2026-09-30", date(2026, 10, 1)) == "2026-10-30" and A.results_due("2026-12-31", date(2026, 10, 1)) == "2027-03-31",
      "٣ موعدُ النتائج: الأوّليةُ خلال 30 يوماً، والسنويةُ خلال 90")

# سدافكو كما قيس للمالك: 22 سهماً، 1.22٪ وهدفُها 3.5٪، المتبقّي 7,548.92، الربحُ −30٪، القرارُ شراء
SAD = {"symbol": "2270", "name": "سدافكو", "held": True, "qty": 22, "avg_cost": 222.95, "invested": 4904.9, "value": 4045.8,
       "pnl_pct": -17.5, "weight": 1.22, "target": 3.5, "remaining": 7548.92, "capital": 331277.74, "price": 183.9,
       "decision": "شراء", "rsi": 19.9, "trend": "هابط", "sma200": 216.05, "w52_low": 183.9, "eps_g": -24.9, "roe": 27.4,
       "dy": 7.07, "pe": 14.2, "price_cagr": 8.5, "fin": 80, "upside": 11.1, "results_due": "2026-10-30",
       "files": ["[فترة 2026-06-30] تراجع صافي الربح لفترة الستة أشهر إلى 170.26 مليون ريال مقابل 243.78 مليون ريال"]}
st = A.stance(SAD)
tot = sum(t["amount"] for t in st["tranches"])
check(st["action"].startswith("انتظر") and len(st["tranches"]) == 3 and abs(tot - 7548.92) < 0.02
      and "النتائج القادمة" in st["tranches"][0]["when"] and "2026-10-30" in st["tranches"][0]["when"]
      and sum(t["shares"] for t in st["tranches"]) <= 41,
      "٤ سدافكو: الربحُ يتراجع ⇒ انتظر النتائج ثمّ ثلاثُ دفعاتٍ مجموعُها المتبقّي بالضبط (كما نُصح المالك)", str(st["tranches"]))
# الدفعاتُ تتواكب: نفّذ المالكُ 14 سهماً ⇒ المتبقّي ينقص من الحالة الحيّة وحدها
SAD2 = {**SAD, "qty": 36, "value": 4045.8 + 14 * 183.9, "weight": 2.0, "remaining": 7548.92 - 14 * 183.9}
st2 = A.stance(SAD2)
check(abs(sum(t["amount"] for t in st2["tranches"]) - (7548.92 - 14 * 183.9)) < 0.02 and st2["remaining_shares"] < st["remaining_shares"],
      "٥ تتواكب مع الزمن: ما نُفّذ يُطرح من المتبقّي الحيّ، وما لم يُنفَّذ يبقى", f"{st['remaining_shares']} ⇒ {st2['remaining_shares']}")
# الراجحي ريت: 2.35٪ وهدفُه 2.8٪، المتبقّي 1,491.67، شراء، الدخلُ يتراجع في الملفّ
REIT = {"symbol": "4340", "name": "الراجحي ريت", "held": True, "qty": 1007, "avg_cost": 8.03, "value": 7784.11, "weight": 2.35,
        "target": 2.8, "remaining": 1491.67, "capital": 331277.74, "price": 7.73, "decision": "شراء", "rsi": 36, "trend": "هابط",
        "is_reit": True, "reit": {"nav": 8.385, "premium": -7.8, "overdue": False, "trend": "صاعد", "nav_change": 2.6},
        "files": ["[سنوي 2025-12-31] انخفض صافي الربح للعام إلى 147.39 مليون ريال مقارنة بـ 187.25 مليون ريال"]}
sr = A.stance(REIT)
check(sr["action"] == "أضف على دفعتين" and abs(sum(t["amount"] for t in sr["tranches"]) - 1491.67) < 0.02
      and sr["tranches"][0]["when"].startswith("الآن") and any("صافي الأصول" in s for s in sr["stop_rules"]),
      "٦ الريت يُحكم بتوزيعه وصافي أصوله لا بربحه: دفعتان أولاهما الآن (كما نُصح المالك)، وقاعدةُ توقّفٍ على التقييم", str(sr["tranches"]))
sr2 = A.stance({**REIT, "reit": {**REIT["reit"], "nav_change": -10.0}})
check(sr2["action"].startswith("انتظر") and any("7.13" in t["when"] for t in sr2["tranches"]),
      "٦ب وإن هبط صافي أصوله 10٪ ⇒ انتظر، وشرطُ القيمة خصمُ 15٪ (7.13)", str(sr2["tranches"]))
# الحقائقُ المحسوبة: الراجحي ريت خصمُه −7.8٪ وأقرانُه أعمق خصماً (أرقامُ reit_now) ⇒ «أغلى» لا «أفضل»
PEERS = [{"symbol": s, "premium": p, "yield": y} for s, p, y in (
    ("4330", -52.4, 7.14), ("4335", -52.9, 6.81), ("4336", -44.3, 7.26), ("4332", -43.2, 6.4), ("4338", -41.2, 7.67),
    ("4348", -38.7, 7.64), ("4339", -32.8, 7.24), ("4333", -32.4, 6.96), ("4345", -30.7, 7.93), ("4349", -27.5, 8.85),
    ("4342", -25.6, 9.2), ("4350", -22.4, 11.3), ("4344", -22.1, 8.27), ("4334", -6.1, 8.84), ("4337", 6.6, 3.84),
    ("4347", 15.6, 8.47), ("4331", 20.0, 9.06))] + [{"symbol": "4340", "premium": -7.8, "yield": 6.92, "self": True}]
fx = A.reit_facts({**REIT, "reit": {**REIT["reit"], "yield": 6.92,
                                     "nav_history": [{"v": 9.091}, {"v": 9.032}, {"v": 8.176}, {"v": 8.385}]}, "peers": PEERS})
check(any("أغلى" in x and "13 من 17" in x for x in fx) and any("هبط 9.5٪" in x and "+2.6٪" in x for x in fx),
      "١٤ حقائقُ الأقران وصافي الأصول محسوبةٌ لا مستنتجة: «أغلى من أكثرهم» وهبوطُ 9.5٪ ثمّ +2.6٪", " | ".join(fx))
# بلغ الهدف ⇒ احتفظ؛ وفوقه ⇒ خفّف بالفائض؛ ولا مركزَ ولا هدف ⇒ راقب
check(A.stance({**REIT, "remaining": 0})["action"] == "احتفظ", "٧ بلغ هدفَه ⇒ احتفظ")
over = A.stance({**REIT, "value": 15000, "weight": 4.5, "remaining": 0})
check(over["action"] == "خفّف" and abs(over["amount"] - (15000 - 0.028 * 331277.74)) < 0.5, "٨ فوق هدفه ⇒ خفّف بالفائض", str(over.get("amount")))
check(A.stance({"symbol": "2280", "name": "المراعي", "price": 43.5})["action"] == "راقب", "٩ لا مركزَ ولا هدف ⇒ راقب")
ALM = {"symbol": "2280", "name": "المراعي", "decision": "انتظار", "roe": 12.2, "dy": 2.64, "pe": 17.8, "eps_g": -1.5,
       "price_cagr": 0.8, "fin": 72, "upside": 5.3}
cmp = A.compare(SAD, ALM)
wins = {r["بند"]: r["الأفضل"] for r in cmp}
check(wins["العائد على حقوق الملكية٪"] == "2270" and wins["عائد التوزيع٪"] == "2270" and wins["مكرّر الربحية"] == "2270"
      and wins["نموّ الربحية٪"] == "2280" and "خسارة" in (A.switch_cost(SAD) or ""),
      "١٠ المقارنة: الأفضلُ في كلّ بند، وكلفةُ الاستبدال تُذكر (خسارةٌ تُثبَّت)", A.switch_cost(SAD) or "")
txt = A.render([SAD], [st])
check("الدفعة 1" in txt and "انتظر" in txt and "القرارُ لك" in txt, "١١ بلا نموذج يُكتب الجوابُ من الموقف نفسِه — المستشارُ لا يصمت")
# ‏«الراجحي ريت» شركةٌ واحدة لا اثنتان (قِيس على الخادم: فُهمت مصرفَ الراجحي معها)
import app.services.market_screener as _ms
_ms.get_cached_screener = lambda: [{"symbol": "2280", "name": "المراعي"}, {"symbol": "1120", "name": "الراجحي"}]
CTX = {"المحفظة": {"المراكز": [{"الرمز": "1120", "الشركة": "مصرف الراجحي"}, {"الرمز": "4340", "الشركة": "صندوق الراجحي ريت"},
                               {"الرمز": "2270", "الشركة": "سدافكو"}]}}
c1 = [c["symbol"] for c in A.companies("هل اضخ في الراجحي ريت في هذا المستوى؟", CTX)]
c2 = [c["symbol"] for c in A.companies("ماذا عن سدافكو هل اغيره بشركة المراعي", CTX)]
c3 = [c["symbol"] for c in A.companies("هل أضيف على مصرف الراجحي؟", CTX)]
check(c1 == ["4340"] and sorted(c2) == ["2270", "2280"] and c3 == ["1120"],
      "١٣ التعرّف: «الراجحي ريت» الصندوقُ وحده، و«سدافكو … المراعي» شركتان، و«مصرف الراجحي» المصرف", f"{c1} · {c2} · {c3}")
src = (ROOT / "backend/app/services/advisor.py").read_text(encoding="utf-8")
chat = (ROOT / "backend/app/services/ai_chat.py").read_text(encoding="utf-8")
check("غيرُ محقّقة" in src and '"SELL": "بيع"' in src and "for i in range(2):" in src
      and "حرفياً" in src and "لا تغيّرها ولا تخترع" in src and "from app.services import advisor" in chat
      and "advisor.intent(question)" in chat and chat.index("advisor.intent(question)") < chat.index("llm_ready = bool("),
      "١٢ صقرٌ (التطبيق وتلغرام) يمرّ بالمستشار قبل أيّ مسار، والنموذجُ ملزَمٌ بأرقام الموقف")
print(f"{'FAIL' if fail else 'PASS'} D567 — مستشارُ المحفظة")
sys.exit(fail)
