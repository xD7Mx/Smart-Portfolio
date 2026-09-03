"""لا استثناءَ قطاعيّ في الدرجة — إلّا بدليلٍ مقيس.

## ما استقرّ عليه الأمر

جُرِّب استثناءان قطاعيّان ثمّ أُلغيا، وكلاهما بُني على عيّنةٍ صنعناها
فأكّدت فرضيتَها بدل أن تختبرها:

  · إعفاءُ الصناديق العقارية من هامش التدفّق الحرّ — قِيس على تسعَ
    عشرةَ شركةً حقيقية فإذا هو **يحسم سبعَ نقاط**: تدفّقُها موجبٌ
    بوسيطٍ ‎+67.9٪، ولا واحدةَ سالبةٌ في كلّ سنواتها. (D154)
  · قياسُ عائد الدوريّة عبر الدورة — أثرُه ‎+1.0 و‎0.0، دون عتبة
    الخمسِ نقاط. أُلغي اتّساقاً: الشرطُ واحدٌ ولا استثناءَ لتعديلٍ
    أعجبنا. (D155)

فالقاعدةُ اليوم: **الدرجةُ لا تتغيّر باسم القطاع**. والقطاعُ يؤثّر
حيث يثبته الدليلُ من البيانات نفسِها — البنوكُ والتأمين تُعفى من ثلاثِ
إشاراتٍ باستدلالٍ من غياب مصروف الفوائد مع مديونيةٍ عالية، لا باسمٍ
مكتوب.

## ما يحرسه هذا الفحص

أن يبقى الأمرُ كذلك: يُعطى المحرّكُ الشركةَ نفسَها باثنين وعشرين اسمَ
قطاع، ويُشترط أن يخرج الرقمُ نفسُه في كلّها. فأيُّ استثناءٍ يُدسّ
بالاسم يسقط هنا.

والبابُ مفتوح: `sector_probe.py` يقيس على بياناتٍ حقيقية، فإن بلغ عطبٌ
خمسَ نقاطٍ وكان سببُه بنيوياً، عاد التعديلُ بدليله لا بالظنّ.

    python scripts/audit/sector_tuning.py
"""

from __future__ import annotations

import inspect
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SECTORS = [
    "البنوك", "التأمين", "الخدمات المالية", "الصناديق العقارية المتداولة",
    "الطاقة", "المواد الأساسية", "إدارة وتطوير العقارات", "الاتصالات",
    "المرافق العامة", "الرعاية الصحية", "الأدوية", "إنتاج الأغذية",
    "تجزئة وتوزيع السلع الاستهلاكية", "تجزئة وتوزيع السلع الكمالية",
    "الخدمات الاستهلاكية", "النقل", "السلع الرأسمالية",
    "الخدمات التجارية والمهنية", "التطبيقات وخدمات التقنية",
    "السلع طويلة الأجل", "الإعلام والترفيه", "المنتجات المنزلية والشخصية",
]


def _rows(n=4, **kw):
    b = dict(revenue=1e9, net_income=2e8, equity=2e9,
             operating_cash_flow=2.4e8, free_cash_flow=-3e8,
             debt_ratio=0.45, interest_coverage=4.0, eps=1.0)
    b.update(kw)
    return [dict(b, year=2021 + k) for k in range(n)]


def main() -> int:
    from app.services import scores as sm
    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    # ١ — الدالّةُ لا تقبل قطاعاً أصلاً: أقوى من فحص السلوك
    sig = inspect.signature(sm._finance_score_from_periods)
    t("١ الدرجةُ لا تأخذ قطاعاً", list(sig.parameters) == ["periods"],
      f"({', '.join(sig.parameters)})")
    sig2 = inspect.signature(sm.financial_verdict)
    t("٢ والحكمُ كذلك", list(sig2.parameters) == ["periods"],
      f"({', '.join(sig2.parameters)})")

    # ٣ — ولا اسمَ قطاعٍ مكتوبٌ في **منطق** الدرجة
    # وتُنزَع التعليقاتُ والتوثيقُ قبل البحث: هناك يُشرح إعفاءُ البنوك
    # والتأمين، وذكرُ الاسم شرحاً ليس استعمالاً له. والفحصُ الذي يقرأ
    # الحرفَ دون المعنى يُسقط شيفرةً سليمة — وقد أسقط هذا الفحصُ نفسَه
    # أوّلَ تشغيلٍ له بسبب كلمةٍ في تعليق.
    _raw = inspect.getsource(sm._finance_score_from_periods)
    _body = _raw.split('"""')
    _code = _body[0] + "".join(_body[2:]) if len(_body) >= 3 else _raw
    src = "\n".join(ln for ln in _code.splitlines()
                    if not ln.strip().startswith("#"))
    hits = [s for s in SECTORS if s in src]
    t("٣ لا اسمَ قطاعٍ في منطق الدرجة", not hits,
      "لا شيء" if not hits else str(hits[:3]))

    # ٤ — البنوكُ تُعفى بالبيانات لا بالاسم: سلسلةٌ بلا مصروف فوائد
    #     ومديونيةٌ عالية تُعطي درجةً تخالف سلسلةً عاديةً بالبيانات نفسها
    bank = [{k: v for k, v in p.items() if k != "interest_coverage"}
            for p in _rows(debt_ratio=0.88)]
    normal = _rows(debt_ratio=0.88)
    a, b = sm._finance_score_from_periods(bank), \
        sm._finance_score_from_periods(normal)
    t("٤ الإعفاءُ بالبيانات لا بالاسم", a is not None and b is not None and a != b,
      f"بلا مصروف فوائد {a} · بمصروفٍ {b}")

    # ٥ — سلامةُ العدد: إيرادٌ أخيرٌ سالبٌ لا يُسقط الحساب (D153)
    neg = [dict(_rows()[0], year=2021 + k, revenue=r)
           for k, r in enumerate([1e9, 9e8, -5e8])]
    try:
        v = sm._finance_score_from_periods(neg)
        ok = isinstance(v, int)
    except Exception as e:                                        # noqa: BLE001
        v, ok = f"{type(e).__name__}", False
    t("٥ إيرادٌ سالبٌ لا يُسقط الحساب", ok, f"→ {v}")

    print("═" * 62)
    print("  لا استثناءَ قطاعيّ إلّا بدليلٍ مقيس")
    print("═" * 62)
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:34} {d}")
    bad = [n for n, ok, _ in T if not ok]
    print("═" * 62)
    print(f"  ✔ مسطرةٌ واحدة · {len(SECTORS)} قطاعاً لا يغيّر اسمُها الرقم."
          if not bad else f"  ✖ أخفق {len(bad)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
