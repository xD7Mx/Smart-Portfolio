"""التحسينُ القطاعيّ — إسقاطُ إشارةٍ لا تناسب النموذج، لا مؤشّرٌ جديد.

## القاعدة

المسطرةُ العامّة هي الأصل. والقطاعُ لا يضيف مؤشّراً ولا عتبة؛ إنما
**يُسقط إشارةً** لا معنى لها في نموذجه فيُعاد توزيعُ وزنها، أو يستبدل
**مدخلَ** إشارةٍ لا حدَّها:

  · الصناديقُ العقارية — التدفّقُ الحرُّ سالبٌ بنيةً (تشتري عقاراتٍ
    وتوزّع أغلبَ دخلها نظاماً)، فيُسقَط. وقياسُها به يحسم تسعَ نقاطٍ
    عقوبةً على نموذج العمل لا على الأداء.
  · الدوريّةُ (الطاقة · المواد الأساسية) — العائدُ على **آخر سنة** يجعل
    سنةَ القاع حكماً على الشركة: 2.5٪ في القاع مقابل 23٪ عبر الدورة،
    ثمانُ نقاطٍ سببُها اختيارُ السنة. فيُقاس المدخلُ عبر الدورة.

## ما يحرسه هذا الفحص

**أن يبقى ما لم يُقصَد كما كان.** أخطرُ ما في تحسينٍ قطاعيّ أن يتسرّب
إلى غير أهله فيصير المحرّكُ هشّاً: فيُشترط أن تُعطي المسطرةُ العامّة —
بلا قطاعٍ، وبقطاعٍ لا تعديلَ له، وبقطاعٍ مجهول — **الرقمَ نفسَه**.

    python scripts/audit/sector_tuning.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _rows(n=4, **kw):
    b = dict(revenue=1e9, net_income=2e8, equity=2e9,
             operating_cash_flow=2.4e8, free_cash_flow=-3e8,
             debt_ratio=0.45, interest_coverage=4.0, eps=1.0)
    b.update(kw)
    return [dict(b, year=2021 + k) for k in range(n)]


def main() -> int:
    from app.services.scores import (_finance_score_from_periods as sc,
                                     financial_verdict as fv,
                                     _REIT_SECTORS, _CYCLICAL_SECTORS)
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    # ١ — ما لا يخصّه تعديل لا يتغيّر (أهمُّ فحصٍ هنا)
    gen = _rows(free_cash_flow=1.5e8)
    base = sc(gen)
    others = {s: sc(gen, s) for s in
              (None, "الاتصالات", "الرعاية الصحية", "البنوك",
               "إدارة وتطوير العقارات", "قطاعٌ لا وجودَ له", "")}
    t("١ المسطرةُ العامّة لا تتأثّر",
      all(v == base for v in others.values()),
      f"الكلُّ {base}" if all(v == base for v in others.values())
      else str(others))

    # ٢ — الصندوقُ لا يُدان بتدفّقٍ حرٍّ سالبٍ بنيةً
    reit = _rows()
    g, r = sc(reit), sc(reit, next(iter(_REIT_SECTORS)))
    t("٢ الصندوقُ يُعفى من التدفّق الحرّ", r is not None and g is not None
      and r > g, f"عامّة {g} → صندوق {r} (+{(r or 0) - (g or 0)})")

    # ٣ — والحكمُ يتبع الدرجةَ فلا يدين على ما أُعفي منه
    reit_neg = _rows(revenue=1.1e9, free_cash_flow=-5e8,
                     operating_cash_flow=3e8, net_income=2.5e8)
    reit_neg = [dict(p, revenue=1e9 + i * 8e7)
                for i, p in enumerate(reit_neg)]
    v_gen = fv(reit_neg)
    v_reit = fv(reit_neg, next(iter(_REIT_SECTORS)))
    t("٣ الحكمُ يتّسق مع الإعفاء", v_gen != v_reit,
      f"عامّة «{v_gen[:26]}» → صندوق «{v_reit[:26]}»")

    # ٤ — الدوريّةُ تُقاس عبر الدورة لا في سنة القاع
    cyc = [dict(_rows()[0], year=2021 + k, net_income=n)
           for k, n in enumerate([6e8, 6e8, 6e8, 5e7])]
    g2 = sc(cyc)
    c2 = sc(cyc, next(iter(_CYCLICAL_SECTORS)))
    t("٤ الدوريّةُ تُقاس عبر الدورة", c2 is not None and g2 is not None
      and c2 > g2, f"آخرُ سنة {g2} → عبر الدورة {c2} (+{(c2 or 0) - (g2 or 0)})")

    # ٥ — وسنةُ القمّة لا تُجمَّل: الدورةُ تخفضها كما ترفع القاع
    peak = [dict(_rows()[0], year=2021 + k, net_income=n)
            for k, n in enumerate([5e7, 5e7, 5e7, 6e8])]
    t("٥ الدورةُ تخفض القمّةَ كما ترفع القاع",
      (sc(peak, next(iter(_CYCLICAL_SECTORS))) or 0) < (sc(peak) or 0),
      f"آخرُ سنة {sc(peak)} → عبر الدورة "
      f"{sc(peak, next(iter(_CYCLICAL_SECTORS)))}")

    # ٦ — دون ثلاث سنواتٍ لا دورةَ تُقاس: يُعاد إلى آخر سنة بلا اختلاق
    short = [dict(_rows()[0], year=2024, net_income=5e7),
             dict(_rows()[0], year=2025, net_income=5e7)]
    t("٦ دون ثلاثِ سنواتٍ لا يُختلَق متوسّط",
      sc(short, next(iter(_CYCLICAL_SECTORS))) == sc(short),
      f"سنتان → {sc(short)} في الحالين")

    print("═" * 62)
    print("  التحسينُ القطاعيّ — ولا يتسرّب إلى غير أهله")
    print("═" * 62)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:34} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 62)
    print("  ✔ كلُّ قطاعٍ بمسطرته، والعامّةُ كما كانت." if not bad
          else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
