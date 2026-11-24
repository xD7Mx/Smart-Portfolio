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

obj = {"headline": "h", "local": [{"text": "من التطبيق وحده", "src": [0]}, {"text": "محليّ", "src": [2]}, {"text": "بلا مصدر", "src": []},
                                  {"text": "مصدرٌ وهميّ", "src": [7]}, {"text": "قالت الجزيرة كابيتال إنّ السوق", "src": [1]}, {"text": "خبرٌ (أرقام)", "src": [1]}],
       "portfolio": [{"symbol": "1120", "text": "ت", "src": [0, 1]}, {"symbol": "9999", "text": "غريب", "src": [1]}, {"symbol": "2222", "text": "أرقامٌ فقط", "src": [0]}],
       "recommendations": [{"symbol": "1120", "action": "شراء", "why": "سبب", "src": [0, 1]}]}
v = RD.validate(obj, 2, {"1120", "2222"})
check([r["text"] for r in v["local"]] == ["محليّ"],
      "٢ لا سطرَ بلا مصدرٍ بحثيٍّ صحيح — ولا اسمَ جهةٍ ناشرةٍ في النصّ (‏D746: «اعتمدها ولا تذكرها»)", str([r["text"] for r in v["local"]]))
check([r["symbol"] for r in v["portfolio"]] == ["1120"], "٣ ولا مركزَ لرمزٍ خارج المحفظة، ولا ما يعني المركزَ بلا خبرٍ من المصادر")
check("recommendations" not in v and "recommendations" not in RD.COMPOSE_PROMPT,
      "٤ والنموذجُ لا يوصي: أفضلُ الاختيارات محسوبةٌ بشروطٍ معلنة (‏research_paper.pick_candidates)")
v0 = RD.validate({"headline": "توقّعت الراجحي المالية ارتفاعاً"}, 1, set())
check(v0["headline"] == "", "٥ والعنوانُ الذي يسمّي جهةً ناشرةً يُحذف")

n = RD._clean_note({"headline": " خ ", "points": ["a", "", "b"], "companies": [{"symbol": "1120.SR", "name": "الراجحي", "target": 80},
                    {"symbol": "1120", "name": "الراجحي", "target": -3}, {"symbol": None}], "sectors": [{"name": "البنوك", "view": "إيجابي"}]})
check(n["headline"] == "خ" and n["points"] == ["a", "b"] and [c["symbol"] for c in n["companies"]] == [None, "1120"]
      and n["companies"][1]["target"] is None and n["companies"][0]["target"] == 80.0 and n["sectors"][0]["name"] == "البنوك",
      "٦ المذكّرة: حقولُها منظّفة، والرمزُ أربعةُ أرقامٍ وإلا لا رمز، والسعرُ المستهدف موجبٌ أو لا شيء")

rep = {"portfolio_name": "محفظتي", "date": "2026-11-15", "headline": "عنوان", "picks": [{"symbol": "8010"}],
       "market": {"tasi": {"close": 10258.22, "pct": -0.66}, "breadth": {"value": 2.7e9}, "tech": {"view": "محايد"}}}
cap = RD.caption(rep)
check(cap.startswith("<b>التقرير اليومي — الأحد 15 نوفمبر 2026</b>") and "10,258.22" in cap and "-0.66%" in cap and "اختياراتنا اليوم: 1" in cap
      and not any(h in cap for h in ("الجزيرة", "الراجحي المالية", "المصادر")),
      "٧ تعليقُ ملفّ تلغرام مؤرَّخٌ بيوم الجلسة، بأرقامها ونظرتِنا، وبلا مصادر", cap.replace("\n", " ¦ "))

k = RD.knowledge()
k["notes"] = [{"key": "a", "date": "2025-10-01"}, {"key": "b", "date": "2026-11-01"}]
k["read"] = {"a": {"date": "2025-10-01"}, "b": {"date": "2026-11-01"}, "c": {"date": "2025-01-01"}}
p = RD.prune(k, T)
check([x["key"] for x in p["notes"]] == ["b"] and set(p["read"]) == {"b"}, "٨ والسياقُ التاريخيُّ سنةٌ تُحفظ وما قبلها يُطوى")

sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
check("create_subprocess_exec" in sch[sch.index("async def job_research_ingest"):sch.index("async def job_research_night")]
      and 'CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=40)' in sch and 'id="research_ingest_night"' in sch
      and 'CronTrigger(hour=15, minute=5), id="research_ingest_afternoon"' in sch and "compose_all(send=True, final=False)" in sch   # ‏D806: يُرسَل مكتوباً
      and 'id="research_report_morning"' not in sch,
      "٩ الجدول: القراءةُ في عمليةٍ منفصلة صباحاً وقبيل الإغلاق وليلاً، والتقريرُ بعد إغلاق السوق أيامَ التداول ويُرسَل")
check('@router.post("/research-desk/run", dependencies=[Depends(require_owner)])' in mk and '@router.get("/research-desk")' in mk
      and '@router.get("/research-desk/paper")' in mk and '@router.get("/research-desk/pdf")' in mk and "/research-desk/library" not in mk
      and "compose_all(send=False)" in mk, "١٠ التشغيلُ اليدويّ للمالك وحده ولا يُرسَل، والورقةُ وملفُّها مساران، ولا مكتبةَ معروضة")
rd = (ROOT / "backend/app/services/research_desk.py").read_text(encoding="utf-8")
check("لا مصدرَ غيرها" in RD.COMPOSE_PROMPT and "src" in RD.COMPOSE_PROMPT and "من نصّ التقرير وأرقامه حرفاً" in RD.READ_PROMPT
      and "لا تذكر أسماءَ الجهات الناشرة" in RD.COMPOSE_PROMPT,
      "١١ النموذجُ مُلزَمٌ بالمصادر: القراءةُ من نصّ التقرير حرفاً، والتقريرُ لا مصدرَ له غيرُ المقروء وأرقامِ التطبيق")
print(("FAIL" if fail else "PASS") + " D745 · D746 — قسمُ الأبحاث: مصادرُ تُلزِم ولا تُعرض، وتقريرٌ مؤرَّخٌ بعد الإغلاق إلى تلغرام")
sys.exit(fail)
