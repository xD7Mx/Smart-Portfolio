"""نموذجُ الأبحاث (D547) — قراءةُ فريق أبحاثٍ لكلّ شركةٍ بعمق تاريخها في التطبيق.

قال المالك: «أريد تقويةَ نموذج التقرير ليكون لديه خبرةٌ بعمق تاريخ بيانات السوق…
أريد تدريبَ النموذج ليكون التقريرُ بناءً على فريق أبحاثٍ محترم».

والتدريبُ هنا حرفيّ لا مجازيّ: لكلّ شركةٍ ولكلّ بندٍ تُجرَّب طرقُ توقّعٍ معروفة على
**كلّ ربعٍ مضى** (سيرٌ إلى الأمام: يُتوقَّع الربعُ بما قبله وحده ثمّ يُقارَن بما نُشر)،
فيُختار لكلّ بندٍ أدقُّها في تاريخ الشركة نفسِها، ويُعلَن خطؤه الماضي ودقّةُ اتّجاهه.
فتوقّعُنا للربع القادم رأيُ طريقةٍ أثبتت نفسَها على هذه الشركة بعينها، لا معادلةٌ واحدةٌ
للسوق كلّه.

ومعه القراءةُ التاريخية التي يكتبها المحلّلُ قبل رأيه:
  · النموّ: المركّبُ السنويُّ للإيراد والربح عبر السنوات المنشورة، واتّجاهُ الهامش.
  · الموسمية: أيُّ الأرباع أقوى، بمتوسّط حصّته من السنة.
  · التقييمُ في تاريخه: مكرّرُ الربحية آخرَ كلّ سنة، وموقعُ اليوم من نطاقه.
  · السهمُ منذ 2010: عائدُه المركّب مقابلَ تاسي، وأقصى تراجع، وأفضلُ سنةٍ وأسوؤها.
  · التوزيعاتُ منذ 2010: سنواتُ التوزيع وانتظامُها ونموُّها.

المصادر: قوائمُ «تداول» (XBRL · حتى 2021 بالحصاد العميق)، والربعُ الرابعُ يُشتقّ
= السنويُّ − الأرباعِ الثلاثة (بنودُ التدفّق وحدها)، وأسعارُ ياهو الشهرية وتوزيعاتُها
(مخزنُ اختبار النجوم)، وتاسي «تداول». وما لا مصدرَ له لا يُكتب.
"""
from __future__ import annotations

import statistics
from datetime import date

FLOW = ("revenue", "ebit", "net_income_parent", "bank_nfi", "bank_op_income")
MIN_TRAIN = 4                      # أدنى عددِ أرباعٍ مقيسةٍ ليُختار بها


def _n(v):
    return float(v) if isinstance(v, (int, float)) else None


def _val(p: dict, key: str):
    v = _n(p.get(key))
    if v is None and key == "net_income_parent":
        v = _n(p.get("net_income"))
    return v


# ══ سلسلةُ الأرباع بربعٍ رابعٍ مشتقّ ══════════════════════════════════════
def quarter_series(quarterly: list[dict], annual: list[dict], key: str) -> list[tuple[str, float]]:
    """(نهايةُ الربع، القيمة) مرتّبةً — والربعُ الرابعُ = السنويُّ − الثلاثةِ قبله."""
    q = {}
    for p in quarterly or []:
        if p.get("col") not in (None, 0):
            continue
        a, v = str(p.get("as_of"))[:10], _val(p, key)
        if v is not None and len(a) == 10:
            q[a] = v
    for p in annual or []:
        a, v = str(p.get("as_of"))[:10], _val(p, key)
        if v is None or len(a) != 10 or not a.endswith("-12-31"):
            continue
        y = a[:4]
        parts = [q.get(f"{y}-03-31"), q.get(f"{y}-06-30"), q.get(f"{y}-09-30")]
        if a not in q and None not in parts:
            q[a] = v - sum(parts)
    return sorted(q.items())


# ══ طرقُ التوقّع المرشّحة ═══════════════════════════════════════════════
def _m_seasonal_growth(h: list[float]):
    """الربعُ المقابل × نموُّ آخر أربعةٍ على الأربعة قبلها."""
    if len(h) < 8 or sum(h[-8:-4]) == 0:
        return None
    return h[-4] * sum(h[-4:]) / sum(h[-8:-4])


def _m_seasonal(h: list[float]):
    """الربعُ المقابلُ من العام الماضي كما هو."""
    return h[-4] if len(h) >= 4 else None


def _m_last(h: list[float]):
    """الربعُ السابق كما هو."""
    return h[-1] if h else None


def _m_seasonal_ratio(h: list[float]):
    """الربعُ السابق × متوسّطِ نسبة هذا الموسم إلى سابقه في الأعوام الماضية."""
    rs = [h[i] / h[i - 1] for i in range(len(h) - 4, 0, -4) if i - 1 >= 0 and h[i - 1]]
    rs = [r for r in rs if 0 < r < 5]
    return h[-1] * statistics.fmean(rs) if rs and h else None


