#!/usr/bin/env python3
"""حارسُ D479: التقريرُ يطبع الإشارةَ قبل رقمها، وعناوينُ جدوله تُقرأ مطبوعة.

    python3 scripts/audit/report_bidi_d479.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F = open(os.path.join(ROOT, "frontend/src/components/reports/ReportDocument.tsx"), encoding="utf-8").read()
B = open(os.path.join(ROOT, "backend/app/services/saqr_report.py"), encoding="utf-8").read()
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

check(F.count('<bdi dir="ltr"') >= 2 and "direction:ltr;unicode-bidi:isolate" in B and '<bdi dir="ltr"' in B,
      "١ الرقمُ وإشارتُه معزولان — لا «11,164+» ولا «(9.1%-) 446-» في سطرٍ عربيّ (الواجهةُ والخادم)")
check('background: NAVY, color: "#fff"' not in F and "thead tr{{background:{NAVY};color:#fff}}" not in B,
      "٢ عناوينُ جدول المراكز داكنةٌ على فاتح — لا أبيضَ على خلفيةٍ لا تُطبع")
print(f"{'FAIL' if fail else 'PASS'} D479 — التقرير")
sys.exit(fail)
