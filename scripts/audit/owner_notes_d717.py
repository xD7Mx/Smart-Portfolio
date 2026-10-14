#!/usr/bin/env python3
"""حارسُ D717 · D718 — ملاحظاتُ المالك (2026-10-14) على الرسم والتقرير والمحفظة.

  · ‏D717 «المستوياتُ جعلتَها منقّطة — خلّها خطّاً متّصلاً»: مستوياتُ فيبوناتشي في D7M كلُّها متّصلة (كانت العاديّةُ متقطّعةً منذ D713).
  · ‏D717 «الشموعُ في تقرير المحفظة لتاسي فقط — احذف شموعَ الربح، وشموعُ تاسي شكلُها غريب: ضع فتراتِ السنوات في الرسم، والتظليلُ
    يوضّح فترةَ التقرير»: لا شموعَ لصافي الربح، وتاسي شهريٌّ لخمس سنواتٍ مستقلٌّ عن تاريخ المحفظة (كان أسابيعَ صافي الربح نفسَها
    فيقصر بقِصَره)، وفترةُ التقرير معه. (والرسمُ نفسُه يقيسه ‎ui_d711.mjs‎ في المتصفّح.)
  · ‏D718 «أيقونةُ مطابقة كشف الوسيط احذفها — مكرّرةٌ بلا قيمةٍ مضافة»: لا زرَّ ولا نافذةَ في المحفظة.

    python3 scripts/audit/owner_notes_d717.py
"""
import ast, datetime, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


def visible(path):
    s = (ROOT / path).read_text(encoding="utf-8")
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", s)


nc = visible("frontend/src/components/analysis/NativeChart.tsx")
fib = nc[nc.index("for (const l of fib.lines)"):nc.index("const zoneList")]
check("lineStyle: 0" in fib and "lineStyle: gold ? 0 : 2" not in fib and not re.search(r"lineStyle:\s*[^0\s,}]", fib),
      "١ مستوياتُ فيبوناتشي كلُّها خطٌّ متّصل — والذهبيّةُ تتميّز بلونها لا بنقطها")

src = (ROOT / "backend/app/api/v1/endpoints/reports.py").read_text(encoding="utf-8")
check("def profit_candles" not in src and "_profit_candles" not in src and '"candles":' not in src and "tasi_weekly" not in src,
      "٢ تقريرُ المحفظة لا يبني شموعَ صافي الربح ولا تاسي المحاذيَ لها")
tree = ast.parse(src)
fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "tasi_monthly"), None)
ns: dict = {}
if fn is not None:
    exec(compile(ast.Module([fn], []), "reports.py", "exec"), ns)
tm = ns.get("tasi_monthly")
rows = [{"date": f"{2019 + (k // 12)}-{k % 12 + 1:02d}-01", "open": 100 + k, "high": 105 + k, "low": 95 + k, "close": 101 + k}
        for k in range(84)]
rows.reverse()                                                    # بأيّ ترتيب
rows.append({**rows[0], "close": 999})                            # شهرٌ مكرَّر ⇒ آخرُ ما وصل (جلسةُ الشهر الجاري)
r = tm(rows, datetime.date(2025, 12, 1), datetime.date(2025, 12, 31)) if tm else None
pts = (r or {}).get("points") or []
check(r and len(pts) == 60 and pts[0]["d"] == "2021-01-01" and pts[-1]["d"] == "2025-12-01" and pts[-1]["c"] == 999
      and all(a["d"] < b["d"] for a, b in zip(pts, pts[1:])) and r["from"] == "2025-12-01" and r["to"] == "2025-12-31"
      and r["interval"] == "شهري",
      "٣ وتاسي شهريٌّ لخمس سنواتٍ مرتّبٌ بلا شهرٍ مكرَّر، وفترةُ التقرير معه",
      f"{len(pts)} شهراً · {pts[0]['d'] if pts else '—'} → {pts[-1]['d'] if pts else '—'}")
check(tm and tm(rows[:11], None, None) is None and tm([], None, None) is None,
      "٤ وأقلُّ من سنةٍ لا يُعدّ رسماً — لا شموعَ مختلَقة")
check("await market_service.get_bars(\"^TASI.SR\", \"1mo\")" in src and "_period_anchors(" in src[src.index("async def _tasi_candles"):],
      "٥ من الشهريّ الذي يرسمه التطبيقُ نفسُه، وفترةُ التقرير هي المغلقةُ نفسُها التي تُقاس بها الأرقام")
rd = visible("frontend/src/components/reports/ReportDocument.tsx")
check("data.candles" not in rd and "data.tasi_candles &&" in rd and 'title="مؤشّرُ تاسي"' in rd,
      "٦ والورقةُ ترسم تاسي وحده، ولو حمل تقريرٌ مؤرشَفٌ شموعَ الربح")
# ‏D717 (المالك): «لا تضع تبريراً بجانب كلمة مؤشّر تاسي — اجعل الرسمَ من الأسفل يوضّح ذلك، هنا قوّةُ التصميم»
crd = visible("frontend/src/components/reports/CompanyReportDocument.tsx")
titles = re.findall(r'<ReportCandles[^>]*?title="([^"]*)"', rd + crd, flags=re.S)
check(titles and all("—" not in t and "شموع" not in t for t in titles),
      "٦ب والعنوانُ اسمٌ وحده بلا شرحٍ بجانبه — السنواتُ والأشهرُ أسفلَ الرسم تقول المدّة", " · ".join(titles))
rc = visible("frontend/src/components/reports/ReportCandles.tsx")
check('data-role="year-label"' in rc and 'data-role="year-sep"' in rc and 'data-role="report-band"' in rc,
      "٧ والمكوِّنُ يسمّي السنواتِ ويفصلها، ويظلّل الفترةَ على شموعها")

pp = visible("frontend/src/pages/PortfolioPage.tsx")
check("كشف الوسيط" not in pp and "ReconcileModal" not in pp and "reconOpen" not in pp,
      "٨ ‏D718: لا أيقونةَ ولا نافذةَ لمطابقة كشف الوسيط في المحفظة — بأمر المالك: مكرّرةٌ بلا قيمةٍ مضافة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
