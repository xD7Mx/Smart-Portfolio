#!/usr/bin/env python3
"""حارسُ D610: «آخرُ اثني عشر شهراً» تُحاكَم إلى السنة المنشورة وإلى مكرّر «تداول»؛ والتطبيعُ صعوداً إلى المنتصف.

    python3 scripts/audit/fv_arbiters_d610.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

import app.services.tadawul_financials as TF
from app.services.fair_value_models import sanity_ttm
TF.read = lambda s: {"page_pe": 11.91} if s == "1835" else {}
# لومي: أرباعٌ 2.84 مليار والسنةُ 1.67
n = []
t, src = sanity_ttm({"revenue": 2.84e9, "net_income": 301e6}, "أربعةُ أرباعٍ حتى 2026-06-30",
                    [{"year": 2025, "revenue": 1.67e9, "net_income": 198e6}], 55e6, 24.72, "4262", n)
check(t["revenue"] == 1.67e9 and src == "سنةُ 2025" and n, "١ لومي: أرباعٌ فوق 1.4 ضعفٍ من السنة ⇒ تُعتمد السنة")
# تمكين: ربحٌ 295 مليوناً والمكرّرُ 11.91 على 43.44 × 26.5 مليون
n = []
t, _ = sanity_ttm({"revenue": 2.66e9, "net_income": 295e6}, "سنةُ 2025", [{"year": 2025, "revenue": 2.66e9}], 26.5e6, 43.44, "1835", n)
check(abs(t["net_income"] - 43.44 * 26.5e6 / 11.91) < 1 and n, "٢ تمكين: ربحٌ يخالف مكرّرَ «تداول» ضعفين فأكثر ⇒ ربحُ «تداول» (96.7 مليوناً)",
      str(round(t["net_income"] / 1e6, 1)))
n = []
t, _ = sanity_ttm({"revenue": 1e9, "net_income": 100e6}, "سنةُ 2025", [{"year": 2025, "revenue": 1e9}], 10e6, 120.0, "1835", n)
check(t["net_income"] == 100e6 and not n, "٣ وربحٌ يوافق المكرّرَ (100 مقابل 100.8) لا يُمسّ")
n = []
t, _ = sanity_ttm({"revenue": 1e9, "net_income": 100e6}, "سنةُ 2025", [{"year": 2025, "revenue": 1e9}], 10e6, 120.0, "9999", n)
check(t["net_income"] == 100e6 and not n, "٤ وبلا مكرّرٍ منشورٍ لا حَكَم ولا اختلاق")
check(TF.parse_page_pe("<td>P/E Ratio</td><td>11.91</td>") == 11.91 and TF.parse_page_pe("<td>P/E Ratio</td><td>-</td>") is None,
      "٥ مكرّرُ «تداول» يُقرأ من الصفحة، والغائبُ لا يُحكَّم")
check(TF.STORE.startswith("tfin2:"), "٦ مخزنٌ جديدٌ للجدول — لا بقايا الوحدات الخاطئة (ولاء)")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
