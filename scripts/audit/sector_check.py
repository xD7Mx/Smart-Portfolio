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



def main() -> int:
    from rank_check import company, _info
    from app.services.four_scores import build_company_features
    from app.services import investment_score as inv
    from app.services import spec_score, risk_gate, red_lines
    from app.data.economic_models import (COMPONENTS, FORBIDDEN,
                                          MODEL_OF_SECTOR, WEIGHTS, model_of)
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

    # ══ ثانياً: الأوزان مثبَّتة ══
    if WEIGHTS != {"quality": 0.40, "dividend": 0.25,
                   "growth": 0.20, "valuation": 0.15}:
        fails.append("الأوزانُ غُيّرت — والمواصفةُ تمنع تغييرها")
    print(f"\n  الأوزان {WEIGHTS} "
          f"{'✔' if not fails or 'الأوزان' not in fails[-1] else '✖'}")

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
