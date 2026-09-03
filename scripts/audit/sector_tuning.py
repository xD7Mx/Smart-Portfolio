"""التحسينُ القطاعيّ — إسقاطُ إشارةٍ لا تناسب النموذج، لا مؤشّرٌ جديد.

## القاعدة

المسطرةُ العامّة هي الأصل. والقطاعُ لا يضيف مؤشّراً ولا عتبة؛ إنما
**يُسقط إشارةً** لا معنى لها في نموذجه فيُعاد توزيعُ وزنها، أو يستبدل
**مدخلَ** إشارةٍ لا حدَّها:

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
                                     _CYCLICAL_SECTORS)
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

    # ٢ — لا إعفاءَ للصناديق العقارية: القياسُ نقضه (D154)
    # على تسعَ عشرةَ شركةً حقيقية كان الإعفاءُ يحسم سبعَ نقاط. فيُشترط
    # ألّا يعود: القطاعُ يُعطي ما تُعطيه المسطرةُ العامّة.
    reit = _rows()
    t("٢ لا إعفاءَ منقوضٌ يعود",
      sc(reit, "الصناديق العقارية المتداولة") == sc(reit),
      f"عامّة {sc(reit)} · صندوق {sc(reit, 'الصناديق العقارية المتداولة')}")

    # ٣ — الدوريّةُ تُقاس عبر الدورة لا في سنة القاع
    cyc = [dict(_rows()[0], year=2021 + k, net_income=n)
           for k, n in enumerate([6e8, 6e8, 6e8, 5e7])]
    g2 = sc(cyc)
    c2 = sc(cyc, next(iter(_CYCLICAL_SECTORS)))
    t("٣ الدوريّةُ تُقاس عبر الدورة", c2 is not None and g2 is not None
      and c2 > g2, f"آخرُ سنة {g2} → عبر الدورة {c2} (+{(c2 or 0) - (g2 or 0)})")

    # ٤ — وسنةُ القمّة لا تُجمَّل: الدورةُ تخفضها كما ترفع القاع
    peak = [dict(_rows()[0], year=2021 + k, net_income=n)
            for k, n in enumerate([5e7, 5e7, 5e7, 6e8])]
    t("٤ الدورةُ تخفض القمّةَ كما ترفع القاع",
      (sc(peak, next(iter(_CYCLICAL_SECTORS))) or 0) < (sc(peak) or 0),
      f"آخرُ سنة {sc(peak)} → عبر الدورة "
      f"{sc(peak, next(iter(_CYCLICAL_SECTORS)))}")

    # ٥ — دون ثلاث سنواتٍ لا دورةَ تُقاس: يُعاد إلى آخر سنة بلا اختلاق
    short = [dict(_rows()[0], year=2024, net_income=5e7),
             dict(_rows()[0], year=2025, net_income=5e7)]
    t("٥ دون ثلاثِ سنواتٍ لا يُختلَق متوسّط",
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
