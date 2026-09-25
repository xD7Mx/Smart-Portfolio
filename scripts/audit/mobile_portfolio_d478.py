#!/usr/bin/env python3
"""حارسُ D478: ملاحظاتُ المالك على الجوّال — المحفظةُ والتوزيعُ النسبيّ وحقلُ الدخول.

    python3 scripts/audit/mobile_portfolio_d478.py
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = open(os.path.join(ROOT, "frontend/src/pages/PortfolioPage.tsx"), encoding="utf-8").read()
L = open(os.path.join(ROOT, "frontend/src/pages/LoginPage.tsx"), encoding="utf-8").read()
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

check(">مركز مغلق<" not in P and "!(h.total_shares > 0)" not in P,
      "١ «الشركاتُ بالمحفظة لا أريدها مركزاً مغلقاً» — كلُّ شركةٍ ببطاقتها الكاملة على الجوّال")
i = P.find('<div className="lg:hidden divide-y"')
mob = P[i:i + 4000] if i >= 0 else ""
check("it.current_weight" in mob, "٢ «التوزيعُ النسبيّ لا يُظهر نسبةَ الامتلاك الحالية» — تظهر في بطاقة الجوّال")
check("onClick={e =>" in L and "el.focus()" in L and "const el = pwRef.current" in L and "ref={pwRef}" in L,
      "٣ «لا يظهر كيبورد الجوال» — لمسةٌ على بطاقة الدخول تركّز الحقل (سفاري لا يفتح اللوحةَ للتركيز التلقائيّ)")
check("el.blur()" in L and "(pointer: fine)" in L and "\n          autoFocus\n" not in L,
      "٤ «باقي تطبيق PWA لا تخرج لوحة المفاتيح» — لا تركيزَ تلقائيَّ على اللمس، واللمسةُ تُحدث تركيزاً جديداً")
print(f"{'FAIL' if fail else 'PASS'} D478 — ملاحظاتُ الجوّال")
sys.exit(fail)
