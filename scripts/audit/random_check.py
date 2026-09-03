"""اختبارٌ عشوائيّ — شركاتٌ لم أُصمّمها، ومدخلاتٌ لم أتوقّعها.

## لماذا

قال المالك: «أعد الاختبار العشوائيّ كمستثمر». وفحصُ الرتبة
(`rank_check.py`) يبني شركاتٍ بتدرّجٍ **أنا** صنعتُه، فيقيس ما توقّعتُه.
والعطبُ لا يسكن ما نتوقّعه.

فهذا يولّد مئاتِ الشركات بأرقامٍ عشوائية — بعضُها مستحيلٌ عمداً: إيرادٌ
صفر، حقوقُ ملكيةٍ سالبة، سنةٌ واحدة، أرقامٌ ضخمة، بنودٌ ناقصة، نموٌّ
سالب — ثم يسأل:

  · **أيُنتِج المحرّكُ رقماً خارج ‎[0, 100]؟**  رقمٌ كهذا يظهر في الشاشة
    ولا يعني شيئاً.
  · **أيسقط بخطأٍ غير معالَج؟**  شركةٌ واحدة تُسقط الصفحة.
  · **أيُخرج درجةً على تغطيةٍ دون الحدّ؟**  وهو ما وُضع الحدُّ لمنعه.
  · **أيَعِد بمخرَجٍ ثم يخالفه؟**  درجةٌ مع سببِ امتناع، أو امتناعٌ بلا سبب.
  · **أيشتعل خطٌّ أحمر بلا سلسلةٍ تُثبته؟**  إدانةٌ على بيانٍ ناقص.

وهي أسئلةُ مهندس اختبار الحدود في المجلس: يُختبَر بالمستحيل قبل الممكن.

## التشغيل

    python scripts/audit/random_check.py [عدد]
"""

from __future__ import annotations

# ══ فحصٌ لا يكتب في بيانات المالك ══ (D160)
# الوحداتُ تقرأ مسارَ المخزن عند **تحميلها**، فيُحوَّل في رأس الوحدة قبل
# أيّ استيرادٍ من `app` — بما فيها الاستيراداتُ المؤجَّلة داخل الدوالّ.
# وسكربتُ فحصٍ يغيّر حالةً ليس فحصاً.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX


import random
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

SECTORS = [
    "البنوك", "التأمين", "التمويل", "الصناديق العقارية المتداولة",
    "الطاقة", "العقارات", "المقاولات", "الأغذية", "التجزئة",
    "الخدمات", "التقنية", "النقل", "التعليم", "الاتصالات",
    "الأسمنت", "الرعاية الصحية", "الكيماويات",
    # وقطاعاتٌ لا نعرفها — يجب أن تمتنع لا أن تُقاس بمسطرة غيرها
    "Widgets Unlimited", "", "قطاعٌ لم يُسمَّ بعد",
]


def _rand_periods(rng: random.Random) -> list[dict]:
    """قوائمُ عشوائية — وبعضُها مستحيلٌ عمداً."""
    n = rng.choice([1, 2, 3, 5, 8, 8, 8])           # سلاسلُ قصيرة وطويلة
    scale = rng.choice([1e2, 1e6, 1e9, 1e12])
    rows = []
    for i in range(n):
        rev = rng.choice([0.0, rng.uniform(-1, 5) * scale, scale])
        ni = rev * rng.uniform(-0.6, 0.35)
        assets = abs(rev) * rng.uniform(0.5, 12) or scale
        eq = assets * rng.uniform(-0.3, 0.8)        # سالبةٌ أحياناً عمداً
        row = {
            "year": 2018 + i,
            "revenue": rev, "net_income": ni,
            "total_equity": eq, "equity": eq,
            "total_assets": assets,
            "total_liabilities": assets - eq,
            "gross_profit": rev * rng.uniform(-0.2, 0.6),
            "operating_income": ni * rng.uniform(0.5, 2.0),
            "cost_of_revenue": rev * rng.uniform(0.3, 1.2),
            "operating_cash_flow": ni * rng.uniform(-2, 3),
            "free_cash_flow": ni * rng.uniform(-2, 2),
            "capex": -abs(rev) * rng.uniform(0, 0.4),
            "depreciation": abs(rev) * rng.uniform(0, 0.2),
            "ebitda": ni * rng.uniform(-1, 3),
            "cash": assets * rng.uniform(0, 0.5),
            "inventory": abs(rev) * rng.uniform(0, 0.6),
            "current_assets": abs(rev) * rng.uniform(0, 2),
            "current_liabilities": abs(rev) * rng.uniform(0, 2),
            "total_debt": assets * rng.uniform(0, 1.4),
            "interest_expense": assets * rng.uniform(0, 0.2),
            "shares_outstanding": rng.choice(
                [0, 1000, 1000 * (1.2 ** i), rng.uniform(1, 1e9)]),
            "dividends_paid": -abs(ni) * rng.uniform(0, 3),
            "net_interest_income": rev * rng.uniform(-0.5, 1.2),
            "interest_income": rev * rng.uniform(0, 2),
            "operating_expense": rev * rng.uniform(0, 1.5),
            "credit_loss_provision": assets * rng.uniform(-0.05, 0.2),
            "net_loans": assets * rng.uniform(0, 1.1),
            "gain_on_asset_sale": ni * rng.uniform(-1, 1),
        }
        # بنودٌ تسقط عشوائياً — المصدرُ لا يُرسل كلَّ شيءٍ دائماً
        for k in list(row):
            if k != "year" and rng.random() < 0.18:
                row[k] = None
        rows.append(row)
    return rows


