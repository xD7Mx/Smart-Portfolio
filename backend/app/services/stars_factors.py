"""نموذجُ العائلات الثماني لنجوم تاسي (D540) — محاكاةُ منهجية InvestingPro ProPicks.

ProPicks يتعلّم من التاريخ أيَّ المقاييس سبقت تفوّقَ السهم على المؤشّر، ويجمعها في
ثماني عائلات. وهنا العائلاتُ نفسُها من بيانات «تداول» في التطبيق:

  ١ البياناتُ المالية        درجةُ الجودة المالية (محرّكُ الجودة)
  ٢ مضاعفاتُ التداول        البعدُ إلى السعر العادل · مكرّرُ الربحية مقابلَ القطاع
  ٣ زخمُ الأسعار            عائدُ 12 شهراً · البعدُ عن م200 · البعدُ عن م50
  ٤ كفاءةُ الأصول            العائدُ على الأصول · دورانُ الأصول
  ٥ اتجاهاتُ الربحية         نموُّ الربح والإيراد: آخرُ أربعة أرباعٍ على الأربعة قبلها
  ٦ الديونُ والسيولة         نسبةُ المطلوبات (داخلَ القطاع) · التدفّقُ النقديُّ الحرّ على الأصول
  ٧ تصنيفُ الصناعة          زخمُ القطاع: متوسّطُ عائد 12 شهراً لشركاته
  ٨ إجراءاتُ الشركة          عائدُ التوزيع · انتظامُ التوزيع (سنواتٌ من ثلاث) · المنحُ في سنتين

كلُّ مقياسٍ يُحوَّل رتبةً مئويةً (0–1) بين المرشّحين، والعائلةُ متوسّطُ مقاييسها
المتوفّرة. والمرحلةُ الأولى بأوزانٍ متساوية؛ والثانيةُ تُعايرها باختبارٍ تاريخيٍّ على
بياناتٍ منشورةٍ في وقتها.
"""
from __future__ import annotations

from datetime import date, timedelta

FAMILIES = [
    ("financial", "البيانات المالية"),
    ("multiples", "مضاعفات التداول"),
    ("momentum", "زخم الأسعار"),
    ("efficiency", "كفاءة الأصول"),
    ("profit_trend", "اتجاهات الربحية"),
    ("debt", "الديون والسيولة"),
    ("industry", "تصنيف الصناعة"),
    ("corporate", "إجراءات الشركة"),
]
WEIGHTS = {k: 1 / len(FAMILIES) for k, _ in FAMILIES}      # المرحلةُ الأولى: متساوية


def _n(v):
    return float(v) if isinstance(v, (int, float)) else None


def _statements(sym: str) -> dict:
    """مقاييسُ القوائم: العائدُ على الأصول ودورانُها، ونموُّ آخر أربعة أرباع، والمديونية."""
    from app.services import tadawul_xbrl
    out: dict = {}
    try:
        ann = tadawul_xbrl.for_symbol(sym, "annual") or []
        qs = sorted(tadawul_xbrl.for_symbol(sym, "quarterly") or [], key=lambda p: str(p.get("as_of")))
    except Exception:                                             # noqa: BLE001
        return out
    last = ann[-1] if ann else {}
    ta, ni, rev = _n(last.get("total_assets")), _n(last.get("net_income")), _n(last.get("revenue"))
    if ta and ta > 0:
        if ni is not None:
            out["roa"] = ni / ta
        if rev is not None:
            out["turnover"] = rev / ta
        fcf = _n(last.get("free_cash_flow"))
        if fcf is not None:
            out["fcf_assets"] = fcf / ta
    dr = _n(last.get("debt_ratio"))
    if dr is not None:
        out["debt_ratio"] = dr

    def ttm_growth(key):
        # ‏D542: الربعُ الرابعُ غائبٌ من الأرباع (يأتي في السنويّ)، فكان شرطُ ثمانية أرباعٍ
        # متتالية لا يتحقّق لأحد. فيُقارَن كلُّ ربعٍ من آخر أربعةٍ بمقابله قبل سنة.
        own = [p for p in qs if p.get("col") in (None, 0) and _n(p.get(key)) is not None]
        by = {str(p.get("as_of"))[:7]: _n(p.get(key)) for p in own}
        a = b = 0.0
        n = 0
        for p in own[-4:]:
            k = str(p.get("as_of"))[:7]
            prev = by.get(f"{int(k[:4]) - 1}{k[4:]}")
            if prev is not None:
                a += _n(p.get(key)); b += prev; n += 1
        return (a - b) / abs(b) if n and b else None
    for key, name in (("net_income", "ni_growth"), ("revenue", "rev_growth")):
        g = ttm_growth(key)
        if g is not None:
            out[name] = max(-2.0, min(2.0, g))
    return out


