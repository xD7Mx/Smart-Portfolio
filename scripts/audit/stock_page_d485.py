#!/usr/bin/env python3
"""حارسُ D485: السعرُ العادل والجودةُ المالية في «تقييم الأداء» وحده، برقمٍ واحد.

    python3 scripts/audit/stock_page_d485.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rd = lambda p: open(os.path.join(ROOT, "frontend/src", p), encoding="utf-8").read()
V, A = rd("components/market/StockView.tsx"), rd("components/analysis/AnalysisPanel.tsx")
H, F = rd("components/analysis/HealthPanel.tsx"), rd("components/analysis/FairValuePanel.tsx")
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

check("<FairValuePanel" not in V and "<HealthPanel" not in V,
      "١ «أصبحوا مكرّرين» — لا نسخةَ في «نظرة عامة»")
check('<HealthPanel symbol={symbol} quality=' in A and "<FairValuePanel symbol={symbol}" in A
      and 'setOpen(open === "fv"' in A and 'setOpen(open === "hl"' in A,
      "٢ مكانُهما «تقييم الأداء»، والتفاصيلُ تُفتح بلمسةٍ على الصندوق")
check("ChevronDown" not in A + H + F, "٣ «الضغطُ خفيٌّ وليس سهماً» — لا أسهم")
check("fvm?.value ?? data.fair_value" in A and 'queryKey: ["fvm", sym4]' in A,
      "٤ رقمٌ واحد: الصندوقُ وتفاصيلُه من المحرّك المرجَّح نفسِه")
check("من 5" not in H and "toFixed(2)" not in H and "<SafetyBar" in H and "quality" in H,
      "٥ الجودةُ المالية نسبةٌ من نموذجنا بشريط السلامة — لا «من خمسة»")
check("#ffffff" in F and "border-t-[6px]" not in F and "h-1.5 rounded-full" in F,
      "٦ أشرطةُ السعر العادل بتصميم شريط السلامة — بلا مثلثات")
print(f"{'FAIL' if fail else 'PASS'} D485 — صفحةُ السهم بلا تكرارٍ ولا تناقض")
sys.exit(fail)