def _m_blend(h: list[float]):
    vs = [v for v in (_m_seasonal_growth(h), _m_seasonal(h), _m_last(h), _m_seasonal_ratio(h)) if v is not None]
    return statistics.fmean(vs) if vs else None


METHODS = {
    "seasonal_growth": ("الربعُ المقابلُ × نموُّ السنة", _m_seasonal_growth),
    "seasonal": ("الربعُ المقابلُ من العام الماضي", _m_seasonal),
    "last": ("الربعُ السابق", _m_last),
    "seasonal_ratio": ("الربعُ السابقُ × موسميّتُه", _m_seasonal_ratio),
    "blend": ("متوسّطُ الطرق", _m_blend),
}


def train(series: list[tuple[str, float]]) -> dict | None:
    """سيرٌ إلى الأمام على تاريخ البند: لكلّ طريقةٍ خطؤها المطلقُ النسبيّ الوسيط ودقّةُ
    اتّجاهها (هل صدقت في الصعود والهبوط عن الربع المقابل) — ويُختار الأدقّ."""
    vals = [v for _, v in series]
    scores = {}
    for k, (_, fn) in METHODS.items():
        errs, hits = [], []
        for t in range(4, len(vals)):
            f = fn(vals[:t])
            a = vals[t]
            if f is None or not a:
                continue
            errs.append(abs(f - a) / abs(a))
            if t >= 4 and vals[t - 4]:
                hits.append((f >= vals[t - 4]) == (a >= vals[t - 4]))
        if len(errs) >= MIN_TRAIN:
            scores[k] = {"mape": statistics.median(errs), "hit": sum(hits) / len(hits) if hits else None,
                         "n": len(errs)}
    if not scores:
        return None
    best = min(scores, key=lambda k: (scores[k]["mape"], k))
    return {"method": best, "label": METHODS[best][0], **scores[best], "all": scores}


def _next_quarter(last: str) -> str:
    y, m = int(last[:4]), int(last[5:7])
    return {3: f"{y}-06-30", 6: f"{y}-09-30", 9: f"{y}-12-31", 12: f"{y + 1}-03-31"}[m]


def forecast(quarterly: list[dict], annual: list[dict], key: str) -> dict | None:
    """توقّعُ الربع القادم بالطريقة التي أثبتت نفسَها على هذه الشركة — ومعه سجلُّها."""
    s = quarter_series(quarterly, annual, key)
    if len(s) < 5:
        return None
    tr = train(s)
    if not tr:
        return None
    v = METHODS[tr["method"]][1]([x for _, x in s])
    if v is None:
        return None
    return {"key": key, "as_of": _next_quarter(s[-1][0]), "value": round(v, 2), "method": tr["method"],
            "label": tr["label"], "mape": round(tr["mape"] * 100, 1),
            "hit": round(tr["hit"] * 100) if tr.get("hit") is not None else None,
            "tested": tr["n"], "history": len(s)}


def expected_at(quarterly: list[dict], annual: list[dict], key: str, as_of: str) -> float | None:
    """ما كان النموذجُ سيتوقّعه لربعٍ بعينه بما قبله وحده — لعمود «توقّعاتنا» في التقرير."""
    s = [x for x in quarter_series(quarterly, annual, key) if x[0] < as_of]
    if len(s) < 5:
        return None
    tr = train(s)
    if not tr:
        return None
    v = METHODS[tr["method"]][1]([x for _, x in s])
    return round(v, 2) if v is not None else None


# ══ القراءةُ التاريخية ═══════════════════════════════════════════════════
def _cagr(a, b, years):
    return round(((b / a) ** (1 / years) - 1) * 100, 1) if a and b and a > 0 and b > 0 and years > 0 else None


def growth(annual: list[dict]) -> dict:
    ys = [p for p in sorted(annual or [], key=lambda p: str(p.get("as_of"))) if str(p.get("as_of"))[5:10] == "12-31"]
    out = {"years": [str(p.get("as_of"))[:4] for p in ys]}
    if len(ys) >= 2:
        n = int(str(ys[-1]["as_of"])[:4]) - int(str(ys[0]["as_of"])[:4])
        for k, name in (("revenue", "rev_cagr"), ("net_income_parent", "ni_cagr")):
            out[name] = _cagr(_val(ys[0], k), _val(ys[-1], k), n)
        margins = [(_val(p, "net_income_parent") or 0) / _val(p, "revenue") for p in ys
                   if _val(p, "revenue") and _val(p, "net_income_parent") is not None]
        if len(margins) >= 2:
            out["margin_first"], out["margin_last"] = round(margins[0] * 100, 1), round(margins[-1] * 100, 1)
    return out


def seasonality(series: list[tuple[str, float]]) -> dict | None:
    """حصّةُ كلّ ربعٍ من سنته، متوسّطةً على السنوات الكاملة."""
    by_y: dict[str, dict[str, float]] = {}
    for a, v in series:
        by_y.setdefault(a[:4], {})[a[5:7]] = v
    shares: dict[str, list[float]] = {}
    for q in by_y.values():
        if len(q) == 4 and sum(q.values()) > 0:
            tot = sum(q.values())
            for m, v in q.items():
                shares.setdefault(m, []).append(v / tot)
    if not shares:
        return None
    avg = {m: round(statistics.fmean(v) * 100, 1) for m, v in shares.items()}
    names = {"03": "الأول", "06": "الثاني", "09": "الثالث", "12": "الرابع"}
    top = max(avg, key=avg.get)
    return {"shares": {names[m]: avg[m] for m in sorted(avg)}, "strongest": names[top],
            "years": len(next(iter(shares.values())))}


