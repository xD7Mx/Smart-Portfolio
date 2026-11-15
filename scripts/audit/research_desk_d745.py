#!/usr/bin/env python3
"""حارسُ D745 — قسمُ الأبحاث («مختبرُ الأبحاث» الجديد · بأمر المالك 2026-11-15).

«تقريرٌ خاصٌّ بمحفظتنا من المصادر الموثوقة نفسِها — لا يجيب شيئاً من رأسه… ويُرسَل يومياً على تلغرام… وتوصياتٌ إن وُجدت، انتقائية».
فيُفحص على الدوالّ نفسِها: الطابورُ (اليوميُّ الأحدثُ أوّلاً ولا يُعاد المقروء)، والتحقّقُ (لا سطرَ بلا مصدرٍ صحيح، ولا توصيةَ لرمزٍ
خارج المحفظة والمصادر ولا بلا دليلين)، والمذكّرةُ (حقولُها ورموزُها)، ورسالةُ تلغرام، والجدولُ (قراءةٌ في عمليةٍ منفصلة · تقريرٌ قبل
الافتتاح أيامَ التداول)، والمساراتُ (التشغيلُ للمالك وحده).

    python3 scripts/audit/research_desk_d745.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date   # noqa: E402
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import research_desk as RD   # noqa: E402
T = date(2026, 11, 15)
items = [{"url": "co", "date": "2026-11-14", "kind": "تقرير شركة"}, {"url": "d1", "date": "2026-11-12", "kind": "تقرير يوميّ"},
         {"url": "d2", "date": "2026-11-15", "kind": "تقرير يوميّ"}, {"url": "old", "date": "2026-09-01", "kind": "تقرير يوميّ"},
         {"url": "ec", "date": "2026-11-13", "kind": "تقرير اقتصاديّ"}, {"url": None, "date": "2026-11-15", "kind": "تقرير يوميّ"}]
q = [i["url"] for i in RD.queue(items, {"d1": {}}, T, 10)]
check(q == ["d2", "ec", "co"], "١ الطابور: اليوميُّ الأحدثُ أوّلاً ثمّ الاقتصاديّ ثمّ الشركات — ولا يُعاد المقروء ولا ما خرج عن المدى أو بلا ملفّ", str(q))

obj = {"headline": "h", "market": {"summary": "s", "points": [{"text": "بمصدر", "src": [1]}, {"text": "بلا مصدر", "src": []}, {"text": "مصدرٌ وهميّ", "src": [7]}]},
       "local": [{"text": "من التطبيق وحده", "src": [0]}, {"text": "محليّ", "src": [2]}],
       "portfolio": [{"symbol": "1120", "stance": "إيجابي", "text": "ت", "src": [0]}, {"symbol": "9999", "text": "غريب", "src": [1]}],
       "recommendations": [{"symbol": "1120", "action": "إضافة", "why": "سبب", "src": [0, 1]},
                           {"symbol": "2222", "action": "شراء", "why": "سبب", "src": [1]},
                           {"symbol": "7777", "action": "شراء", "why": "سبب", "src": [0, 1]},
                           {"symbol": "2010", "action": "شراء", "why": "", "src": [0, 2]}], "no_rec_reason": "x"}
v = RD.validate(obj, 2, {"1120", "2222", "2010"})
check([r["text"] for r in v["market"]["points"]] == ["بمصدر"] and [r["text"] for r in v["local"]] == ["محليّ"],
      "٢ لا سطرَ بلا مصدرٍ صحيح — والخبرُ لا يكفيه رقمُ التطبيق وحده (‏0)", str([r["text"] for r in v["market"]["points"] + v["local"]]))
check([r["symbol"] for r in v["portfolio"]] == ["1120"], "٣ ولا مركزَ لرمزٍ خارج المحفظة والمصادر")
check([r["symbol"] for r in v["recommendations"]] == ["1120"] and v["no_rec_reason"] == "",
      "٤ والتوصيةُ بدليلين (مصدرٌ بحثيّ + أرقامُ التطبيق) ولرمزٍ معروفٍ وبسبب — وإلا تُحذف", str([r["symbol"] for r in v["recommendations"]]))
v0 = RD.validate({"recommendations": [], "no_rec_reason": "لا ما يستحقّ"}, 1, set())
check(v0["recommendations"] == [] and v0["no_rec_reason"] == "لا ما يستحقّ", "٥ وإن لم تكن توصيةٌ قيل ذلك وسببُه")

n = RD._clean_note({"headline": " خ ", "points": ["a", "", "b"], "companies": [{"symbol": "1120.SR", "name": "الراجحي", "target": 80},
                    {"symbol": "1120", "name": "الراجحي", "target": -3}, {"symbol": None}], "sectors": [{"name": "البنوك", "view": "إيجابي"}]})
check(n["headline"] == "خ" and n["points"] == ["a", "b"] and [c["symbol"] for c in n["companies"]] == [None, "1120"]
      and n["companies"][1]["target"] is None and n["companies"][0]["target"] == 80.0 and n["sectors"][0]["name"] == "البنوك",
      "٦ المذكّرة: حقولُها منظّفة، والرمزُ أربعةُ أرقامٍ وإلا لا رمز، والسعرُ المستهدف موجبٌ أو لا شيء")

rep = {"portfolio_name": "محفظتي", "date": "2026-11-15", "headline": "عنوان", "market": {"summary": "مستقرّ"},
       "local": [{"text": "محليّ", "src": [1]}], "global": [], "portfolio": [{"name": "الراجحي", "stance": "إيجابي", "text": "ت", "src": [0, 1]}],
       "recommendations": [], "no_rec_reason": "لا ما يستحقّ", "sources": [{"n": 1, "source": "الجزيرة كابيتال"}, {"n": 2, "source": "الراجحي المالية"}]}
L = RD.telegram_lines(rep)
check(L[0].startswith("📑 التقرير اليوميّ — محفظتي") and any("لا توصيةَ اليوم" in x for x in L) and "المصادر: الجزيرة كابيتال · الراجحي المالية" in L[-1],
      "٧ رسالةُ تلغرام: العنوانُ والسوقُ والأخبارُ ومحفظتُنا والتوصياتُ (أو سببُ غيابها) والمصادر", L[-1])

k = RD.knowledge()
k["notes"] = [{"key": "a", "date": "2025-10-01"}, {"key": "b", "date": "2026-11-01"}]
k["read"] = {"a": {"date": "2025-10-01"}, "b": {"date": "2026-11-01"}, "c": {"date": "2025-01-01"}}
p = RD.prune(k, T)
check([x["key"] for x in p["notes"]] == ["b"] and set(p["read"]) == {"b"}, "٨ والسياقُ التاريخيُّ سنةٌ تُحفظ وما قبلها يُطوى")

sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check("create_subprocess_exec" in sch[sch.index("async def job_research_ingest"):sch.index("async def job_research_night")]
      and 'CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=9, minute=40)' in sch and 'id="research_ingest_night"' in sch
      and "compose_all(send=True)" in sch,
      "٩ الجدول: القراءةُ في عمليةٍ منفصلة صباحاً وعصراً وليلاً، والتقريرُ قبل الافتتاح أيامَ التداول ويُرسَل")
check('@router.post("/research-desk/run", dependencies=[Depends(require_owner)])' in mk and '@router.get("/research-desk")' in mk
      and "compose_all(send=False)" in mk, "١٠ التشغيلُ اليدويّ للمالك وحده ولا يُكرّر رسالةَ تلغرام")
rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
check("لا مصدرَ غيرها" in rd and "src" in RD.COMPOSE_PROMPT and "من نصّ التقرير وأرقامه حرفاً" in RD.READ_PROMPT,
      "١١ النموذجُ مُلزَمٌ بالمصادر: القراءةُ من نصّ التقرير حرفاً، والتقريرُ لا مصدرَ له غيرُ المقروء وأرقامِ التطبيق")
print(("FAIL" if fail else "PASS") + " D745 — قسمُ الأبحاث: مصادرُ موثّقة، وتوصياتٌ انتقائية بدليلين، وتقريرٌ يوميٌّ إلى تلغرام")
sys.exit(fail)
