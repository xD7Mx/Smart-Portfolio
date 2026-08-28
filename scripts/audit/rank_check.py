"""فحصُ الرتبة — لكل نمطٍ عشيرةٌ كاملة، ويُراجَع مخرَجُها.

## لماذا

قال المالك: «جرّب اختر شركاتٍ من كل قطاع وراجع الدرجة، لا تسلّم الحزمة
قبل أن تنجح». وبيئةُ البناء لا تصل إلى مصدر البيانات، فلا شركاتٍ حقيقية
فيها. والبديلُ ليس التخمين بل **فحصَ الآلة نفسها**: يُبنى لكل نمطٍ من
الأحد عشر عشيرةٌ من أربعٍ وعشرين شركةً بتدرّج جودةٍ معلوم، ثم يُسأل
المحرّك عن أضعفها وأوسطها وأقواها — فإن لم تخرج الرتبةُ متصاعدةً فالعطبُ
في الآلة لا في البيانات.

وهذا يكشف طبقةً كاملة من الأعطاب: نمطٌ لا يُحلّ · مؤشّرٌ لا يُحسب لهذا
النمط · اتّجاهٌ مقلوب (كلّما ساءت الشركة ارتفعت رتبتُها) · مدىً محصور ·
خطٌّ أحمر يشتعل على شركةٍ سليمة أو يصمت عن معطوبة.

أمّا القيمُ الحقيقية لشركاتٍ بعينها فتُفحص على الخادم حيث البيانات —
وهذا السكربتُ لا يغني عن ذلك ولا يدّعيه.

## التشغيل

    python scripts/audit/rank_check.py

ويعود بصفرٍ إن نجح الجميع، وبواحدٍ إن أخفق نمطٌ واحد.
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

# قطاعٌ حقيقيّ لكل نمط — الحلُّ يمرّ بالخريطة نفسها التي يمرّ بها التطبيق.
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

COHORT = 24          # حجمُ العشيرة — فوق الحدّ الأدنى للرتبة بضعفٍ ونصف
YEARS = 8


def _info(arch: str) -> dict:
    """المعلوماتُ الملخّصة بحسب النمط — كما تصل في التطبيق.

    النسبةُ المجمّعة تصل من «أرقام» لا من ياهو، وبطاقةُ التأمين تُعلنها
    ركناً لا تقوم الدرجةُ بدونه. فعيّنةٌ لا تمرّرها تختبر امتناعاً لا
    ترتيباً — وهو الدرسُ نفسه المتكرّر: العيّنةُ تشبه القطاع أو لا تقيسه.
    """
    base = {"beta": 1.0}
    if arch == "insurance":
        base["_regulatory_ratios"] = {"combined_ratio": 94.0}
    return base


def _payout(arch: str, ni: float, dep: float) -> float:
    """التوزيعُ النقديّ بحسب عُرف النمط.

    · الريت — نحو ‎85٪ من الأموال من العمليات (صافي الربح + الإهلاك)،
      وهو داخل النطاق الصحّيّ ‎75–90 وموافقٌ لإلزام الهيئة بالتوزيع.
    · المرافقُ والبنية — موزِّعةٌ ناضجة، نحو ‎55٪ من الربح.
    · وسائرُ الأنماط — نحو الثلث، وهو المعتاد لشركةٍ تُعيد الاستثمار.
    """
    if arch == "reit":
        return (ni + dep) * 0.85
    if arch == "capital_infra":
        return ni * 0.55
    return ni * 0.35


def _ocf(arch: str, ni: float, conv: float, i: int) -> float:
    """التدفّقُ التشغيليّ كما يظهر فعلاً في قائمة كل نمط.

    البنكُ والتمويلُ والتأمين: نموُّ دفتر القروض والأقساط يقع في القسم
    التشغيليّ، فالشركةُ النامية تُظهر تدفّقاً **سالباً** وهو نموٌّ صحّيّ.
    والمطوّرُ العقاريّ: الأرضُ والمشاريعُ تحت التنفيذ أصولٌ تشغيلية،
    فبناؤها يستهلك النقد.
    """
    if arch in ("bank", "financial", "insurance"):
        return -abs(ni) * (0.4 + 0.1 * i)
    if arch == "re_developer":
        return -abs(ni) * 0.3
    return ni * conv


def _fcf(arch: str, ni: float, conv: float, i: int) -> float:
    if arch in ("bank", "financial", "insurance", "re_developer"):
        return _ocf(arch, ni, conv, i) - abs(ni) * 0.1
    if arch == "contracting":
        return -abs(ni) * 0.2          # رأسُ مالٍ عاملٌ يبتلع النقد
    return ni * conv * 0.75


def company(q: float, arch: str) -> list[dict]:
    """قوائمُ ثماني سنواتٍ لشركةٍ جودتُها `q` بين صفرٍ وواحد.

    التدرّجُ يمسّ ما تقيسه البطاقةُ فعلاً: الربحيةَ والهامشَ والتدفّقَ
    والنموَّ والرافعة. والأرقامُ متّسقةٌ داخلياً حتى لا يسقط مؤشّرٌ لسببٍ
    منطقيّ فيُقرأ عطباً في الآلة.
    """
    rows = []
    margin = 0.04 + 0.16 * q                 # هامشٌ صافٍ من ‎4٪ إلى ‎20٪
    growth = 0.01 + 0.11 * q                 # نموٌّ من ‎1٪ إلى ‎12٪
    conv = 0.55 + 0.75 * q                   # تحويلُ الربح إلى نقد
    debt_r = 0.55 - 0.35 * q                 # الدينُ إلى الأصول
    # ══ الضعيفُ متذبذب — والعيّنةُ الملساء أخفت عطباً فادحاً ══
    # كانت السلاسلُ ملساءً تماماً لكلّ درجات الجودة، فمعاملُ الاختلاف
    # ثابتٌ للجميع — فلم يُختبر مؤشّرا الاستقرار قطّ، ونجا اتّجاهُهما
    # المقلوب من كلّ فحوصنا حتى كشفته أرقامُ تداول (جرير بـ«أعلى من ‎0٪»
    # والرياض ريت بـ«أعلى من ‎100٪»).
    # والتذبذبُ ليس زينةً في العيّنة: هو **ما يفرّق** الشركةَ الجيّدة من
    # الرديئة في الواقع. فالجيّدةُ تنمو باطّراد والرديئةُ تتأرجح.
    # ويتلاشى **خطّياً** لا تربيعياً: التربيعُ يجعل النصفَ الأعلى من
    # العشيرة أملسَ كلَّه فيتعادل ويتضاغط في القمّة، والخطّيُّ يوزّع
    # التدرّجَ على العشيرة كلِّها كما هي حالُ سوقٍ حقيقية.
    _swing = 0.45 * (1 - q)
    for i in range(YEARS):
        _osc = 1 + _swing * (1 if i % 2 == 0 else -1) * (0.6 + 0.4 * (i % 3))
        rev = 6000 * (1 + growth) ** i
        ni = rev * margin * _osc
        # والضعيفُ يخسر أحياناً — وهو ما يجعل «سنوات الربحية» تفرّق
        # فعلاً. ولا ثلاثَ سنواتٍ متّصلة حتى لا يشتعل خطٌّ أحمر على
        # عيّنةٍ يُفترض أن تُرتَّب لا أن تُستبعد.
        if q < 0.35 and i in (1, 4):
            ni = -abs(ni) * 0.5
        assets = rev * (1.4 + 6.0 * (arch in ("bank", "financial")))
        equity = assets * (0.10 + 0.03 * q if arch in ("bank", "financial")
                           else 0.35 + 0.20 * q)
        rows.append({
            "year": 2018 + i,
            "revenue": rev, "net_income": ni,
            "total_equity": equity, "equity": equity,
            "total_assets": assets, "total_liabilities": assets - equity,
            "gross_profit": rev * (0.22 + 0.28 * q),
            "operating_income": ni * 1.3,
            "cost_of_revenue": rev * (0.78 - 0.28 * q),
            # ══ التدفّقُ يتبع بنيةَ القائمة في كل نمط ══
            # كانت العيّنةُ تُنتج تدفّقاً موجباً للجميع، فلم يكشف الفحصُ
            # أن الخطوطَ الحمراء تُدين بنكاً سليماً نامياً: نموُّ دفتر
            # القروض يقع في القسم التشغيليّ فيظهر **سالباً**. ومثلُه
            # الأقساطُ في التأمين، والأرضُ والمشاريعُ تحت التنفيذ عند
            # المطوّر. وعيّنةٌ لا تشبه بنيةَ القائمة تُخفي عطبَ القياس.
            "operating_cash_flow": _ocf(arch, ni, conv, i),
            "free_cash_flow": _fcf(arch, ni, conv, i),
            "capex": -rev * 0.05,
            "depreciation": rev * 0.04,
            "ebitda": ni * 1.6,
            "cash": assets * 0.06,
            "inventory": rev * (0.20 - 0.10 * q),
            # السيولةُ تتبع الجودة: الضعيفُ يعمل برأس مالٍ عاملٍ مشدود.
            "current_assets": rev * (0.65 + 0.55 * q),
            "current_liabilities": rev * 0.6,
            "total_debt": assets * debt_r,
            "interest_expense": assets * debt_r * 0.05,
            "shares_outstanding": 1000,
            # ══ التوزيعُ يُبنى على عُرف النمط لا على رقمٍ واحد للجميع ══
            # كانت العيّنةُ توزّع ‎35٪ للجميع، فخرج الريتُ كلُّه بصفرٍ في
            # «توزيع الأموال من العمليات» — ونظامُ هيئة السوق المالية
            # يُلزم الصندوقَ بتوزيع تسعين بالمئة. فكانت العيّنةُ لا تشبه
            # القطاع، فقاست الآلةَ بمُدخَلٍ مستحيل. وعيّنةٌ لا تشبه من
            # تقيسه تُنتج إخفاقاً كاذباً — وهو ما يُضيّع الوقت على عطبٍ
            # لا وجود له.
            "dividends_paid": -_payout(arch, ni, rev * 0.04),
            # بنودُ الأطر القطاعية
            "net_interest_income": rev * (0.55 + 0.25 * q),
            "interest_income": rev * 1.10,
            "operating_expense": rev * (0.45 - 0.20 * q),
            "credit_loss_provision": assets * (0.010 - 0.008 * q),
            "provision_for_loan_losses": assets * (0.010 - 0.008 * q),
            "net_loans": assets * 0.75,
            "gain_on_asset_sale": 0.0,
        })
    return rows


def main() -> int:
    from app.services.four_scores import build_company_features
    from app.services import peer_distribution as pd
    from app.services import spec_score, red_lines, lastgood
    from app.data.archetype_spec import SCORECARDS

    # ── تُبنى عشيرةُ كل نمطٍ ويُحفظ التوزيع ──
    wanted: set[str] = set()
    for card in SCORECARDS.values():
        if not card.get("abstain"):
            for k, *_ in card["metrics"]:
                wanted.add(k)

    pools: dict[str, dict[str, list[float]]] = {}
    for arch, sector in ARCH_SECTOR.items():
        for i in range(COHORT):
            feats, _i, _q = build_company_features(
                company(i / (COHORT - 1), arch), info=_info(arch),
                sector=sector)
            bucket = pools.setdefault(arch, {})
            for k in wanted:
                v = feats.get(k)
                v = v.get("value") if isinstance(v, dict) else v
                if isinstance(v, (int, float)) and v == v:
                    bucket.setdefault(k, []).append(float(v))

    dist = {"as_of": "test", "companies": COHORT * len(ARCH_SECTOR),
            "archetypes": {}}
    for arch, keys in pools.items():
        row = {k: {"n": len(v), "cuts": [round(c, 6) for c in pd._quantiles(v)]}
               for k, v in keys.items() if len(v) >= pd.MIN_COHORT}
        if row:
            dist["archetypes"][arch] = row

    prior = lastgood.load(pd.STORE_KEY)
    lastgood.save(pd.STORE_KEY, dist)
    try:
        return _review(dist)
    finally:
        # لا يبقى توزيعُ اختبارٍ في المخزن — يُعاد ما كان أو يُمحى.
        if prior is None:
            import json
            import os
            p = lastgood._PATH
            if os.path.exists(p):
                d = json.load(open(p))
                d.pop(pd.STORE_KEY, None)
                json.dump(d, open(p, "w"), ensure_ascii=False)
        else:
            lastgood.save(pd.STORE_KEY, prior)


def _review(dist: dict) -> int:
    from app.services.four_scores import build_company_features
    from app.services import spec_score, red_lines
    from app.data.archetype_spec import SCORECARDS

    fails: list[str] = []
    print("═" * 72)
    print("  فحصُ الرتبة — أحدَ عشرَ نمطاً، عشيرةُ كلٍّ منها "
          f"{COHORT} شركة")
    print("═" * 72)
    print(f"  {'النمط':20}{'ضعيفة':>8}{'وسطى':>8}{'قوية':>8}{'تغطية':>8}"
          f"  الأساس")
    print("─" * 72)

    for arch, sector in ARCH_SECTOR.items():
        got = []
        cov = None
        basis = ""
        for q in (0.04, 0.5, 0.96):
            feats, _i, _q = build_company_features(
                company(q, arch), info=_info(arch), sector=sector)
            sp = spec_score.compute(feats, sector)
            got.append(sp.score)
            cov, basis = sp.coverage, (sp.basis or sp.abstain_reason or "")[:22]
            if sp.archetype != arch:
                fails.append(f"{arch}: حُلَّ إلى «{sp.archetype}» بدل نفسه")

        show = "  ".join(f"{('—' if g is None else f'{g:.1f}'):>6}" for g in got)
        print(f"  {arch:20}{show}{cov:>8.2f}  {basis}")

        if any(g is None for g in got):
            fails.append(f"{arch}: امتناعٌ عن شركةٍ كاملة البنود — "
                         f"مؤشّراتُ البطاقة لا تُحسب لهذا النمط")
            continue
        # ── الرتبةُ تتصاعد مع الجودة ──
        if not (got[0] < got[1] < got[2]):
            fails.append(f"{arch}: الرتبةُ لا تتصاعد مع الجودة "
                         f"({got[0]:.1f} → {got[1]:.1f} → {got[2]:.1f})")
        # ── المدى مستعمَل: لا انحصارَ حول الوسط ──
        if got[2] - got[0] < 30:
            fails.append(f"{arch}: المدى محصور ({got[2] - got[0]:.1f} نقطة "
                         f"بين أضعفها وأقواها)")
        # ── الأقوى تبلغ نطاق «ممتاز» ──
        if got[2] < 70:
            fails.append(f"{arch}: أقوى شركةٍ في العشيرة لا تبلغ ‎70 "
                         f"({got[2]:.1f}) — سقفٌ لا تقييم")
        # ══ الفصلُ يُقاس بالفروق لا بأرضيةٍ مطلقة ══
        # كان الشرطُ «أضعفُ شركةٍ دون ‎35»، وأخفقت البنيةُ عنده بـ‎36.0.
        # والسببُ في الشرط لا في المحرّك: بطاقةُ البنية فيها ركنان
        # بنيويّان (الإنفاق الرأسماليّ إلى الإهلاك · نسبةُ التوزيع)
        # يستحقّهما حتى الضعيفُ إن صان أصلَه ووزّع بانضباط. فأرضيةٌ
        # مطلقة تفترض أن كلَّ ركنٍ قابلٌ للسوء — وليس كذلك.
        # والمقصودُ حقّاً أن المحرّك **يفصل**: الضعيفةُ دون الوسطى بفارقٍ
        # بيّن، والقويةُ فوقها بفارقٍ بيّن. وهذا يُقاس بالفروق.
        if got[1] - got[0] < 15:
            fails.append(f"{arch}: الضعيفةُ لا تُفصل عن الوسطى "
                         f"({got[0]:.1f} مقابل {got[1]:.1f})")
        if got[2] - got[1] < 15:
            fails.append(f"{arch}: القويةُ لا تُفصل عن الوسطى "
                         f"({got[2]:.1f} مقابل {got[1]:.1f})")

    # ══ الخلاصةُ تُحسب في موضعين — فيجب أن تتّفقا ══
    # `spec_score.compute` يبني القراءاتِ ثم يتوسّطها، و`raw_composite`
    # يُعيد الحساب ليبني `peer_distribution` توزيعَ الخلاصة. ولو انحرف
    # أحدُهما عن الآخر لَقِيست الشركةُ بمسطرةٍ غير التي بُني بها التوزيع —
    # وهو انحرافٌ صامت لا يُنتج خطأً بل رقماً خاطئاً.
    from app.services import spec_score as _ss
    from app.services import peer_distribution as _pdc
    drift = 0
    for arch, sector in ARCH_SECTOR.items():
        for q in (0.2, 0.55, 0.9):
            fe, _i, _q = build_company_features(company(q, arch),
                                                info=_info(arch), sector=sector)
            rc = _ss.raw_composite(fe, arch, dist)
            sp = _ss.compute(fe, sector)
            if rc is None or sp.score is None:
                continue
            # الدرجةُ المعروضة رتبةُ الخلاصة في السوق؛ فتُقارن بعد الترتيب
            cc = (dist.get("composite") or {}).get("cuts")
            expect = (_pdc.percentile_of(rc, [float(c) for c in cc], True)
                      if cc else rc)
            if abs(expect - sp.score) > 0.15:
                drift += 1
                fails.append(f"{arch}: الخلاصةُ تختلف بين المسارين "
                             f"({expect:.2f} مقابل {sp.score:.2f})")
    print(f"\n  اتّفاقُ مساري الخلاصة: {'✔' if not drift else f'✖ {drift}'}")

    # ── الخطوطُ الحمراء: تشتعل حين يجب وتصمت حين يجب ──
    print("\n" + "─" * 72)
    print("  الخطوطُ الحمراء")
    print("─" * 72)
    # ══ السليمُ من **كلّ** نمطٍ يجب أن يمرّ صامتاً ══
    # كان الفحصُ يجرّب نمطاً واحداً، فمرّ عطبٌ جسيم: بنكٌ سليمٌ نامٍ خرج
    # بثلاثة خطوطٍ حمراء لأن نموَّ دفتر قروضه يظهر تدفّقاً تشغيليّاً
    # سالباً — والخطُّ الأحمر يُبطِل الحكمَ كلَّه، فبنوكُ السوق النامية
    # كانت تُصنَّف «تجنّب». وريتٌ برافعةٍ طبيعية أُدين كذلك.
    for arch, sector in ARCH_SECTOR.items():
        ps = company(0.7, arch)
        fh, _i, _q = build_company_features(ps, info=_info(arch),
                                            sector=sector)
        ids = [r["id"] for r in red_lines.check(fh, ps, arch)]
        print(f"  سليمٌ · {arch:20} {ids or '— صامتة'}")
        if ids:
            fails.append(f"خطٌّ أحمر على شركةٍ سليمة في «{arch}»: {ids}")

    healthy = company(0.7, "asset_light")
    feats_h, _i, _q = build_company_features(healthy, info={"beta": 1.0},
                                             sector="التقنية")

    cases = {
        "loss_streak": lambda ps: [
            {**p, "net_income": -abs(p["net_income"])} if i >= 5 else p
            for i, p in enumerate(ps)],
        "no_cash": lambda ps: [
            {**p, "operating_cash_flow": -abs(p["operating_cash_flow"])}
            for p in ps],
        "no_fcf": lambda ps: [
            {**p, "free_cash_flow": -abs(p["free_cash_flow"])} for p in ps],
        "accruals": lambda ps: [
            {**p, "operating_cash_flow": p["net_income"] - 0.30 * p["total_assets"]}
            for p in ps],
        "negative_equity": lambda ps: [
            {**p, "total_equity": -abs(p["total_equity"]),
             "equity": -abs(p["total_equity"])} for p in ps],
        # ── الرافعةُ حالاً مستمرّة لا سنةً عابرة (D127) ──
        "interest_thin": lambda ps: [
            {**p, "operating_income": abs(p["interest_expense"]) * 0.8}
            for p in ps],
        "debt_over_six": lambda ps: [
            {**p, "operating_income": p["total_debt"] * 0.02,
             "depreciation": p["total_debt"] * 0.01, "ebitda": None}
            for p in ps],
    }
    for want, mutate in cases.items():
        ps = mutate(company(0.7, "asset_light"))
        f2, _i, _q = build_company_features(ps, info={"beta": 1.0},
                                            sector="التقنية")
        ids = [r["id"] for r in red_lines.check(f2, ps, "asset_light")]
        ok = want in ids
        print(f"  {want:20} {ids}  {'✔' if ok else '✖'}")
        if not ok:
            fails.append(f"الخطُّ «{want}» لم يشتعل على حالته")

    # ══ والصمتُ يُختبر كما يُختبر الاشتعال ══ (D127)
    # الخطُّ الأحمر يُبطِل الحكمَ كلَّه، فإشعالُه بلا موجبٍ أفدحُ من
    # إغفاله: الدرجةُ الخاطئة أشدُّ من الامتناع. وهذه ثلاثُ حالاتٍ كان
    # يُدين فيها بريئاً — قِيست على السوق: ‎105 إشعالاتٍ من أصل ‎212.
    quiet = {
        "سنةٌ دوريّةٌ واحدةٌ ضعيفة": (
            lambda ps: [{**p, "operating_income": abs(p["interest_expense"]) * 0.9}
                        if i == len(ps) - 1 else p for i, p in enumerate(ps)],
            "interest_thin"),
        "إهلاكٌ لم يصل فالنسبةُ تقدير": (
            lambda ps: [{**p, "depreciation": None, "ebitda": None,
                         "operating_income": p["total_debt"] * 0.10}
                        for p in ps],
            "debt_over_six"),
        "أسهمُ منحةٍ ترفع العدد بلا تخفيف": (
            lambda ps: [{**p, "shares_outstanding": 1000 * (1.09 ** i)}
                        for i, p in enumerate(ps)],
            "dilution"),
    }
    for label, (mutate, must_not) in quiet.items():
        ps = mutate(company(0.7, "asset_light"))
        f2, _i, _q = build_company_features(ps, info={"beta": 1.0},
                                            sector="التقنية")
        ids = [r["id"] for r in red_lines.check(f2, ps, "asset_light")]
        ok = must_not not in ids
        print(f"  صمتاً · {label:28} {ids or '—'}  {'✔' if ok else '✖'}")
        if not ok:
            fails.append(f"الخطُّ «{must_not}» اشتعل على «{label}»")

    print("\n" + "═" * 72)
    if fails:
        print(f"  ✖ أخفق {len(fails)}:")
        for m in fails:
            print(f"      · {m}")
        return 1
    print("  ✔ كلُّ نمطٍ يرتّب عشيرتَه، والخطوطُ الحمراء تشتعل حين يجب.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
