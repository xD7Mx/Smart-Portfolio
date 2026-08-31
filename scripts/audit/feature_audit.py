"""تشخيصُ طبقة البيانات — لماذا لا يقوم مكوّن، سمةً سمةً.

## لماذا تشخيصٌ قبل إصلاح

قِيس على السوق: التقييمُ ‎0 من ‎268 والنموُّ ‎17. ورقمٌ كهذا لا يُعالَج
بتخفيف شرطٍ ولا بتعديل وزن — يُعالَج بمعرفة **أيُّ بندٍ لم يصل ولماذا**.
وقد أخطأتُ في هذا المشروع ستَّ مرّاتٍ حين استنتجتُ من عيّنةٍ نظيفة ما
لا تقوله بياناتُ السوق.

فهذا السكربتُ لا يحسب درجةً ولا يغيّرها. يمرّ على السوق ويُخرج لكلّ
سمةٍ في كلّ مكوّن:

    اسمُ السمة · المصدرُ في الأنبوب · REPORTED أم DERIVED ·
    كم شركةً توفّرت لها · كم أخفقت · سببُ الإخفاق الحقيقيّ ·
    الحقلُ الذي يبحث عنه الكود · الحقلُ البديلُ الموجودُ فعلاً

وسببُ الإخفاق يُقرأ من **البنود الخام** لا من تخميني: إن غاب `eps`
قيل «البندُ لم يرد»، وإن ورد وكان سالباً قيل «المقامُ غيرُ موجب»،
وإن كانت الفتراتُ أقلَّ من المطلوب قيل ذلك بعددها.

    docker exec sp_backend python /app/scripts/audit/feature_audit.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ══ خريطةُ السمة إلى بنودها الخام ══
#
# لكلّ سمةٍ: (المصدر، النوع، البنودُ التي لا تقوم بدونها، أقلُّ فترات،
#             بنودٌ بديلةٌ يُبحث عنها في الخام إن غاب الأصل)
#
# «REPORTED» بندٌ ورد كما هو · «DERIVED» محسوبٌ من بنودٍ واردة.
SOURCES: dict[str, tuple] = {
    # ── الجودة ──
    "roe": ("financial_features", "DERIVED", ("net_income", "total_equity"), 1, ()),
    "roe_stability": ("financial_features", "DERIVED", ("net_income", "total_equity"), 3, ()),
    "eps_stability": ("financial_features", "DERIVED", ("eps",), 3, ("net_income", "shares_outstanding")),
    "earnings_stability": ("financial_features", "DERIVED", ("net_income",), 3, ()),
    "leverage_x": ("sector_metrics", "DERIVED", ("total_assets", "total_equity"), 1, ()),
    "roic": ("financial_features", "DERIVED", ("operating_income", "total_equity", "total_debt"), 1, ()),
    "operating_margin": ("financial_features", "DERIVED", ("operating_income", "revenue"), 1, ()),
    "cash_conversion_ratio": ("financial_features", "DERIVED", ("operating_cash_flow", "net_income"), 1, ()),
    "net_debt_ebitda": ("sector_metrics", "DERIVED", ("total_debt", "ebitda"), 1, ("operating_income", "depreciation")),
    "interest_coverage": ("market_data", "DERIVED", ("operating_income", "interest_expense"), 1, ("ebit",)),
    "ltv_pct": ("sector_metrics", "DERIVED", ("total_debt", "total_assets"), 1, ()),
    "inventory_intensity": ("sector_metrics", "DERIVED", ("inventory", "total_assets"), 1, ()),
    "normalized_eps": ("financial_features", "DERIVED", ("eps",), 3, ("net_income", "shares_outstanding")),
    "worst_leverage": ("sector_metrics", "DERIVED", ("total_debt", "ebitda"), 3, ()),
    "fcf_margin": ("financial_features", "DERIVED", ("free_cash_flow", "revenue"), 1, ("operating_cash_flow", "capex")),
    "roic_cycle": ("sector_metrics", "DERIVED", ("operating_income", "total_assets"), 5, ()),
    # ── التوزيعات ──
    "dividend_yield": ("price_features", "DERIVED", ("_dividend_per_share", "_current_price"), 0, ()),
    "dividend_growth": ("financial_features", "DERIVED", ("dividends_paid",), 3, ()),
    "dividend_years": ("financial_features", "DERIVED", ("dividends_paid",), 1, ()),
    "payout_ratio": ("financial_features", "DERIVED", ("dividends_paid", "net_income"), 1, ()),
    "ffo_payout": ("sector_metrics", "DERIVED", ("net_income", "depreciation", "dividends_paid"), 1, ()),
    # ── النموّ ──
    "eps_cagr_5y": ("financial_features", "DERIVED", ("eps",), 5, ("net_income", "shares_outstanding")),
    "revenue_cagr_5y": ("financial_features", "DERIVED", ("revenue",), 5, ()),
    "book_value_cagr_5y": ("financial_features", "DERIVED", ("total_equity", "shares_outstanding"), 5, ()),
    "eps_cagr_3y": ("financial_features", "DERIVED", ("eps",), 3, ("net_income", "shares_outstanding")),
    "revenue_cagr_3y": ("financial_features", "DERIVED", ("revenue",), 3, ()),
    "book_value_cagr_3y": ("financial_features", "DERIVED", ("total_equity", "shares_outstanding"), 3, ()),
    "roic_trend": ("financial_features", "DERIVED", ("operating_income", "total_assets"), 3, ()),
    "ffo": ("sector_metrics", "DERIVED", ("net_income", "depreciation"), 1, ()),
    # ── التقييم ──
    "p_e": ("price_features", "DERIVED", ("eps", "_current_price"), 1, ("net_income", "shares_outstanding")),
    "p_b": ("price_features", "DERIVED", ("_book_value_per_share", "_current_price"), 1, ("total_equity", "shares_outstanding")),
    "p_e_normalized": ("price_features", "DERIVED", ("_normalized_eps", "_current_price"), 3, ()),
    "ev_ebitda": ("price_features", "DERIVED", ("shares_outstanding", "ebitda", "total_debt", "_current_price"), 1, ("operating_income", "depreciation")),
    "p_ffo": ("sector_metrics", "DERIVED", ("net_income", "depreciation", "shares_outstanding", "_current_price"), 1, ()),
    "fv_discount": ("fair_value", "DERIVED", ("_fair_value", "_current_price"), 2, ()),
}


def _present(periods: list[dict], line: str) -> int:
    """كم فترةً ورد فيها هذا البندُ رقماً."""
    return sum(1 for p in periods
               if isinstance(p.get(line), (int, float)))


async def main(argv: list[str]) -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.economic_models import COMPONENTS, model_of
    from app.services import investment_score as inv
    from app.services.four_scores import build_company_features
    from app.services.market_data import market_service

    limit = next((int(a) for a in argv if a.isdigit()), None)

    # ── حصادُ السوق: قوائمُ وسعرٌ لكلّ شركة ──
    print("═" * 78)
    print("  قراءةُ السوق — قوائمُ وتسعيرة")
    print("═" * 78)
    rows: list[dict] = []
    no_price = 0
    for sym, meta in MARKET_UNIVERSE.items():
        if sym.startswith("9"):
            continue
        if limit and len(rows) >= limit:
            break
        try:
            data = await market_service.get_financials(f"{sym}.SR",
                                                       allow_supplement=False)
        except Exception:                                         # noqa: BLE001
            continue
        ps = (data or {}).get("periods") or []
        if len(ps) < 2:
            continue
        # ══ السعرُ يُطلب صراحةً ══
        # لا يمرّ في خطّ السمات: `build_company_features` يعيد
        # (‏eps · book_value · roe) فقط. ومسبارٌ لا يطلبه يقيس صفراً
        # في التقييم ويظنّه شحّاً في البيانات.
        info = {}
        try:
            ci = await market_service.get_company_info(f"{sym}.SR")
            if isinstance(ci, dict):
                info = dict(ci)
        except Exception:                                         # noqa: BLE001
            pass
        if not isinstance(info.get("current_price"), (int, float)):
            no_price += 1
        rows.append({"sym": sym, "sector": meta.get("sector"),
                     "ps": ps, "info": info})

    print(f"  {len(rows)} شركة · {no_price} بلا سعرٍ واصل\n")

    # ── لكلّ سمةٍ: توفّرَت أم لا، ولماذا ──
    stat: dict[str, Counter] = defaultdict(Counter)
    alts: dict[str, Counter] = defaultdict(Counter)

    for r in rows:
        ps, info, sector = r["ps"], r["info"], r["sector"]
        model = model_of(sector)
        if model is None:
            continue
        try:
            fe, inf, _ = build_company_features(ps, info=info, sector=sector)
            merged = dict(inf or {})
            merged.update(info)
            px = inv.price_features(merged, fe, ps)
            feats = {**fe, **px}
        except Exception as e:                                    # noqa: BLE001
            stat["__crash__"][type(e).__name__] += 1
            continue

        wanted = {k for comp in COMPONENTS[model].values()
                  for k, *_ in comp}
        for key in wanted:
            src, kind, lines, need_n, alt = SOURCES.get(
                key, ("?", "?", (), 0, ()))
            if inv._val(feats, key) is not None:
                stat[key]["ok"] += 1
                continue
            # ── سببُ الإخفاق من البنود الخام لا من التخمين ──
            gone = []
            for ln in lines:
                if ln.startswith("_"):
                    real = ln[1:]
                    have = (isinstance(info.get(real), (int, float))
                            or inv._val(feats, real) is not None)
                    if not have:
                        gone.append(real)
                elif _present(ps, ln) == 0:
                    gone.append(ln)
            if gone:
                stat[key]["|".join(sorted(gone)) + " — لم يرد"] += 1
                for a in alt:
                    if _present(ps, a) > 0:
                        alts[key][a] += 1
            elif need_n and len(ps) < need_n:
                stat[key][f"يلزم {need_n} فترات والمتاح {len(ps)}"] += 1
            else:
                stat[key]["البنودُ واردةٌ والحسابُ لم ينتج — مقامٌ صفرٌ أو سالب"] += 1

    # ── العرض ──
    for model in ("FINANCIAL", "REIT", "CYCLICAL", "OPERATING", "REAL_ESTATE"):
        n_model = sum(1 for r in rows if model_of(r["sector"]) == model)
        if not n_model:
            continue
        print("═" * 78)
        print(f"  {model}  —  {n_model} شركة")
        print("═" * 78)
        for comp in ("quality", "dividend", "growth", "valuation"):
            print(f"\n  ── {comp} ──")
            for key, label, weight, _d in COMPONENTS[model][comp]:
                src, kind, lines, need_n, _alt = SOURCES.get(
                    key, ("?", "?", (), 0, ()))
                c = stat.get(key, Counter())
                ok = c.get("ok", 0)
                bad = sum(v for k, v in c.items() if k != "ok")
                print(f"    {key:22} {src:18} {kind:9} "
                      f"توفّر {ok:>4} · أخفق {bad:>4}")
                print(f"    {'':22} يبحث عن: {', '.join(lines) or '—'}")
                for why, n in c.most_common(3):
                    if why != "ok":
                        print(f"    {'':22} ✖ {n:>4}  {why}")
                if alts.get(key):
                    a = "، ".join(f"{k} ({v})" for k, v in alts[key].most_common(3))
                    print(f"    {'':22} ← بديلٌ موجودٌ خاماً: {a}")

    if stat.get("__crash__"):
        print("\n  سقوطٌ أثناء البناء:")
        for k, v in stat["__crash__"].most_common():
            print(f"    {k}: {v}")

    print("\n" + "═" * 78)
    print("  لا درجةَ حُسبت هنا ولا غُيّرت. هذا تشخيصٌ فقط.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
