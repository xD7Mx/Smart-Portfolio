"""سقفُ التغطية الممكن لكلّ نمط — يُقاس ولا يُقدَّر.

## لماذا

الدرجةُ تنكمش نحو الخمسين بجذر التغطية، والتغطيةُ تُنسب إلى **ما يمكن
بلوغه** من مصدرنا لا إلى كمالٍ نظريّ (‏D092). وذلك السقفُ رقمٌ لكلّ نمط
في `archetype_spec.ATTAINABLE` — ورقمٌ في ملفٍّ يشيخ بصمت: يُضاف مؤشّرٌ
إلى خطّ السمات فيرتفع السقفُ الحقيقيّ ويبقى المكتوبُ كما هو، فتُخصم من
الشركات درجاتٌ بلا سبب.

فهذا السكربتُ يُعيد قياسه: يمرّر قوائمَ **كاملةَ البنود** — فيها كلُّ سطرٍ
قد يحتاجه أيُّ مؤشّر — على خطّ السمات لكلّ نمط، ثم يقرأ نسبةَ الوزن الذي
أمكن حسابُه فعلاً. فما بقي غائباً بعد قوائمَ كاملة فهو نقصٌ في مصدرنا لا
في الشركة، وهو تعريفُ السقف.

## التشغيل

    python scripts/audit/attainable.py

ويطبع الجدولَ جاهزاً للّصق، ويُنبّه إن خالف المكتوبَ في المواصفة.
"""

from __future__ import annotations

import sys

import os

# ══ السكربتُ يعرف موضعَه ══
# كان يُدرج `/app` في رأس المسار، فيدهس `PYTHONPATH` ويقرأ الشيفرةَ
# المثبَّتة بدل التي يُفحَص بها — فيُفحص شيءٌ غيرُ المقصود. والترتيبُ
# هنا مقصود: يُدرج `/app` أوّلاً ثم جذرُ السكربت، فيستقرّ جذرُه في
# الصدارة ويسبق المثبَّت.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# قطاعٌ حقيقيّ لكلّ نمط — الحلُّ يمرّ بالخريطة نفسها التي يمرّ بها التطبيق.
ARCH_SECTOR = {
    "bank": "البنوك",
    "insurance": "التأمين",
    "financial": "التمويل",
    "reit": "الصناديق العقارية المتداولة",
    "commodity": "الطاقة",
    "re_developer": "العقارات",
    "contracting": "المقاولات",
    "consumer_defensive": "الأغذية",
    "consumer_cyclical": "التجزئة",
    "capital_infra": "الخدمات",
    "asset_light": "التقنية",
}


def _full_statements() -> list[dict]:
    """قوائمُ كاملةُ البنود لثماني سنوات — كلُّ سطرٍ قد يحتاجه أيُّ مؤشّر.

    الأرقامُ متّسقةٌ داخلياً (ربحٌ موجب · نموٌّ معتدل · رافعةٌ معقولة) حتى
    لا يسقط مؤشّرٌ لسببٍ منطقيّ فيُحسب نقصاً في المصدر.
    """
    rows = []
    for i in range(8):
        rev = 2600 + 120 * i
        ni = 900 + 70 * i
        at = 52000 + 3000 * i
        rows.append({
            "year": 2018 + i,
            "net_income": ni, "total_equity": 7000 + 400 * i,
            "total_assets": at, "revenue": rev,
            "gross_profit": rev * 0.38, "operating_income": ni * 1.3,
            "operating_expense": 820 + 25 * i,
            "operating_cash_flow": ni * 1.2, "capex": -rev * 0.05,
            "depreciation": rev * 0.04, "ebitda": ni * 1.6,
            "cash": at * 0.08, "inventory": rev * 0.12,
            "current_assets": rev * 0.9, "current_liabilities": rev * 0.6,
            "total_debt": at * 0.30, "total_liabilities": at * 0.60,
            "interest_expense": rev * 0.03,
            "interest_income": 2900 + 130 * i,
            "provision_for_loan_losses": 150 + 5 * i,
            "net_loans": 40000 + 2200 * i, "loans": 40000 + 2200 * i,
            "premiums_earned": 1200 + 60 * i, "claims_incurred": 800 + 35 * i,
            "shares_outstanding": 1000,
            "dividends_paid": -ni * 0.5,
        })
    return rows


def main() -> int:
    from app.services.four_scores import build_company_features
    from app.data.archetype_spec import SCORECARDS, ATTAINABLE

    periods = _full_statements()
    info = {"beta": 1.0, "current_price": 40.0, "dividend_per_share": 2.0}
    drift = []

    print("═" * 62)
    print("  سقفُ التغطية الممكن — مقيساً بقوائمَ كاملة")
    print("═" * 62)
    print(f"  {'النمط':22}{'مقيس':>8}{'مكتوب':>8}   الغائبُ رغم اكتمال القوائم")
    print("─" * 62)

    measured = {}
    for arch, card in sorted(SCORECARDS.items()):
        if card.get("abstain"):
            continue
        feats, _, _ = build_company_features(
            periods, info=dict(info), sector=ARCH_SECTOR.get(arch))
        tot = got = 0.0
        gone = []
        for key, _label, weight, *_rest in card["metrics"]:
            tot += weight
            v = feats.get(key)
            v = v.get("value") if isinstance(v, dict) else v
            if isinstance(v, (int, float)):
                got += weight
            else:
                gone.append(key)
        val = round(got / tot, 2) if tot else 1.0
        measured[arch] = val
        wrote = ATTAINABLE.get(arch)
        flag = ""
        if wrote is None or abs(wrote - val) > 0.05:
            flag = "  ←"
            drift.append((arch, wrote, val))
        print(f"  {arch:22}{val:>8}{str(wrote):>8}{flag}   {' · '.join(gone) or '—'}")

    print("\n  الجدولُ جاهزاً للّصق في archetype_spec.py:\n")
    print("ATTAINABLE = {")
    for a in sorted(measured):
        print(f'    "{a}": {measured[a]:.2f},')
    print("}")

    if drift:
        print(f"\n  ✖ {len(drift)} نمطاً خالف المكتوب — السقفُ شاخ:")
        for a, w, v in drift:
            print(f"      {a}: مكتوب {w} · مقيس {v}")
        return 1
    print("\n  ✔ المكتوبُ يطابق المقيس.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