def _dividends(sym: str) -> dict:
    from app.services import lastgood
    rows = ((lastgood.load(f"div:tadawul:{sym}") or {}).get("rows")) or []
    since = (date.today() - timedelta(days=3 * 365)).isoformat()
    years = {str(r.get("eligibility"))[:4] for r in rows
             if r.get("eligibility") and str(r["eligibility"]) >= since and (r.get("amount") or 0) > 0}
    return {"div_years": len(years) / 3}


def _pct_rank(vals: list[float]) -> list[float]:
    from app.services.tasi_stars import _pct_rank as pr
    return pr(vals)


def score_all(cands: list[dict], bonus: set[str] | None = None) -> dict[str, dict]:
    """cands: صفوفُ الفرز المؤهّلة (فيها ret_12m) — يعيد لكلّ رمزٍ عائلاتِه ودرجتَه."""
    if not cands:
        return {}
    bonus = bonus or set()
    sec_ret: dict[str, list[float]] = {}
    for r in cands:
        if _n(r.get("ret_12m")) is not None:
            sec_ret.setdefault(r.get("sector") or "", []).append(r["ret_12m"])
    sec_avg = {k: sum(v) / len(v) for k, v in sec_ret.items() if v}

    raw: dict[str, dict] = {}
    for r in cands:
        s = str(r.get("symbol"))
        st = _statements(s)
        dv = _dividends(s)
        pe, spe = _n(r.get("pe_ratio")), _n(r.get("sector_pe"))
        frames = (r.get("frames") or {}).get("D") or r
        raw[s] = {
            "financial": {"q": _n(r.get("finance_score"))},
            "multiples": {"up": min(_n(r.get("fair_value_upside_pct")) or 0, 60.0) if _n(r.get("fair_value_upside_pct")) is not None else None,
                          "cheap": (-(pe / spe)) if pe and spe and pe > 0 and spe > 0 else None},
            "momentum": {"r12": _n(r.get("ret_12m")), "d200": _n(frames.get("dist_sma200")),
                         "d50": _n(frames.get("dist_sma50"))},
            "efficiency": {"roa": st.get("roa"), "turn": st.get("turnover")},
            "profit_trend": {"ni": st.get("ni_growth"), "rev": st.get("rev_growth")},
            "debt": {"low_debt": (-st["debt_ratio"]) if "debt_ratio" in st else None, "fcf": st.get("fcf_assets")},
            "industry": {"sec": sec_avg.get(r.get("sector") or "")},
            "corporate": {"dy": _n(r.get("dividend_yield")), "reg": dv["div_years"],
                          "bonus": 1.0 if s in bonus else 0.0},
        }

    syms = list(raw)
    # المديونيةُ تُقارَن داخلَ القطاع (البنكُ مطلوباتُه ودائع) — وسائرُ المقاييس على السوق.
    ranks: dict[str, dict[str, float]] = {s: {} for s in syms}
    metric_keys = {(f, m) for s in syms for f, ms in raw[s].items() for m in ms}
    for fam, m in metric_keys:
        groups = {"": syms}
        if (fam, m) == ("debt", "low_debt"):
            groups = {}
            for s in syms:
                groups.setdefault(next((r.get("sector") for r in cands if str(r.get("symbol")) == s), "") or "", []).append(s)
        for g in groups.values():
            have = [s for s in g if raw[s][fam].get(m) is not None]
            if len(have) < 2:
                continue
            pr = _pct_rank([raw[s][fam][m] for s in have])
            for s, v in zip(have, pr):
                ranks[s][f"{fam}.{m}"] = v

    out: dict[str, dict] = {}
    for s in syms:
        fams = {}
        for fam, _ in FAMILIES:
            vs = [v for k, v in ranks[s].items() if k.startswith(fam + ".")]
            fams[fam] = sum(vs) / len(vs) if vs else 0.5          # عائلةٌ بلا قياسٍ: محايدة
        sc = sum(WEIGHTS[f] * fams[f] for f in fams) * 100
        out[s] = {"families": {k: round(v * 100) for k, v in fams.items()}, "score": round(sc, 1)}
    return out