def price_history(months: list[tuple[str, float]], tasi: dict[str, float], divs: list) -> dict:
    """السهمُ منذ أوّل شهرٍ متاح: المركّبُ مقابلَ تاسي، وأقصى تراجع، والسنواتُ، والتوزيعات."""
    if len(months) < 13:
        return {}
    m = dict(months)
    first, last = months[0][0], months[-1][0]
    yrs = (int(last[:4]) - int(first[:4])) + (int(last[5:7]) - int(first[5:7])) / 12
    out = {"since": first, "cagr": _cagr(months[0][1], months[-1][1], yrs)}
    if first in tasi and last in tasi:
        out["tasi_cagr"] = _cagr(tasi[first], tasi[last], yrs)
    peak, dd = months[0][1], 0.0
    for _, v in months:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1)
    out["max_dd"] = round(dd * 100, 1)
    ye = {}
    for a, v in months:
        ye[a[:4]] = v
    ys = sorted(ye)
    rets = {y: round((ye[y] / ye[p] - 1) * 100, 1) for p, y in zip(ys, ys[1:]) if ye[p]}
    if rets:
        b, w = max(rets, key=rets.get), min(rets, key=rets.get)
        out["best"], out["worst"] = {"y": b, "r": rets[b]}, {"y": w, "r": rets[w]}
    dy = {}
    for d, a in divs or []:
        dy[d[:4]] = dy.get(d[:4], 0) + a
    if dy:
        paid = sorted(y for y, a in dy.items() if a > 0)
        span = list(range(int(paid[0]), date.today().year))
        out["div"] = {"since": paid[0], "years_paid": len(paid),
                      "regularity": round(sum(1 for y in span if str(y) in dy) / len(span) * 100) if span else None}
        full = [y for y in paid if int(y) < date.today().year]
        if len(full) >= 2:
            out["div"]["cagr"] = _cagr(dy[full[0]], dy[full[-1]], int(full[-1]) - int(full[0]))
    return out


def pe_band(annual: list[dict], months: dict[str, float], price: float | None) -> dict | None:
    """مكرّرُ الربحية آخرَ كلّ سنةٍ منشورة (سعرُ ديسمبر ÷ ربحية السهم) وموقعُ اليوم منه."""
    pts = []
    for p in annual or []:
        a = str(p.get("as_of"))[:10]
        eps = _n(p.get("eps"))
        px = months.get(a[:7])
        if a.endswith("12-31") and eps and eps > 0 and px and abs(eps) < 1000:
            pts.append((a[:4], round(px / eps, 1)))
    if len(pts) < 2:
        return None
    vals = [v for _, v in pts]
    out = {"points": pts, "low": min(vals), "high": max(vals), "median": round(statistics.median(vals), 1)}
    ttm_eps = None
    if price and annual:
        eps = _n(sorted(annual, key=lambda p: str(p.get("as_of")))[-1].get("eps"))
        ttm_eps = eps if eps and eps > 0 and abs(eps) < 1000 else None
    if ttm_eps:
        cur = round(price / ttm_eps, 1)
        out["current"] = cur
        out["position"] = round(sum(1 for v in vals if v <= cur) / len(vals) * 100)
    return out


def note(symbol: str, price: float | None = None) -> dict:
    """المذكّرةُ الكاملة لشركة: توقّعاتٌ مدرَّبةٌ وقراءةٌ تاريخية — من مخازن التطبيق وحدها."""
    from app.services import lastgood, tadawul_xbrl
    from app.services.stars_backtest import DATA_KEY, clean_months
    sym = str(symbol).replace(".SR", "").strip()
    q = tadawul_xbrl.for_symbol(sym, "quarterly") or []
    a = tadawul_xbrl.for_symbol(sym, "annual") or []
    bank = tadawul_xbrl._arch_of(sym) == "bank"
    keys = ("bank_nfi", "bank_op_income", "net_income_parent") if bank else ("revenue", "ebit", "net_income_parent")
    fc = {k: forecast(q, a, k) for k in keys}
    main = "bank_op_income" if bank else "revenue"
    bt = lastgood.load(DATA_KEY) or {}
    px = (bt.get("px") or {}).get(sym) or {}
    months = clean_months(px.get("m"))
    return {"symbol": sym, "bank": bank,
            "forecast": {k: v for k, v in fc.items() if v},
            "growth": growth(a),
            "seasonality": seasonality(quarter_series(q, a, main)),
            "price": price_history(months, bt.get("tasi") or {}, px.get("div") or []),
            "pe_band": pe_band(a, dict(months), price),
            "quarters": len(quarter_series(q, a, main))}
