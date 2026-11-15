#!/usr/bin/env python3
"""حارسُ D749 — أرشيفُ التقارير لجميع الجلسات بتسلسلٍ تاريخيّ (بأمر المالك 2026-11-16: «بصيغة أيام — 15 · 14 · 13 — ويتوفّر لجميع الأيام»).

يُفحص: سوقُ الجلسة الماضية من أرقامها هي لا من بعدها (الشموعُ حتّاها، والقطاعاتُ وعمقُ السوق من إغلاقات الشركات يومَها وما قبله، والأسواقُ
العالمية بآخر إغلاقٍ حتّاها)، ولا تقريرَ ليومٍ بلا جلسة، والمذكّراتُ لا تدخل تقريرَ جلسةٍ نُشرت بعد التالية، وصفحةُ المحفظة لا تُعاد لما مضى،
والأرشيفُ يعمل ليلاً في عمليةٍ منفصلة.

    python3 scripts/audit/research_archive_d749.py
"""
import os, pathlib, sys, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from datetime import date, timedelta   # noqa: E402
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import research_paper as RP, research_desk as RD   # noqa: E402
bars, d, px = [], date(2025, 12, 1), 100.0
while d <= date(2026, 11, 15):
    if d.weekday() not in (4, 5):
        bars.append({"date": d.isoformat(), "open": px, "high": px + 1, "low": px - 0.5, "close": px + 0.5, "volume": 1})
        px += 0.5
    d += timedelta(days=1)
day = "2026-11-12"
hist = [{"date": b["date"], "close": b["close"]} for b in bars]
ctx = {"tasi": RP._bars_ok(bars), "intra": [{"date": f"{day} 10:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
                                             {"date": "2026-11-15 10:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}],
       "closes": {"1": {"2026-11-11": 10.0, day: 11.0, "2026-11-15": 50.0}, "2": {"2026-11-11": 10.0, day: 9.0, "2026-11-15": 1.0},
                  "3": {"2026-11-11": 10.0, day: 10.0}},
       "fund": {"1": {"shares": 1e6, "verified": True, "ni": 1e5, "eq": 5e6}, "2": {"shares": 1e6, "verified": True, "ni": 1e5, "eq": 5e6},
                "3": {"shares": 1e6, "verified": True, "ni": 1e5, "eq": 5e6}},
       "hist": {"^DJI": hist}, "dy": {}, "names": {"1": "أ", "2": "ب", "3": "ج"}, "sectors": {"1": "البنوك", "2": "البنوك", "3": "الطاقة"},
       "events": [{"date": "2026-11-13", "symbol": "1", "company_name": "أ", "title": "صرف أرباح"}, {"date": "2026-12-30", "symbol": "1", "title": "بعيد"}]}
m = RP.market_at(day, ctx, {day: {"value": 4.1e9, "volume": 2.3e8, "trades": 4e5}})
last = [b for b in bars if b["date"] <= day][-1]
check(m and m["tech"]["date"] == day and m["tasi"]["close"] == last["close"] and m["daily"][-1]["d"] == day
      and len(m["intraday"]) == 1 and m["global"] and m["global"][0]["date"] == day,
      "١ سوقُ الجلسة الماضية من أرقامها هي: الشموعُ والرسمُ داخلَ الجلسة والأسواقُ العالمية حتّاها لا بعدها")
check(m["breadth"]["up"] == 1 and m["breadth"]["down"] == 1 and m["breadth"]["unch"] == 1 and m["breadth"]["value"] == 4.1e9
      and m["gainers"][0]["name"] == "أ" and abs(m["gainers"][0]["pct"] - 10) < 1e-9 and m["losers"][0]["name"] == "ب"
      and next(s for s in m["sectors"] if s["name"] == "البنوك")["value"] is None,
      "٢ وعمقُ السوق والأكثرُ ارتفاعاً وانخفاضاً من إغلاقات الشركات يومَها، والقيمةُ من سجلّ الجلسات — وما لم يُحفظ لا يُكتب")
check([a["date"] for a in m["actions"]] == ["2026-11-13"], "٣ وإجراءاتُ الشركات أسبوعَ الجلسة نفسِه")
check(RP.market_at("2026-11-14", ctx) is None, "٤ ولا تقريرَ ليومٍ بلا جلسة")
notes = [{"date": "2026-11-10", "key": "a"}, {"date": "2026-11-12", "key": "b"}, {"date": "2026-11-15", "key": "c"}]
got = [n["key"] for n in RD.recent_sources(notes, date(2026, 11, 12), upto="2026-11-13")]
check(got == ["b", "a"], "٥ ولا تدخل تقريرَ الجلسة مذكّرةٌ نُشرت بعد الجلسة التالية", str(got))
rep = {"date": day, "portfolio_name": "محفظتي", "headline": "عنوان", "market": m, "averages": {}, "analysis": RP.market_analysis(m, {}),
       "tech_text": list(RP.tech_commentary(m)), "positions": [{"symbol": "1120", "name": "x", "view": "شراء"}], "picks": [], "backfill": True,
       "local": [], "global": [], "watch": []}
pf = RP.render(rep, "portfolio")
check("لا تُعاد كتابتُها لجلسةٍ مضت" in pf and "نظرتنا لمراكز المحفظة" not in pf and "None" not in RP.render(rep, "all"),
      "٦ وصفحةُ المحفظة لا تُعاد لجلسةٍ مضت بمراكز اليوم — تقول ذلك")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text(encoding="utf-8")
lab = (ROOT / "frontend/src/pages/ResearchLab.tsx").read_text(encoding="utf-8")
check("backfill_cli" in sch and 'id="research_backfill"' in sch and "create_subprocess_exec" in sch[sch.index("async def job_research_backfill"):]
      and hasattr(RD, "backfill") and RD.KEEP_REPORTS >= 600,
      "٧ الأرشيفُ يُكتب ليلاً في عمليةٍ منفصلة، ويتّسع لنحو سنةٍ من التقارير")
check("months(head.data.dates)" in lab and 'data-role="rl-day"' in lab and 'd.label.split(" ")[1]' in lab,
      "٨ والأيامُ في الصفحة أرقاماً تحت شهرها — 15 · 14 · 13")
print(("FAIL" if fail else "PASS") + " D749 — أرشيفُ التقارير لجميع الجلسات بتسلسلٍ تاريخيّ، كلُّ جلسةٍ بأرقامها هي")
sys.exit(fail)
