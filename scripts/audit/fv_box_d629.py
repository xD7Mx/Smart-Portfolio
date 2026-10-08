#!/usr/bin/env python3
"""حارسُ D629: صندوقُ «السعر العادل» لا ينتظر نداءَ النماذج متى حمل التحليلُ الرقم (رآه المالك في سدافكو: هيكلٌ لا يزول)."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
src = (ROOT / "frontend/src/components/analysis/AnalysisPanel.tsx").read_text()
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
check("data.fair_value ?? fvm?.value ?? null" in src, "١ الرقمُ من التحليل أوّلاً (رقمُ المحرّك بعد شروط النشر)")
check("const fvWaiting = fvmLoading && data.fair_value == null" in src, "٢ الهيكلُ فقط حين لا رقمَ في التحليل")
check("{fvmLoading ? (" not in src and "{fvWaiting ? (" in src, "٣ لا يُشترط انتهاءُ نداء النماذج لعرض الرقم")
check("data.fair_value != null ? (data.fair_value_upside_pct" in src, "٤ والشريطُ والنسبةُ من مصدر الرقم نفسه")
F = (ROOT / "frontend/src/components/analysis/FairValuePanel.tsx").read_text()
check("withheld={data.fair_value == null ? data.fair_value_unavailable_reason : null}" in src
      and "if (withheld) return" in F and F.find("if (withheld) return") < F.find("if (isLoading) return"),
      "٥ ما حجبه التحليلُ لا تُظهره التفاصيلُ رقماً — بل سببَه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
