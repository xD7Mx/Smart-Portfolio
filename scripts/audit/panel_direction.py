"""اتّجاهُ قراءة المؤشّر يوافق معناه — حارسُ D157.

## العطب

`earnings_stability` و`margin_stability` و`margin_stability_gross` كلُّها
**معامِلُ تذبذّب** موثَّقٌ في `financial_features` بنصّه «أقل = أكثر
استقراراً». وكان مجلسُ الخبراء يقرؤها `higher` — فيعدّ شركةً تذبذبُها
سبعون بالمئة **ممتازةً** وأخرى أربعين **ضعيفة**. قلبُ الحقيقة على
خمسٍ وعشرين شركةَ تأمينٍ وغيرِها.

## كيف يُمسَك

لا بقائمةِ أسماءٍ تُكتب باليد — تلك تشيخ. بل **من وصف الميزة نفسِه**:
`financial_features` يوثّق كلَّ ميزةٍ بجملةٍ عربية، ومن قال وصفُه
«أقل = أكثر» فاتّجاهُه `lower` حتماً. فالمصدرُ واحدٌ للمعنى والفحص.

    python scripts/audit/panel_direction.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# جملةٌ في وصف الميزة تدلّ على أن الأقلَّ أفضل
LOWER_IS_BETTER = ("أقل = أكثر", "أقلّ = أكثر", "كلما قلّ", "كلما زاد التذبذب")


def _feature_docs() -> dict[str, str]:
    """وصفُ كلّ ميزةٍ كما يكتبه `financial_features` — بتشغيله على قوائمَ
    كاملةٍ فتُبنى الأوصافُ كلُّها، لا بقراءة نصِّ الملفّ."""
    from app.services.financial_features import compute_features
    per = [{"year": 2019 + k, "revenue": 9e9 + k * 2e8, "net_income": 1e9,
            "equity": 1e10, "eps": 3.0, "operating_cash_flow": 1.2e9,
            "capex": -2e8, "depreciation": 2e8, "total_debt": 1e9,
            "ending_cash": 5e8, "shares_outstanding": 3.3e8,
            "operating_income": 1.3e9, "total_assets": 1.4e10,
            "gross_profit": 3e9, "total_liabilities": 4e9,
            "interest_expense": 5e7, "dividends_paid": -3e8}
           for k in range(5)]
    # `compute_features` تُعيد {اسم: {"value":…, "note": وصفٌ عربيّ}}
    return {k: str((v or {}).get("note") or "")
            for k, v in (compute_features(per) or {}).items()}


def main() -> int:
    from app.services.expert_panel import _ARCH_PILLARS
    docs = _feature_docs()
    if not docs:
        print("✖ تعذّر بناءُ أوصاف الميزات — لا يُحكم بلا مرجع.")
        return 2

    wrong, unknown, checked = [], [], 0
    for arch, rows in _ARCH_PILLARS.items():
        for row in rows:
            key, _label, _unit, direction = row[0], row[1], row[2], row[3]
            doc = docs.get(key)
            if doc is None:
                unknown.append(f"{arch}/{key}")
                continue
            if any(p in doc for p in LOWER_IS_BETTER):
                checked += 1
                if direction != "lower":
                    wrong.append(f"{arch}/{key}: «{direction}» ووصفُها "
                                 f"«أقل = أكثر استقراراً»")

    print("═" * 62)
    print("  اتّجاهُ القراءة يوافق معنى الميزة")
    print("═" * 62)
    print(f"  أنماطٌ مفحوصة {len(_ARCH_PILLARS)} · "
          f"ميزاتٌ «الأقلُّ أفضل» {checked} · "
          f"بلا وصفٍ في المصدر {len(unknown)}")
    if unknown:
        # ليست إخفاقاً: بعضُ الميزات تُبنى في مسارٍ آخر (سِمات قطاعية).
        print(f"    (‏{', '.join(unknown[:6])}{'…' if len(unknown) > 6 else ''})")
    if wrong:
        print("\n  ✖ اتّجاهٌ مقلوب:")
        for w in wrong:
            print(f"    · {w}")
    print("═" * 62)
    print("  ✔ لا مؤشّرَ يُقرأ عكسَ معناه." if not wrong
          else f"  ✖ أخفق {len(wrong)}")
    return 0 if not wrong else 1


if __name__ == "__main__":
    sys.exit(main())
