#!/usr/bin/env python3
"""السوقُ العالميّ بمحرّك الرسم نفسِه لا بتطبيقٍ مختلف (D443).

    python3 scripts/audit/global_chart_native.py

رآه المالك: تبويبُ «السوق العالمي» إطارٌ من TradingView يقول «هذا الرمزُ
غيرُ موجود» لـTADAWL:2080، ويخالف تصميمَ التطبيق. فيُشترط أن تخلو صفحةُ
الرسم من ذلك الإطار، وأن يرسم التبويبُ العالميّ بـNativeChart، وأن يُرمَّز
الرمزُ في مسار التاريخ (‏^ و= في رموزٍ عالمية).
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
src = (ROOT / "frontend/src/pages/ChartPage.tsx").read_text(encoding="utf-8")
api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
check("TradingViewChart" not in src, "١ لا إطارَ TradingView في صفحة الرسم")
check(src.count("<NativeChart") == 1 and "<InlineStockSearch onPick={pick} global />" in src,
      "٢ D521 السوقان في رسمٍ واحدٍ وحقلِ بحثٍ واحد — لا تبويبَ «السوق العالمي»")
check("/market/history/${encodeURIComponent(symbol)}" in api, "٣ والرمزُ مُرمَّزٌ في مسار التاريخ")
check('"^TASI.SR", "تاسي"' in src, "٤ وتاسي ضمن مؤشّرات الأسواق (بأمر المالك)")
nc = (ROOT / "frontend/src/components/analysis/NativeChart.tsx").read_text(encoding="utf-8")
check("const tkey" in nc and "time: b.date," not in nc,
      "٥ والرسمُ يقبل نقاطَ الجلسة بساعتها (تاسي من «تداول») لا التاريخَ وحدَه")

# ══ D521 غرفةُ التداول ══
import os as _os
_R = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_css = open(_os.path.join(_R, "frontend/src/styles/globals.css"), encoding="utf-8").read()
_i18 = open(_os.path.join(_R, "frontend/src/i18n.ts"), encoding="utf-8").read()
check("62vh" not in nc and "height: 440" in nc and ".chart-frame { contain: strict" in _css
      and "pinch-zoom" not in _css.split(".chart-lock {")[1].split("/* إشعار")[0],
      "٦ D521 الرسمُ إطارٌ مقفلُ الارتفاع لا يتبع vh، والقرصُ والمحوران للرسم لا للصفحة")
check("<Drop label={(RANGES.find" in nc and "<Drop label={IND.filter" in nc and "RANGES.map(([id, lbl]) => (\n            <button key={id} onClick={() => setRange(id)}" not in nc,
      "٧ D521 المدّةُ والمؤشراتُ قائمتان منسدلتان يظهر عليهما المختارُ وحدَه")
check('ar: "الرسم البياني"' in _i18 and 'tab("idx", "المؤشرات")' in src and 'tab("mine", "محفظتك")' in src
      and "stars" not in src,
      "٨ D529 التبويبُ «الرسم البياني» ودرجاه «محفظتك» و«المؤشرات» — بلا «نجوم تاسي»")
check('"channel" ? null' not in nc and '[["free", "حرّ"], ["line", "خطّ"]]' in nc and "onPointerMove={onMove}" in nc,
      "٩ D529 أداةُ «رسم» بخيارين: حرٌّ وخطّ — بلا قناة")
print(("FAIL" if fail else "PASS") + " D443 · D521 — رسمٌ واحدٌ للسوقين")
sys.exit(fail)
