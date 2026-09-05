#!/usr/bin/env python3
"""هل بوابة الـ25% تقيس جودة المحرك، أم تفاؤل المحللين؟

تجربة مُصطنعة يمكن إعادة إنتاجها: نفترض محرّكاً **مثالياً** يُخرج القيمة
الجوهرية الحقيقية بالضبط (خطأ صفر)، وأهداف محللين مبنية على نفس القيمة
الحقيقية مضافاً إليها تفاؤل بنيوي وضجيج. ثم نقيس البوابات الثلاث.

إن رسب المحرك المثالي في G1، فالبوابة لا تقيس المحرك.
"""
from __future__ import annotations
import random
from statistics import median

random.seed(7)
N = 149  # حجم عيّنة المواصفة


def spearman(a, b):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for p, i in enumerate(o): r[i] = p + 1
        return r
    ra, rb = rk(a), rk(b); n = len(a)
    ma, mb = sum(ra)/n, sum(rb)/n
    num = sum((x-ma)*(y-mb) for x, y in zip(ra, rb))
    den = (sum((x-ma)**2 for x in ra)*sum((y-mb)**2 for y in rb))**0.5
    return num/den if den else float("nan")


def run(optimism: float, target_noise: float, engine_error: float, label: str):
    dev, ratio, vp, tp = [], [], [], []
    for _ in range(N):
        true_v = random.lognormvariate(0, 0.35)          # القيمة الجوهرية الحقيقية
        price  = true_v * random.lognormvariate(0.20, 0.25)  # السوق أغلى من الجوهر وسطياً
        engine = true_v * random.lognormvariate(0, engine_error)
        target = price * (1 + optimism) * random.lognormvariate(0, target_noise)
        dev.append(abs(engine - target)/target)
        ratio.append(engine/target); vp.append(engine/price); tp.append(target/price)
    med_r = median(ratio)
    spread = median(abs(r - med_r)/med_r for r in ratio)
    g1, g3 = median(dev), spearman(vp, tp)
    print(f"{label:<44} G1 {g1:6.1%} {'اجتاز' if g1 <= .25 else 'رسب  '} | "
          f"G2 {spread:6.1%} {'اجتاز' if spread <= .25 else 'رسب  '} | G3 {g3:5.2f}")


print("محرّك خطؤه صفر — القيمة الحقيقية بالضبط:")
run(0.136, 0.12, 0.001, "  تفاؤل محللين 13.6% (المقدَّر من بياناتك)")
run(0.00,  0.12, 0.001, "  تفاؤل صفر (أهداف = السعر)")
print("\nمحرّك واقعي بخطأ تقدير 20%:")
run(0.136, 0.12, 0.20,  "  تفاؤل 13.6%")
run(0.00,  0.12, 0.20,  "  تفاؤل صفر")
print("\nمحرّك رديء بخطأ 60% لكنه غير متحفّظ (يقلّد السعر):")
run(0.136, 0.12, 0.60,  "  تفاؤل 13.6%")