def main(argv: list[str]) -> int:
    from app.services.four_scores import build_company_features
    from app.services import spec_score, red_lines, governance_pillar

    n = int(argv[0]) if argv and argv[0].isdigit() else 400
    rng = random.Random(20260827)
    fails: list[str] = []
    scored = abstained = crashed = 0

    for i in range(n):
        sector = rng.choice(SECTORS)
        periods = _rand_periods(rng)
        own = rng.choice([
            None, {}, {"insiders": rng.uniform(0, 100), "institutions": 5.0,
                       "public": rng.uniform(0, 100)},
            {"insiders": None, "institutions": None, "public": None}])
        try:
            feats, _info, _q = build_company_features(
                periods, info={"beta": rng.uniform(0, 3)}, sector=sector)
            sp = spec_score.compute(feats, sector)
            lines = red_lines.check(feats, periods, sp.archetype)
            gov = governance_pillar.build(feats, periods, own)
        except Exception as e:                                    # noqa: BLE001
            crashed += 1
            fails.append(f"#{i} «{sector}» سقط: {type(e).__name__}: {e}")
            continue

        # ── الدرجةُ داخل المدى أو معدومة ──
        if sp.score is not None:
            scored += 1
            if not (0.0 <= sp.score <= 100.0):
                fails.append(f"#{i} «{sector}» درجةٌ خارج المدى: {sp.score}")
            if sp.abstain_reason:
                fails.append(f"#{i} درجةٌ ({sp.score}) مع سببِ امتناع")
            if sp.coverage < spec_score.MIN_COVERAGE:
                fails.append(f"#{i} درجةٌ على تغطية {sp.coverage:.2f} "
                             f"دون الحدّ {spec_score.MIN_COVERAGE}")
            if len(sp.metrics) < spec_score.MIN_PILLARS:
                fails.append(f"#{i} درجةٌ على {len(sp.metrics)} ركنٍ فقط")
        else:
            abstained += 1
            if not sp.abstain_reason:
                fails.append(f"#{i} «{sector}» امتناعٌ بلا سبب")

        # ── كلُّ رتبةٍ داخل المدى ──
        for m in sp.metrics:
            if not (0.0 <= m.score <= 100.0):
                fails.append(f"#{i} رتبةُ «{m.key}» خارج المدى: {m.score}")
            if m.value != m.value:                       # NaN
                fails.append(f"#{i} قيمةُ «{m.key}» ليست رقماً")

        # ── الخطُّ الأحمر لا يُدين على بيانٍ ناقص ──
        ids = {r["id"] for r in lines}
        nis = [p.get("net_income") for p in periods
               if isinstance(p.get("net_income"), (int, float))]
        if "loss_streak" in ids and len(nis) < 3:
            fails.append(f"#{i} «loss_streak» على {len(nis)} سنةً فقط")
        ocf = [p.get("operating_cash_flow") for p in periods
               if isinstance(p.get("operating_cash_flow"), (int, float))]
        if "no_cash" in ids and len(ocf) < 3:
            fails.append(f"#{i} «no_cash» على {len(ocf)} سنواتٍ فقط")
        for r in lines:
            if not r.get("message"):
                fails.append(f"#{i} خطٌّ أحمر «{r['id']}» بلا رسالة")

        # ── ركنُ الحوكمة ──
        if gov.get("score") is not None and not (0 <= gov["score"] <= 100):
            fails.append(f"#{i} درجةُ حوكمةٍ خارج المدى: {gov['score']}")
        if gov.get("score") is None and gov.get("pillars"):
            fails.append(f"#{i} حوكمةٌ بلا درجةٍ ومعها أركان")

    print("═" * 70)
    print(f"  اختبارٌ عشوائيّ — {n} شركةً بمدخلاتٍ لم تُصمَّم")
    print("═" * 70)
    print(f"  دُرِّجت {scored}  ·  امتنعت {abstained}  ·  سقطت {crashed}")
    print(f"  نسبةُ الامتناع {abstained / n:.0%} — وهي مقصودة: كثيرٌ من "
          f"المدخلات ناقصٌ عمداً")
    if fails:
        print(f"\n  ✖ {len(fails)} مخالفة:")
        for m in fails[:25]:
            print(f"      · {m}")
        if len(fails) > 25:
            print(f"      … و{len(fails) - 25} غيرها")
        return 1
    print("\n  ✔ لا درجةَ خارج المدى · لا سقوط · لا إدانةَ على بيانٍ ناقص.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
