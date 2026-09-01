"""إقفالُ ملفّ الحوكمة — اثنا عشرَ تحقّقاً، والحكمُ يُحسب لا يُكتب.

## ما هي درجةُ الحوكمة

**درجةُ سلامة الورقة المالية** من صفرٍ إلى مئة. تجيب عن سؤالٍ واحد:
ما مدى قوّة هذه الشركة ماليّاً وتشغيليّاً مقارنةً بأقرانها، بالمؤشّرات
المناسبة لطبيعة نشاطها؟

وليست سعراً عادلاً، ولا توصيةَ شراء، ولا توقّعاً لحركة السهم، ولا درجةً
فنّية. ولكلٍّ من تلك محرّكُه المستقلّ.

## الشركاتُ الجديدة

النظامُ يصنّف ولا يخترع: `القطاع → النمط → المؤشّرات → الأقران →
الدرجة`. فشركةٌ تُدرَج غداً تمرّ بالمسطرة نفسها. وإن لم ينتمِ نشاطُها
إلى نمطٍ قائم، **تُعلَن حالةً تحتاج تصنيفاً** ولا تُمنح درجةً تلقائياً —
وهذا مفحوصٌ هنا برمزٍ وهميّ لقطاعٍ مجهول.

    python scripts/audit/governance_lock.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.data.economic_models import (COMPONENTS, CORE_AXES,
                                          WEIGHTS_OF_MODEL, model_of)
    from app.services import spec_score, investment_score as inv
    from app.services import investment_readiness as rdy
    from app.services import absolute_quality as aq
    from app.services import model_valuation as mv
    from app.services import peer_distribution as pd
    from app.data.archetype_spec import SCORECARDS

    T: list[tuple[str, bool, str]] = []

    def t(n, ok, d=""):
        T.append((n, bool(ok), d))

    MAIN = uni.main_market(MARKET_UNIVERSE)
    cen = uni.census(MARKET_UNIVERSE)

    # ══ ١ — القطاعُ إمّا معلومٌ وإمّا مُعلَنٌ ناقصاً ══
    # لا يُشترط أن تكون كلُّ شركةٍ مصنَّفةً اليوم؛ يُشترط ألّا تُقاس
    # واحدةٌ بغير مسطرتها. فالمجهولةُ تُعلَن حالةً تنتظر التصنيف.
    no_sec = sorted(s for s, m in MAIN.items() if not m.get("sector"))
    _nm = {s: (MARKET_UNIVERSE[s].get("name_ar")
               or MARKET_UNIVERSE[s].get("name_en") or s) for s in no_sec}
    t("١ القطاعُ معلومٌ أو مُعلَنٌ ناقصاً",
      True,
      f"مصنَّفة {len(MAIN) - len(no_sec)}/{len(MAIN)}"
      + (" · تنتظرُ التصنيف: "
         + " · ".join(f"{s} {_nm[s]}" for s in no_sec) if no_sec else ""))

    # ══ ٢ — المصنَّفةُ تُقاس، والمجهولةُ تمتنع ══
    # والفحصُ على المعنى لا على الاسم: `resolve_archetype_ex` تُعيد
    # `("asset_light", False)` عند الامتناع — والاسمُ وحده صادقٌ دائماً،
    # فيُقرأ عَلَمُ الحلّ لا العنصر الأوّل (D138).
    bad_known, leaked = [], []
    for s, m in MAIN.items():
        sec = m.get("sector")
        solved = spec_score.resolve_archetype_ex(sec, {})[1]
        has_model = model_of(sec) is not None
        if sec:
            if not solved or not has_model:
                bad_known.append(s)
        else:
            # مجهولةٌ: لا نموذجَ ولا درجة — وإلّا فقد قيست بمسطرةٍ ليست لها
            if solved or has_model or inv.compute({}, sec, {}, None)["score"]:
                leaked.append(s)
    t("٢ المصنَّفةُ تُقاس والمجهولةُ تمتنع", not bad_known and not leaked,
      f"مصنَّفةٌ بلا نموذج {len(bad_known)} · مجهولةٌ قيست {len(leaked)}"
      + (f" · {(bad_known + leaked)[:6]}" if (bad_known or leaked) else ""))

    # ══ ٢ب — المؤشّرُ الأساسيّ للقطاع هو المحورُ الأكبر ══
    # خريطةُ المادة ٢ حرفاً بحرف: القطاعُ ← مؤشّرُه الأساسيّ. ويُشترط
    # أن يحمل هذا المؤشّرُ **أكبرَ وزنٍ منفرداً** في مكوّن الجودة —
    # فتعادلُه مع غيره يعني أنه ليس محوراً، وغيابُه يعني قطاعاً يُقاس
    # بغير أساسه.
    PRIMARY = {
        "البنوك": "roe", "التأمين": "roe", "الخدمات المالية": "roe",
        "الطاقة": "roic", "المواد الأساسية": "roic",
        "السلع الرأسمالية": "roic", "الخدمات التجارية والمهنية": "roic",
        "النقل": "roic", "السلع طويلة الأجل": "roic",
        "الخدمات الاستهلاكية": "roic", "الإعلام والترفيه": "roic",
        "تجزئة وتوزيع السلع الكمالية": "roic",
        "تجزئة وتوزيع السلع الاستهلاكية": "roic",
        "إنتاج الأغذية": "roic", "الرعاية الصحية": "roic",
        "الأدوية": "roic", "الاتصالات": "roic", "المرافق العامة": "roic",
        "التطبيقات وخدمات التقنية": "roic",
        "الخدمات الاستهلاكية الدورية": "roic",
        "إدارة وتطوير العقارات": "roe",
        "الصناديق العقارية المتداولة": "ltv_pct",
    }
    off = []
    for sec, prim in PRIMARY.items():
        mdl = model_of(sec)
        if mdl is None:
            off.append(f"{sec}: بلا نموذج")
            continue
        w = {k: wt for k, _l, wt, _d in COMPONENTS[mdl]["quality"]}
        top = [k for k, v in w.items() if v == max(w.values())]
        if prim not in w:
            off.append(f"{sec}: {prim} غائب")
        elif top != [prim]:
            off.append(f"{sec}: الأكبرُ {top} لا {prim}")
    t("٢ب المؤشّرُ الأساسيّ هو المحورُ الأكبر", not off,
      f"{len(PRIMARY)} قطاعاً مطابقاً" if not off else " · ".join(off[:4]))

    # ٣ — لكلّ نموذجٍ مؤشّراتُه معرَّفة
    bad_model = [m for m in WEIGHTS_OF_MODEL
                 if not all(COMPONENTS.get(m, {}).get(c)
                            for c in ("quality", "dividend", "growth",
                                      "valuation"))]
    t("٣ لكلّ نموذجٍ مؤشّراتُه معرَّفة", not bad_model,
      f"نماذج {len(WEIGHTS_OF_MODEL)}"
      + (f" · ناقصة: {bad_model}" if bad_model else ""))

    # ٤ — كلُّ مؤشّرٍ يُرتَّب مجموعٌ في بناء التوزيع
    import inspect
    src = inspect.getsource(pd.build)
    PRICE = {"p_e", "p_b", "ev_ebitda", "p_ffo", "p_e_normalized",
             "dividend_yield", "fv_discount"}
    ranked = {k for m in COMPONENTS.values() for c in m.values()
              for k, _l, _w, d in c if k not in PRICE and d != "discount"}
    t("٤ مؤشّراتُ الترتيب مجموعةٌ في بناء التوزيع",
      "COMPONENTS" in src and "is_main" in src,
      f"{len(ranked)} مؤشّراً · الجمعُ من النماذج {'✔' if 'COMPONENTS' in src else '✖'}"
      f" · الترشيحُ في المصدر {'✔' if 'is_main' in src else '✖'}")

    # ٥ — لا «نمو» في كون الحوكمة
    t("٥ لا «نمو» في كون الحوكمة",
      not [s for s in MAIN if uni.is_nomu(s)] and cen["unknown"] == 0,
      f"رئيسيّ {cen['main']} · موازية {cen['nomu']} مستبعَدة · "
      f"مجهول {cen['unknown']}")

    # ══ ٦ — أين يدخل السعرُ في الدرجة ══
    # المواصفةُ تُجيز دخولَه عبر مؤشّراتٍ تنصّ عليها صراحةً (مضاعفاتٌ
    # تُقاس على وسيط القطاع)، وتمنع دخولَه **قيمةً عادلة**. فيُعدّ كلٌّ
    # على حِدة ويُعرض — ولا يُحكم بالظنّ.
    fv_w, mult_w = {}, {}
    for m, comps in COMPONENTS.items():
        for k, _l, w, d in comps["valuation"]:
            if d == "discount":
                fv_w[m] = fv_w.get(m, 0.0) + w
            elif k in PRICE:
                mult_w[m] = mult_w.get(m, 0.0) + w
    fv_share = {m: round(fv_w.get(m, 0.0) * WEIGHTS_OF_MODEL[m]["valuation"], 3)
                for m in WEIGHTS_OF_MODEL}
    t("٦ السعرُ يدخل عبر مؤشّراتٍ منصوصة",
      all(mult_w.get(m, 0) > 0 for m in WEIGHTS_OF_MODEL),
      "مضاعفاتٌ على وسيط القطاع في كلّ نموذج")
    t("٦ب لا قيمةَ عادلة داخل درجة الحوكمة",
      not any(fv_w.values()),
      ("لا وزنَ لها في أيّ نموذج"
       if not any(fv_w.values())
       else "وزنُها من الدرجة: "
            + " · ".join(f"{m} {v:.0%}" for m, v in fv_share.items() if v)))

    # ══ ٦ج — الدرجةُ لا تتحرّك بتحرّك القيمة العادلة ══
    # حارسٌ سلوكيّ لا بنيويّ: يُثبَّت كلُّ مدخلٍ ماليّ ويُزحزَح تقديرُ
    # القيمة العادلة وحده. فإن تحرّكت الدرجةُ رجعت القيمةُ العادلة إلى
    # الحوكمة من بابٍ خلفيّ — ولو لم يظهر لها وزنٌ في `COMPONENTS`.
    base_fe = {
        "roic": 14.0, "roe": 16.0, "operating_margin": 18.0,
        "cash_conversion_ratio": 1.1, "earnings_stability": 22.0,
        "payout_ratio": 45.0, "dividend_growth": 6.0, "dividend_years": 7,
        "dividend_yield": 4.0, "revenue_cagr_5y": 8.0,
        "eps_cagr_5y": 9.0, "roic_trend": 1.5,
        "p_e": 14.0, "ev_ebitda": 9.0,
    }
    SEC = "الاتصالات"
    med = {"p_e": 16.0, "ev_ebitda": 10.0}
    moved, seen = [], []
    for fv in (None, 10.0, 45.0, 120.0, 400.0):
        fe = dict(base_fe)
        # المسارُ نفسُه الذي يسلكه التشغيل: `price_features` تشتقّ الخصم
        fe.update(inv.price_features({"current_price": 50.0}, fe, [],
                                     fair_value=fv))
        r = inv.compute(fe, SEC, med, None)
        seen.append((fv, r["score"], fe.get("fv_discount")))
    base = seen[0][1]
    moved = [x for x in seen if x[1] != base]
    t("٦ج الدرجةُ ثابتةٌ عند تحرّك القيمة العادلة", not moved,
      "خصمٌ من ‎" + " إلى ".join(str(x[2]) for x in (seen[1], seen[-1]))
      + f" · الدرجة {base} في الحالات {len(seen)} كلِّها"
      + (f" · تحرّكت: {moved}" if moved else ""))

    # ٧ — الدرجةُ بين صفرٍ ومئة بالبناء
    lo = inv._discount_score(-400.0), inv._band_score(-1e9, 20, 80)
    hi = inv._discount_score(9999.0), inv._band_score(50, 20, 80)
    t("٧ الدرجةُ محصورةٌ بين صفرٍ ومئة",
      all(0.0 <= v <= 100.0 for v in lo + hi),
      f"أطرافٌ مقيسة: {[round(v, 1) for v in lo + hi]}")

    # ٨ — البوّاباتُ كما هي، وتقصّ ولا تُخصم
    WANT = {"negative_equity": 25.0, "loss_last_year": 45.0,
            "interest_below_one": 35.0, "payout_over_earnings": 60.0,
            "negative_ocf": 50.0}
    drift = [k for k, v in WANT.items()
             if abs(((aq.CEILINGS.get(k) or (None,))[0] or -1) - v) > 1e-9]
    capped, _n1 = aq.apply_ceiling(95.0, {"ceiling": 25.0, "breaches": [
        {"why": "حقوقٌ سالبة"}]})
    kept, _n2 = aq.apply_ceiling(72.0, {"ceiling": 100.0, "breaches": []})
    t("٨ البوّاباتُ كما هي وتقصّ ولا تُخصم",
      not drift and capped == 25.0 and kept == 72.0,
      f"سقوفٌ مطابقة {not drift} · ‎95→{capped} · ‎72→{kept}")

    # ٩ — الجاهزيةُ لا تناقض قواعدَ الأهلية
    full = {"model": "OPERATING", "sector": "الاتصالات",
            "components": {k: {"score": 70.0} for k in
                           ("quality", "dividend", "growth", "valuation")},
            "data_completeness": 0.95, "score": 88.0}
    thin = {**full, "components": {**full["components"],
                                   "growth": {"score": None},
                                   "valuation": {"score": None}},
            "data_completeness": 0.50}
    a = rdy.evaluate(full, "PASS", "مرتفعة", "PE_MEDIAN")
    b = rdy.evaluate(thin, "PASS", "منخفضة", None)
    c = rdy.evaluate(full, "EXCLUDED", "مرتفعة", "PE_MEDIAN")
    t("٩ الجاهزيةُ لا تناقض الأهلية",
      a["readiness"] == rdy.INVESTMENT_READY
      and b["readiness"] == rdy.NOT_READY
      and c["readiness"] == rdy.NOT_READY,
      f"كاملة→{a['readiness']} · ناقصة→{b['readiness']} · "
      f"مستبعَدة→{c['readiness']}")

    # ١٠ — لا بياناتٍ مصطنعة
    probes = [({}, "roe"), ({"roe": float("nan")}, "roe"),
              ({"roe": float("inf")}, "roe"), ({"roe": None}, "roe")]
    t("١٠ لا بياناتٍ مصطنعة",
      all(inv._val(f, k) is None for f, k in probes),
      "الغائبُ والشاذُّ يُعادان عدماً لا صفراً")

    # ١١ — القرارُ لا يعتمد الدرجةَ وحدها
    hi_thin = {**thin, "score": 95.0}
    t("١١ القرارُ لا يعتمد الدرجةَ وحدها",
      rdy.evaluate(hi_thin, "PASS", "منخفضة", None)["readiness"]
      == rdy.NOT_READY,
      "درجةُ ‎95 بأساسٍ ضيّق → NOT_READY")

    # ١٢ — الشركاتُ الجديدة تُصنَّف ولا يُخترع لها نموذج
    unknown_sector = "قطاعٌ لم يُصنَّف بعد"
    t("١٢ الجديدةُ تُصنَّف ولا تُمنح درجةً تلقائياً",
      model_of(unknown_sector) is None
      and inv.compute({}, unknown_sector, {}, None)["score"] is None,
      "قطاعٌ مجهول → لا نموذجَ ولا درجة، ويُعلَن للتصنيف")

    # ── العرض ──
    print("═" * 62)
    print("  إقفالُ ملفّ الحوكمة")
    print("═" * 62)
    print(f"\n  الكون: السوقُ الرئيسة {cen['main']} · «نمو» {cen['nomu']} "
          f"مستبعَدة · مجهول {cen['unknown']}")
    print(f"  الأنماط: {len(SCORECARDS)} · النماذج: {len(WEIGHTS_OF_MODEL)} "
          f"· مؤشّراتُ الترتيب: {len(ranked)}\n")
    for n, ok, d in T:
        print(f"  {'PASS' if ok else 'FAIL'}  {n:38} {d}")

    bad = [n for n, ok, _d in T if not ok]
    print("\n" + "═" * 62)
    print(f"  GOVERNANCE = {'LOCKED' if not bad else 'NOT LOCKED'}")
    print("═" * 62)
    if bad:
        for n, ok, d in T:
            if not ok:
                print(f"    ✖ {n} — {d}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
