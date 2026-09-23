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
check(src.count("<NativeChart") >= 2, "٢ والتبويبُ العالميُّ يرسم بالمحرّك نفسِه")
check("/market/history/${encodeURIComponent(symbol)}" in api, "٣ والرمزُ مُرمَّزٌ في مسار التاريخ")
print(("FAIL" if fail else "PASS") + " D443 — رسمٌ واحدٌ للسوقين")
sys.exit(fail)
