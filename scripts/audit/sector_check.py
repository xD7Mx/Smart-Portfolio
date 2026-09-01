"""اختبارُ القبول القطاعيّ — المادة ٥٢ من المواصفة التنفيذية.

## ماذا يثبت

المواصفةُ تُلزم باختبار سبعةَ عشرَ قطاعاً على الأقلّ، والتأكّدِ من أن
مؤشّراً لا يناسب بنيةَ القائمة لم يتسلّل إلى نموذجها: لا تدفّقَ حرّاً
صناعياً للبنوك، ولا عائداً صناعياً على رأس المال، ولا نسبةَ تداولٍ،
ولا جراهام للصناديق العقارية، ولا مضاعفَ ربحيةٍ آنيّاً حَكَماً للدورية.

وهذا الفحصُ يُجريه على **قائمة المنع** المكتوبة في `economic_models`
لا على قراءتي للشيفرة — فالقائمةُ تُنفَّذ والتعليقُ يُقرأ.

## ويثبت ما هو أهمّ

أن الدرجةَ تفرّق: شركةٌ جيّدةٌ تخرج أعلى من رديئةٍ **في كلّ قطاع**.
ومحرّكٌ يعطي الجميعَ خمسين ليس محرّكاً، وهو عطبٌ لا يظهر في أيّ فحصٍ
ساكن.

    python scripts/audit/sector_check.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# قطاعٌ حقيقيّ من كلّ نموذج، وفيه القطاعاتُ التي تُلزم بها المادة ٥٢.
SECTORS = (
    "البنوك", "التأمين", "الخدمات المالية",
    "الصناديق العقارية المتداولة",
    "الطاقة", "المواد الأساسية",
    "الاتصالات", "المرافق العامة", "الرعاية الصحية", "الأدوية",
    "إنتاج الأغذية", "تجزئة وتوزيع السلع الاستهلاكية",
    "تجزئة وتوزيع السلع الكمالية", "النقل", "السلع الرأسمالية",
    "الخدمات التجارية والمهنية", "التطبيقات وخدمات التقنية",
    "إدارة وتطوير العقارات",
)

COHORT = 24     # عشيرةٌ لكلّ قطاعٍ يُرتَّب فيها

# ══ العيّنةُ تحمل سعراً وتوزيعاً ══
# مكوّنا التقييم والتوزيعات لا يقومان بلا سعرٍ وربحِ سهم، و`_info` في
# `rank_check` يبني للقوائم وحدها. فعيّنةٌ بلا سعرٍ تختبر امتناعاً لا
# تقييماً — وهو الدرسُ المتكرّر: العيّنةُ تشبه ما تقيسه أو لا تقيسه.
def _info_px(arch: str, periods: list) -> dict:
    from rank_check import _info
    base = dict(_info(arch))
    last = periods[-1]
    shares = last.get("shares_outstanding") or 1000
    dv = last.get("dividends_paid")
    base["current_price"] = 40.0
    if isinstance(dv, (int, float)) and dv:
        base["dividend_per_share"] = abs(dv) / shares
    return base



def company_feats(q: float):
    """سماتُ شركةٍ بجودة `q` في نمط `asset_light` — تُستعمل في الحراسة."""
    from rank_check import company
    from app.services.four_scores import build_company_features
    from app.services import investment_score as inv
    ps = company(q, "asset_light")
    nfo = _info_px("asset_light", ps)
    fe, _i, _q = build_company_features(ps, info=nfo,
                                        sector="التطبيقات وخدمات التقنية")
    fe.update(inv.price_features(nfo, fe, ps,
                                 fair_value=nfo["current_price"] * 1.5))
    return fe


def main() -> int:
    from rank_check import company, _info
    from app.services.four_scores import build_company_features
    from app.services import investment_score as inv
    from app.services import spec_score, risk_gate, red_lines
    from app.data.economic_models import (COMPONENTS, CORE_AXES, FORBIDDEN,
                                          MODEL_OF_SECTOR, WEIGHTS_OF_MODEL,
                                          model_of)
    from app.services import investment_readiness as rdy
    from app.data.market_universe import MARKET_UNIVERSE

    fails: list[str] = []

    # ══ أوّلاً: قائمةُ المنع ══
    print("═" * 74)
    print("  ما لا يجوز لكلّ نموذج — المادة ٥٢")
    print("═" * 74)
    for model, banned in FORBIDDEN.items():
        used = set()
        for comp in COMPONENTS[model].values():
            for key, *_rest in comp:
                used.add(key)
        hit = sorted(used & set(banned))
        print(f"  {model:14} {'✖ ' + str(hit) if hit else '✔ نظيف'}")
        if hit:
            fails.append(f"‏{model} يستعمل ما لا يناسبه: {hit}")

    # ══ ثانياً: أوزانُ كلّ نموذجٍ كما نصّت المواصفة ومجموعُها واحد ══
    WANT = {
        "FINANCIAL":   {"quality": .35, "dividend": .20, "growth": .15, "valuation": .30},
        "REIT":        {"quality": .30, "dividend": .30, "growth": .15, "valuation": .25},
        "CYCLICAL":    {"quality": .30, "dividend": .15, "growth": .25, "valuation": .30},
        "OPERATING":   {"quality": .30, "dividend": .20, "growth": .25, "valuation": .25},
        "REAL_ESTATE": {"quality": .30, "dividend": .15, "growth": .20, "valuation": .35},
    }
    print("\n" + "═" * 74)
    print("  أوزانُ كلّ نموذج")
    print("═" * 74)
    for m, want in WANT.items():
        got = WEIGHTS_OF_MODEL.get(m, {})
        tot = sum(got.values())
        ok = got == want and abs(tot - 1.0) < 1e-9
        print(f"  {m:14} {got}  مجموع {tot:.2f}  {'✔' if ok else '✖'}")
        if not ok:
            fails.append(f"أوزانُ {m} تخالف المواصفة أو لا يبلغ مجموعُها واحداً")

    # ══ الكونُ: السوقُ الرئيسة وحدها ══ (D136)
    # الاستبعادُ المتأخّر ليس استبعاداً: كان الكونُ يمرّ كاملاً إلى بناء
    # التوزيع ثم تُطرح «نمو» في حلقة التسجيل، فتدخل شركاتُها كلَّ عشيرةٍ
    # ووسيطٍ ومئين. فيُفحص هنا أن الحسمَ يقع **في المصدر**.
    from app.data import universe as _uni
    print("\n" + "═" * 74)
    print("  الكونُ — السوقُ الرئيسة وحدها، والحسمُ في المصدر")
    print("═" * 74)
    cen = _uni.census()
    print(f"  الكون {cen['total']} · رئيسيّ {cen['main']} · "
          f"موازية {cen['nomu']} · مجهول {cen['unknown']}")
    print(f"  مصدرُ التصنيف: {cen['source']}")
    if cen["unknown"]:
        fails.append(f"{cen['unknown']} رمزاً لا يُعرف سوقُه: "
                     f"{cen['unknown_symbols']}")

    leaked = [s for s in _uni.main_market() if _uni.is_nomu(s)]
    print(f"  رموزُ «نمو» داخل الكون المعتمَد: {len(leaked)}"
          f"  {'✔' if not leaked else '✖'}")
    if leaked:
        fails.append(f"تسرّبت «نمو» إلى الكون المعتمَد: {leaked[:10]}")

    # والحسمُ يقع في `peer_distribution` نفسه لا في مَن يستدعيه
    import inspect
    from app.services import peer_distribution as _pdm2
    _bsrc = inspect.getsource(_pdm2.build)
    at_source = "is_main" in _bsrc
    print(f"  الترشيحُ داخل بناء التوزيع: "
          f"{'✔ نعم' if at_source else '✖ لا — الاستبعادُ متأخّر'}")
    if not at_source:
        fails.append("‏`peer_distribution.build` لا يرشّح السوقَ الموازية "
                     "عند المصدر — فتتلوّث العشيراتُ ثم تُستبعد بعد الحساب")

    # وحالاتُ حدّيّة في التصنيف
    for sym, want in (("9500", "NOMU"), ("2222", "MAIN"), ("1120", "MAIN"),
                      ("9999", "NOMU"), ("2222.SR", "MAIN"),
                      ("abc", None), ("", None), ("222", None)):
        got = _uni.market_of(sym)
        if got != want:
            fails.append(f"تصنيفُ «{sym}» خرج {got} والمتوقَّع {want}")
    print(f"  حالاتٌ حدّيّة في التصنيف: فُحصت ٨")

    # ══ كلُّ مؤشّرٍ يُرتَّب له مسطرةٌ تُبنى ══ (D134)
    # المؤشّرُ يُحسب ثم يُقاس على عشيرته. فإن لم يُجمع مفتاحُه في
    # `peer_distribution` لم يجد مسطرةً فيُعدّ مفقوداً — وهو عطبُ تركيبٍ
    # يظهر «شحَّ بيانات». قِيس أثرُه: تسعةٌ من تسعةَ عشرَ مؤشّراً بلا
    # مسطرة، فسقط النموُّ لـ‎179 شركةً ولها أفقُ نموٍّ محسوب.
    print("\n" + "═" * 74)
    print("  لكلّ مؤشّرٍ يُرتَّب مسطرةٌ تُبنى له")
    print("═" * 74)
    import inspect
    from app.services import peer_distribution as _pdm
    from app.data.archetype_spec import SCORECARDS as _SC
    from app.services import governance_pillar as _gp
    _src = inspect.getsource(_pdm.build)
    collected = set()
    for card in _SC.values():
        if not card.get("abstain"):
            for k, *_r in card["metrics"]:
                collected.add(k)
    collected |= set(_gp.METRIC_KEYS)
    price_based = {"p_e", "p_b", "ev_ebitda", "p_ffo", "p_e_normalized",
                   "dividend_yield", "fv_discount"}
    if "COMPONENTS" in _src:
        for _m in COMPONENTS.values():
            for _c in _m.values():
                for k, *_r in _c:
                    if k not in price_based:
                        collected.add(k)
    need = set()
    for m, comps in COMPONENTS.items():
        for cn, ms in comps.items():
            for k, _l, _w, d in ms:
                if k not in price_based and d != "discount":
                    need.add(k)
    orphan = sorted(need - collected)
    print(f"  مؤشّراتٌ تُرتَّب {len(need)} · مجموعةٌ في المفاتيح "
          f"{len(need & collected)} · غيرُ مجموعة {len(orphan)}"
          f"  {'✔' if not orphan else '✖'}")
    # ══ وهذا يحرس الحرفَ لا المعنى ══ (D137)
    # جمعُ المفتاح شرطٌ لازمٌ لا كافٍ: التوزيعُ لا يُبنى إلّا إن بلغت
    # العشيرةُ حدَّها، والقيمةُ لا تصل العشيرةَ إلّا إن حُسبت من بنودٍ
    # بأسمائها الحقيقية. فقال هذا الفحصُ «19/19» بينما بنى الخادمُ ‎17
    # توزيعاً فقط — وكلاهما صادقٌ في شيءٍ مختلف.
    #
    # ولا يُقاس البناءُ الفعليّ هنا: يحتاج سوقاً. فيُقاس في `decide.py`
    # (الاختبار ٣) ويفرّق هناك بين عطبِ تركيبٍ وشحٍّ حقيقيّ.
    print("  ملاحظة: هذا يفحص جمعَ المفاتيح. وبناءَ التوزيع فعلياً")
    print("          يفحصه `decide.py` — الاختبار ٣ — على السوق.")

    # ── وأسماءُ البنود تُقرأ كما يُخرجها المصدر ──
    # كان `sector_metrics` يقرأ `total_equity` والمصدرُ يُخرج `equity`،
    # فلم تُحسب الرافعةُ لشركةٍ واحدةٍ قطّ. والعيّنةُ تضع المفتاحين معاً
    # فأخفته. فيُفحص هنا بفترةٍ **بمفاتيح المصدر وحدها**.
    from app.services import sector_metrics as _sm
    _real = {"year": 2025, "equity": 1000.0, "total_assets": 5000.0,
             "total_debt": 1500.0, "ending_cash": 300.0,
             "operating_income": 400.0, "depreciation": 100.0,
             "revenue": 3000.0, "net_income": 250.0, "inventory": 200.0}
    _f = (_sm.compute("commodity", [_real, _real], None, None)
          .get("features") or {})
    for _k in ("leverage_x", "net_debt_ebitda", "ltv_pct"):
        _ok = _f.get(_k) is not None
        print(f"  بمفاتيح المصدر الحقيقية · {_k:18} "
              f"{_f.get(_k)}  {'✔' if _ok else '✖'}")
        if not _ok:
            fails.append(f"«{_k}» لا يُحسب بأسماء بنود المصدر الحقيقية")
    for k in orphan:
        print(f"      ✖ {k}")
    if orphan:
        fails.append(f"{len(orphan)} مؤشّراً يُرتَّب بلا توزيعٍ يُبنى له: {orphan}")

    # ══ ولا معلومةَ تُحتسب مرّتين ══ (المادتان ٥ و٦)
    # مفهومٌ يتكرّر في مكوّنٍ واحد يضاعف وزنَه بلا إعلان: الرِّبحيّةُ
    # تُكتب ربعاً وتُحتسب نصفاً. ويُفحص كذلك أن مفهومَ كلّ مؤشّرٍ يقع
    # في بُعد مكوّنه، فلا يُقاس نموٌّ داخل الجودة تسلّلاً.
    from app.data.economic_models import (CONCEPT_OF, ALLOWED_REPEAT,
                                          DIMENSIONS)
    print("\n" + "═" * 74)
    print("  لا تكرارَ لمعلومة، ولا مؤشّرَ خارجَ بُعد مكوّنه")
    print("═" * 74)
    dup = 0
    for m, comps in COMPONENTS.items():
        for cn, metrics in comps.items():
            seen: dict = {}
            for k, *_r in metrics:
                con = CONCEPT_OF.get(k)
                if con is None:
                    fails.append(f"«{k}» بلا مفهومٍ معلَن ({m}.{cn})")
                    continue
                if con not in DIMENSIONS.get(cn, ()):
                    fails.append(f"«{k}» مفهومُه {con} خارج بُعد {cn} ({m})")
                if con in seen and ALLOWED_REPEAT.get((m, cn)) != con:
                    fails.append(f"{m}.{cn}: «{k}» يكرّر «{seen[con]}» ({con})")
                    dup += 1
                seen[con] = k
    print(f"  مؤشّراتٌ موصوفة {len(CONCEPT_OF)} · تكرارٌ غيرُ معلَن {dup}"
          f"  {'✔' if not dup else '✖'}")

    # ══ والطبقةُ المطلقة تقصّ ولا ترفع ══ (المادة ٨)
    from app.services import absolute_quality as aq
    print("\n" + "═" * 74)
    print("  الترتيبُ النسبيّ لا يُخفي ضعفاً مالياً مطلقاً")
    print("═" * 74)
    bad_rows = [{"total_equity": -100.0, "net_income": -5.0,
                 "operating_income": 10.0, "interest_expense": 40.0,
                 "operating_cash_flow": -20.0}]
    ab = aq.evaluate(bad_rows, {"payout_ratio": 130.0}, "OPERATING")
    capped, note = aq.apply_ceiling(95.0, ab)
    print(f"  ضعيفةٌ مطلقاً برتبةٍ ‎95 → {capped}  ({len(ab['breaches'])} واقعة)")
    if capped is None or capped >= 95.0:
        fails.append("الطبقةُ المطلقة لم تقصّ درجةً عاليةً على ضعفٍ صريح")
    good = aq.evaluate([{"total_equity": 100.0, "net_income": 10.0,
                         "operating_income": 40.0, "interest_expense": 4.0,
                         "operating_cash_flow": 30.0}],
                       {"payout_ratio": 50.0}, "OPERATING")
    kept, _n2 = aq.apply_ceiling(72.0, good)
    print(f"  سليمةٌ برتبةٍ ‎72        → {kept}  (السلامةُ لا تُكافأ)")
    if kept != 72.0:
        fails.append("الطبقةُ المطلقة غيّرت درجةَ شركةٍ سليمة — وهي تقصّ فقط")

    # ══ ثالثاً: كلُّ قطاعٍ في السوق له نموذج ══
    live = {m.get("sector") for s, m in MARKET_UNIVERSE.items()
            if not s.startswith("9") and m.get("sector")}
    orphan = sorted(s for s in live if model_of(s) is None)
    print(f"\n  قطاعاتُ السوق {len(live)} · بلا نموذج {len(orphan)}")
    if orphan:
        for s in orphan:
            print(f"      ✖ {s}")
        fails.append(f"{len(orphan)} قطاعاً بلا نموذجٍ اقتصاديّ: {orphan}")
    extra = sorted(set(MODEL_OF_SECTOR) - live)
    if extra:
        print(f"  ‏{len(extra)} قطاعاً في المواصفة لا وجودَ له في السوق: {extra}")

    # ══ رابعاً: الدرجةُ تفرّق في كلّ قطاع ══
    print("\n" + "═" * 74)
    print("  الدرجةُ تفرّق — ضعيفةٌ ووسطى وقويّة في كلّ قطاع")
    print("═" * 74)
    print(f"  {'القطاع':32}{'النموذج':13}{'ضعيفة':>8}{'وسطى':>8}{'قويّة':>8}  المكوّنات")
    print("─" * 74)

    for sector in SECTORS:
        arch = spec_score.resolve_archetype_ex(sector, {})[0]
        # عشيرةٌ من الشركات نفسها يُرتَّب فيها المرشّحون
        cohort = [company(i / (COHORT - 1), arch) for i in range(COHORT)]
        dist = _dist_from(cohort, sector, arch)
        row = []
        comps_seen: set[str] = set()
        for q in (0.10, 0.50, 0.92):
            ps = company(q, arch)
            nfo = _info_px(arch, ps)
            fe, inf, _ = build_company_features(ps, info=nfo, sector=sector)
            fe.update(inv.price_features(nfo, fe, ps,
                                         fair_value=nfo["current_price"]))
            r = inv.compute(fe, sector, dist, arch, medians=_MEDIANS)
            row.append(r["score"])
            comps_seen |= {k for k, c in r["components"].items()
                           if c["score"] is not None}
        model = model_of(sector) or "—"
        cells = "".join(f"{('—' if v is None else f'{v:.1f}'):>8}" for v in row)
        print(f"  {sector:32}{model:13}{cells}  {len(comps_seen)}/4")

        if any(v is None for v in row):
            fails.append(f"«{sector}» لم تُنتج درجةً لأحد المرشّحين")
            continue
        if not (row[0] < row[1] < row[2]):
            fails.append(f"«{sector}» لا تفرّق: {row[0]} · {row[1]} · {row[2]}")
        if row[2] - row[0] < 15:
            fails.append(f"«{sector}» فرقُ الطرفين {row[2] - row[0]:.1f} — ضيّقٌ لا يُقرأ")

    # ══ خامساً: البوّابة تمنع ولا تُعوَّض ══
    print("\n" + "═" * 74)
    print("  البوّابة تمنع التأهّل ولا تُخصم")
    print("═" * 74)
    ps = company(0.95, "asset_light")
    ps = [{**p, "total_equity": -abs(p["total_equity"]),
           "equity": -abs(p["total_equity"])} for p in ps]
    fe, _i, _q = build_company_features(ps, info=_info("asset_light"),
                                        sector="التطبيقات وخدمات التقنية")
    g = risk_gate.evaluate(fe, ps, red_lines.check(fe, ps, "asset_light"))
    print(f"  ممتازةٌ بحقوقٍ سالبة → {g['status']}  {g['excluded_by']}")
    if g["status"] != risk_gate.EXCLUDED:
        fails.append("حقوقُ ملكيةٍ سالبة لم تُقصِ — البوّابةُ لا تعمل")

    ps2 = company(0.20, "commodity")
    ps2 = [{**p, "net_income": -abs(p["net_income"])} for p in ps2]
    fe2, _i, _q = build_company_features(ps2, info=_info("commodity"),
                                          sector="الطاقة")
    g2 = risk_gate.evaluate(fe2, ps2, red_lines.check(fe2, ps2, "commodity"))
    print(f"  خسائرُ متّصلة        → {g2['status']}  ({len(g2['flags'])} إنذاراً)")
    if g2["status"] == risk_gate.EXCLUDED:
        fails.append("خسائرُ متّصلة أقصت برمجياً — والمادة ٤٦ تجعلها إنذاراً")

    # ══ سادساً: الناقصُ لا يصير صفراً ══
    print("\n" + "═" * 74)
    print("  الناقصُ يُستبعَد ولا يصير صفراً")
    print("═" * 74)
    arch = "consumer_defensive"
    sector = "إنتاج الأغذية"
    cohort = [company(i / (COHORT - 1), arch) for i in range(COHORT)]
    dist = _dist_from(cohort, sector, arch)
    full = company(0.80, arch)
    nfo = _info_px(arch, full)
    fe, _i, _q = build_company_features(full, info=nfo, sector=sector)
    fe.update(inv.price_features(nfo, fe, full, fair_value=nfo["current_price"]))
    a = inv.compute(fe, sector, dist, arch, medians=_MEDIANS)
    thin = dict(fe)
    for k in ("roic", "cash_conversion_ratio"):
        thin.pop(k, None)
    b = inv.compute(thin, sector, dist, arch, medians=_MEDIANS)
    qa = a["components"]["quality"]["score"]
    qb = b["components"]["quality"]["score"]
    print(f"  الجودة كاملةً {qa}  ·  بعد إسقاط مؤشّرين {qb}")
    if qb is None:
        print("      (سقط المكوّن — تغطيةٌ دون الحدّ)")
    elif qb < qa - 25:
        fails.append(f"الناقصُ عاقَب: الجودة {qa} ← {qb}")

    # ══ سابعاً: العدُّ على سلسلةٍ لم تصل يمتنع ولا يُصفّر ══ (D128)
    # `sum()` على قائمةٍ كلُّها `None` يعيد صفراً، فتُقرأ الشركةُ
    # «صفرَ سنواتِ توزيع» ثم تُرتَّب في القاع — فيجتمع الممنوعان:
    # الناقصُ صار صفراً ثم صار عقوبة.
    print("\n" + "═" * 74)
    print("  ما لم يصل يمتنع ولا يُصفَّر")
    print("═" * 74)
    for line, feat in (("dividends_paid", "dividend_years"),
                       ("net_income", "profitable_years")):
        ps = [{k: v for k, v in p.items() if k != line}
              for p in company(0.6, "consumer_defensive")]
        try:
            fe, _i, _q = build_company_features(
                ps, info=_info("consumer_defensive"), sector="إنتاج الأغذية")
            got = inv._val(fe, feat)
        except Exception as e:                                # noqa: BLE001
            got = f"سقط: {type(e).__name__}"
        ok = got is None
        print(f"  بلا «{line}» → {feat} = {got}  {'✔' if ok else '✖'}")
        if not ok:
            fails.append(f"«{feat}» أعطى {got} وسلسلتُه لم تصل — الناقصُ صار رقماً")

    # ══ ثامناً: الجاهزيةُ تمنع الأساسَ الضيّق من العبور ══ (المادة ٨)
    # كشفه المالك: «الماجد للعود» ‎89.6 · A والنموُّ والتقييمُ لم يُقاسا.
    # فدرجةٌ عاليةٌ بمحورٍ جوهريٍّ غائبٍ يجب ألّا تعبر بوّابةَ الترشيح.
    print("\n" + "═" * 74)
    print("  الجاهزيةُ منفصلةٌ عن الدرجة — والأساسُ الضيّق لا يعبر")
    print("═" * 74)
    arch, sector = "asset_light", "التطبيقات وخدمات التقنية"
    cohort = [company(i / (COHORT - 1), arch) for i in range(COHORT)]
    dist = _dist_from(cohort, sector, arch)
    ps = company(0.95, arch)
    nfo = _info_px(arch, ps)
    fe, _i, _q = build_company_features(ps, info=nfo, sector=sector)
    fe.update(inv.price_features(nfo, fe, ps, fair_value=nfo["current_price"] * 1.5))
    thinf = {k: v for k, v in fe.items()
             if k not in ("revenue_cagr_5y", "eps_cagr_5y", "roic_trend",
                          "p_e", "ev_ebitda", "fv_discount")}
    r = inv.compute(thinf, sector, dist, arch, medians=_MEDIANS)
    cf, _w = inv.confidence_of(r, inv._val(thinf, "years_available"))
    verdict = rdy.evaluate(r, "PASS", cf, None)
    print(f"  ممتازةٌ بلا نموٍّ ولا تقييم → درجة {r['score']} · "
          f"{r['grade']} · اكتمال {(r['data_completeness'] or 0):.0%}")
    print(f"     جاهزية {verdict['readiness']} — {verdict['why'][:2]}")
    if verdict["readiness"] != rdy.NOT_READY:
        fails.append(f"أساسٌ ضيّقٌ خرج بـ{verdict['readiness']} — "
                     f"والمادة ١٢ توجب NOT_READY")
    # ── والدرجةُ لا تتضخّم بالبيانات المفقودة (المادة ١١) ──
    rw, fin, cv = r.get("raw_score"), r.get("score"), r.get("data_coverage")
    print(f"     خام {rw} · تغطية {(cv or 0):.0%} · نهائية {fin}")
    if rw is not None and cv is not None and rw > 50 and not (fin < rw):
        fails.append(f"الدرجةُ لم تنكمش مع نقص التغطية: خام {rw} نهائية {fin}")
    # وتناظرُ المبدأ: الضعيفةُ ناقصةُ البيانات ترتفع نحو الوسط لا تُعاقَب
    weak = inv.compute(
        {k: v for k, v in company_feats(0.05).items()
         if k not in ("revenue_cagr_5y", "eps_cagr_5y", "roic_trend",
                      "p_e", "ev_ebitda", "fv_discount")},
        sector, dist, arch, medians=_MEDIANS)
    if (weak.get("raw_score") is not None and weak["raw_score"] < 50
            and not weak["score"] > weak["raw_score"]):
        fails.append("المبدأُ غيرُ متناظر — فهو عقوبةٌ لا ترجيحُ مصداقية")
    print(f"     وضعيفةٌ ناقصة: خام {weak.get('raw_score')} → "
          f"نهائية {weak.get('score')}  (ترتفع نحو الوسط)")

    # ── ثلاثُ حالاتٍ لا رابع ──
    states = {rdy.INVESTMENT_READY, rdy.WATCH, rdy.NOT_READY}
    if len(states) != 3:
        fails.append("حالاتُ الجاهزية ليست ثلاثاً")

    # وكاملةُ البيانات تعبر، وإلّا فالبوّابةُ تمنع الجميع
    full = inv.compute(fe, sector, dist, arch, medians=_MEDIANS)
    cf2, _w2 = inv.confidence_of(full, inv._val(fe, "years_available"))
    v2 = rdy.evaluate(full, "PASS", cf2, "PE_MEDIAN")
    print(f"  كاملةُ المحاور            → درجة {full['score']} · "
          f"اكتمال {(full['data_completeness'] or 0):.0%} · "
          f"جاهزية {v2['readiness']}")
    if v2["readiness"] not in (rdy.READY, rdy.WATCH):
        fails.append(f"كاملةُ المحاور لم تعبر: {v2['why']}")

    # ══ اختبارُ الانحدار النهائيّ ══ (البند ٦ — بعد إغلاق الحوكمة)
    # سبعُ ضماناتٍ لا يُسمح بانكسار واحدةٍ منها بعد اليوم. وما يحتاج
    # سوقاً حيّاً منها يُفحص في `decide.py`؛ وما يُفحص هنا يُفحص ببناءٍ
    # متعمَّدٍ للخطأ لا بقراءة نصّ.
    print("\n" + "═" * 74)
    print("  اختبارُ الانحدار — سبعُ ضمانات")
    print("═" * 74)
    from app.services import model_valuation as _mv

    # ١ — «نمو» لا تدخل الكون
    _leak = [x for x in ("9500", "9999") if _uni.is_main(x)]
    print(f"  ١ «نمو» خارج الكون                 {'✔' if not _leak else '✖'}")
    if _leak:
        fails.append(f"«نمو» دخلت الكون: {_leak}")

    # ٢ — الترشيحُ داخل بناء التوزيع (يُقرأ من المصدر لا يُفترض)
    print(f"  ٢ الترشيحُ في مصدر التوزيع          "
          f"{'✔' if at_source else '✖'}")

    # ٣ — شركةٌ مستبعَدةٌ لا تظهر جاهزة
    _res = {"model": "OPERATING", "sector": "التقنية",
            "components": {k: {"score": 70.0} for k in
                           ("quality", "dividend", "growth", "valuation")},
            "data_completeness": 0.95, "score": 88.0}
    _v = rdy.evaluate(_res, "EXCLUDED", "مرتفعة", "PE_MEDIAN")
    ok3 = _v["readiness"] == rdy.NOT_READY
    print(f"  ٣ المستبعَدةُ لا تظهر جاهزة          {'✔' if ok3 else '✖'}"
          f"  ({_v['readiness']})")
    if not ok3:
        fails.append("شركةٌ ببوّابةٍ مغلقة خرجت جاهزة")

    # ٤ — الأوزانُ والعتباتُ مطابقة
    _WANT_C = {"negative_equity": 25.0, "loss_last_year": 45.0,
               "interest_below_one": 35.0, "payout_over_earnings": 60.0,
               "negative_ocf": 50.0}
    _drift = [k for k, v in _WANT_C.items()
              if abs((aq.CEILINGS.get(k) or (None,))[0] or -1) != v]
    _drift += [m for m, w in WANT.items()
               if {k: round(x, 4) for k, x in
                   WEIGHTS_OF_MODEL.get(m, {}).items()} != w]
    print(f"  ٤ لا انحرافَ في الأوزان والسقوف     "
          f"{'✔' if not _drift else '✖'}")
    if _drift:
        fails.append(f"انحرافٌ في ثوابت: {_drift}")

    # ٥ — لا NaN/Inf يخرج من الدرجة
    import math as _math
    _bad = [k for k, v in {"nan": float("nan"), "inf": float("inf")}.items()
            if inv._val({"x": v}, "x") is not None]
    print(f"  ٥ NaN/Inf لا تمرّ من قارئ القيمة    "
          f"{'✔' if not _bad else '✖'}")
    if _bad:
        fails.append(f"قيمٌ غيرُ منتهيةٍ تمرّ: {_bad}")

    # ٦ — طريقةُ تقييمٍ غيرُ مسجَّلة لا تُنتج قيمة
    _known = {m for ms in _mv.METHODS.values() for m in ms}
    _fake, _h, _g = _mv._try("NO_SUCH_METHOD", {}, [{}], {})
    ok6 = _fake is None and "NO_SUCH_METHOD" not in _known
    print(f"  ٦ طريقةٌ غيرُ مسجَّلة لا تُنتج قيمة   {'✔' if ok6 else '✖'}")
    if not ok6:
        fails.append("طريقةُ تقييمٍ مجهولة أنتجت قيمة")

    # ٧ — مؤشّرٌ بلا توزيعٍ لا يُرتَّب (ولا يُعطى مئيناً مصطنعاً)
    _sc = inv._metric_score("roe", "higher", 12.0, "commodity",
                            {"archetypes": {"commodity": {}}}, None)
    ok7 = _sc is None
    print(f"  ٧ بلا توزيعٍ لا مئينَ مصطنعاً        {'✔' if ok7 else '✖'}")
    if not ok7:
        fails.append(f"مؤشّرٌ بلا توزيعٍ أُعطي مئيناً: {_sc}")

    print("\n" + "═" * 74)
    if fails:
        print(f"  ✖ أخفق {len(fails)}:")
        for m in fails:
            print(f"      · {m}")
        return 1
    print("  ✔ كلُّ قطاعٍ يُقاس بنموذجه، والدرجةُ تفرّق، والبوّابةُ تمنع.")
    return 0


# وسائطُ قطاعيةٌ ثابتةٌ للفحص — تُحاكي ما يأتي من ماسح السوق.
_MEDIANS = {"p_e": 16.0, "p_b": 1.8, "ev_ebitda": 9.0,
            "p_ffo": 13.0, "dividend_yield": 4.0}


def _dist_from(cohort: list, sector: str, arch: str) -> dict:
    """توزيعُ أقرانٍ من عشيرةٍ مبنيّةٍ في الذاكرة — بلا نداءِ مصدر."""
    from app.services import peer_distribution as pd
    from app.services.four_scores import build_company_features
    from rank_check import _info

    raws = []
    for ps in cohort:
        fe, _i, _q = build_company_features(ps, info=_info(arch),
                                            sector=sector)
        raws.append(fe)
    keys: dict[str, list[float]] = {}
    for fe in raws:
        for k, v in fe.items():
            v = v.get("value") if isinstance(v, dict) else v
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                keys.setdefault(k, []).append(float(v))
    cuts = {k: {"n": len(vs), "cuts": pd._quantiles(vs)}
            for k, vs in keys.items() if len(vs) >= 8}
    return {"archetypes": {arch: cuts}, "companies": len(cohort)}


if __name__ == "__main__":
    sys.exit(main())
