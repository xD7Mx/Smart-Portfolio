"""السلامةُ الماليةُ بخمسة محاور — ترتيبٌ داخل قطاع «تداول» الرسميّ (D469).

بأمر المالك: «طوِّر المحرّكين». وقِيست بنيةُ «InvestingPro» من صوره (العثيم
4001: القيمة 2.46 · الزخم 0.56 · التدفّق 1.98 · الربحية 2.45 · النمو 1.88 ·
الكلّ 1.86 = متوسّطُ المحاور): لكلّ مقياسٍ نقطةٌ مئويةٌ بين الشركات، ودرجتُه
‏5 × النقطة (أو 5 × (1 − النقطة) لما الأقلُّ فيه أفضل)، والمحورُ متوسّطُ
مقاييسه. ونتفوّق عليه بثلاث:

  · **الأقرانُ من قطاع «تداول» الرسميّ** (23 مجموعةً صناعية) لا خليطٌ عالميّ.
  · **كلُّ محورٍ يُشرح بجملة**: أقوى مقياسٍ وأضعفُه بقيمتيهما — لا «عادل» بلا سبب.
  · **المدخلاتُ من إفصاح XBRL الرسميّ** والسعرُ من لقطة «تداول».

والزخمُ من لقطة «تداول» وحدَها (موقعُ السعر في نطاق 52 أسبوعاً وبعدُه عن
قمّته وقاعه) — لا تاريخَ أسعارٍ للقطاع كلِّه يُجلب في كلّ طلب؛ ويُقال ذلك.
"""
from __future__ import annotations

import statistics
from typing import Optional

from loguru import logger

MIN_PEERS = 4

# (المفتاح، الاسم، المحور، الأعلى أفضل؟)
METRICS = [
    ("pe", "مكرّرُ الربحية", "value", False),
    ("pb", "مضاعفُ الدفترية", "value", False),
    ("ps", "مضاعفُ المبيعات", "value", False),
    ("ev_ebit", "قيمةُ المنشأة/الربح التشغيليّ", "value", False),
    ("ev_sales", "قيمةُ المنشأة/الإيراد", "value", False),
    ("fcf_yield", "عائدُ التدفّق الحرّ", "value", True),
    ("div_yield", "عائدُ التوزيعات", "value", True),
    ("net_margin", "هامشُ صافي الربح", "profit", True),
    ("ebit_margin", "هامشُ الربح التشغيليّ", "profit", True),
    ("roe", "العائدُ على الحقوق", "profit", True),
    ("roa", "العائدُ على الأصول", "profit", True),
    ("rev_growth", "نموُّ الإيراد (سنويّ)", "growth", True),
    ("ni_growth", "نموُّ صافي الربح (سنويّ)", "growth", True),
    ("ebit_growth", "نموُّ الربح التشغيليّ (سنويّ)", "growth", True),
    ("rev_cagr", "نموُّ الإيراد المركّب (3 سنوات)", "growth", True),
    ("ocf_to_ni", "جودةُ الأرباح (التشغيليّ ÷ الصافي)", "cash", True),
    ("fcf_margin", "هامشُ التدفّق الحرّ", "cash", True),
    ("interest_cover", "تغطيةُ الفوائد", "cash", True),
    ("debt_to_equity", "الدينُ إلى الحقوق", "cash", False),
    ("pos_52w", "موقعُ السعر في نطاق 52 أسبوعاً", "momentum", True),
    ("off_high", "البعدُ عن قمّة 52 أسبوعاً", "momentum", False),
    ("day_change", "تغيّرُ اليوم", "momentum", True),
]
PILLARS = {"value": "القيمة النسبية", "momentum": "زخمُ السعر", "cash": "سلامةُ التدفّق النقدي",
           "profit": "سلامةُ الربحية", "growth": "سلامةُ النمو"}
FMT_PCT = {"fcf_yield", "div_yield", "net_margin", "ebit_margin", "roe", "roa", "rev_growth", "ni_growth",
           "ebit_growth", "rev_cagr", "fcf_margin", "pos_52w", "off_high", "day_change"}


def label(score: float) -> str:
    return ("ضعيف" if score < 1.0 else "عادل" if score < 2.5 else "جيد" if score < 3.25
            else "جيد جداً" if score < 4.0 else "ممتاز")


def _n(x) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _g(a, b):
    return (a / b - 1) if (a is not None and b and b > 0) else None


def metrics_of(sym: str, row: dict, dps: float | None = None) -> dict | None:
    """مقاييسُ ورقةٍ واحدة من XBRL ولقطة «تداول» — أو None."""
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services.fair_value_models import _shares_of, _ttm_of
    px = _n((row or {}).get("price"))
    try:
        an, qu = X(sym, "annual") or [], X(sym, "quarterly") or []
    except Exception:                                              # noqa: BLE001
        return None
    if not px or not an:
        return None
    sh = _shares_of(an, qu)
    if not sh:
        return None
    ttm, _ = _ttm_of(qu, an)
    bal = (qu or an)[-1]
    mcap = px * sh
    debt, cash = _n(bal.get("total_debt")) or 0, _n(bal.get("ending_cash")) or 0
    ev = mcap + debt - cash
    rev, ni, ebit = _n(ttm.get("revenue")), _n(ttm.get("net_income")), _n(ttm.get("ebit"))
    ocf, capex = _n(ttm.get("operating_cash_flow")), _n(ttm.get("capex")) or 0
    fcf = (ocf - capex) if ocf is not None else None
    eq, ta, ie = _n(bal.get("equity")), _n(bal.get("total_assets")), _n(ttm.get("interest_expense"))
    prev = an[-2] if len(an) >= 2 else None
    last = an[-1]
    m = {
        "pe": mcap / ni if ni and ni > 0 else None,
        "pb": mcap / eq if eq and eq > 0 else None,
        "ps": mcap / rev if rev and rev > 0 else None,
        "ev_ebit": ev / ebit if ebit and ebit > 0 else None,
        "ev_sales": ev / rev if rev and rev > 0 else None,
        "fcf_yield": fcf / mcap if fcf is not None and mcap > 0 else None,
        "div_yield": (dps / px) if dps else 0.0,
        "net_margin": ni / rev if ni is not None and rev else None,
        "ebit_margin": ebit / rev if ebit is not None and rev else None,
        "roe": ni / eq if ni is not None and eq and eq > 0 else None,
        "roa": ni / ta if ni is not None and ta and ta > 0 else None,
        "rev_growth": _g(_n(last.get("revenue")), _n(prev.get("revenue")) if prev else None),
        "ni_growth": _g(_n(last.get("net_income")), _n(prev.get("net_income")) if prev else None),
        "ebit_growth": _g(_n(last.get("ebit")), _n(prev.get("ebit")) if prev else None),
        "rev_cagr": ((_n(an[-1].get("revenue")) / _n(an[0].get("revenue"))) ** (1 / (len(an) - 1)) - 1
                     if len(an) >= 2 and _n(an[0].get("revenue")) and _n(an[-1].get("revenue")) else None),
        "ocf_to_ni": ocf / ni if ocf is not None and ni and ni > 0 else None,
        "fcf_margin": fcf / rev if fcf is not None and rev else None,
        "interest_cover": ebit / ie if ebit is not None and ie and ie > 0 else None,
        "debt_to_equity": debt / eq if eq and eq > 0 else None,
    }
    hi, lo = _n(row.get("week52_high")), _n(row.get("week52_low"))
    if hi and lo and hi > lo:
        m["pos_52w"] = (px - lo) / (hi - lo)
        m["off_high"] = (hi - px) / hi
    m["day_change"] = _n(row.get("change_pct"))
    if m["day_change"] is not None:
        m["day_change"] /= 100
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}


def _pct_rank(x: float, xs: list[float]) -> float:
    """نسبةُ الأقران الذين دون القيمة (والمتساوي نصفٌ) — 0..1."""
    below = sum(1 for v in xs if v < x) + 0.5 * sum(1 for v in xs if v == x)
    return below / len(xs)


# ══ المصارفُ والتأمينُ والتمويلُ لا تُقاس بتدفّقٍ حرٍّ ولا ربحٍ تشغيليّ ══
# قِيس على الراجحي 1120: «هامشُ ربحٍ تشغيليّ 96٪» و«جودةُ أرباحٍ سالبة» — نموُّ
# دفتر القروض يظهر تدفّقاً تشغيلياً سالباً وهو نموٌّ صحّيّ، وهو عينُ ما يستبعده
# المحرّكُ الرئيسُ للمصارف (‏NO_DCF). فتسقط هذه المقاييسُ ويبقى ما يصحّ.
FIN_SKIP = {"ev_ebit", "ev_sales", "fcf_yield", "ebit_margin", "ocf_to_ni", "fcf_margin",
            "interest_cover", "ebit_growth", "debt_to_equity", "ps"}
FIN_TYPES = {"bank", "insurance", "financial"}


def score(sym: str, table: dict[str, dict], archetype: str | None = None) -> dict | None:
    me = table.get(sym)
    if not me:
        return None
    skip = FIN_SKIP if archetype in FIN_TYPES else set()
    pillars: dict[str, list[dict]] = {k: [] for k in PILLARS}
    for key, name, pil, higher in METRICS:
        if key in skip:
            continue
        x = me.get(key)
        xs = [t[key] for t in table.values() if isinstance(t.get(key), (int, float))]
        if not isinstance(x, (int, float)) or len(xs) < MIN_PEERS:
            continue
        p = _pct_rank(x, xs)
        s = 5 * (p if higher else 1 - p)
        pillars[pil].append({"key": key, "name": name, "value": x, "percentile": round(p * 100, 1),
                             "score": round(s, 2), "peers": len(xs),
                             "display": (f"{x*100:.1f}%" if key in FMT_PCT else f"{x:.2f}x")})
    out = []
    for pil, ms in pillars.items():
        if not ms:
            continue
        sc = statistics.mean(m["score"] for m in ms)
        best, worst = max(ms, key=lambda m: m["score"]), min(ms, key=lambda m: m["score"])
        why = (f"أقوى مقاييسه {best['name']} {best['display']} بدرجة {best['score']:.1f} من 5، وأضعفُها "
               f"{worst['name']} {worst['display']} بدرجة {worst['score']:.1f} من 5 — بين {best['peers']} شركةً في القطاع")
        out.append({"pillar": pil, "name": PILLARS[pil], "score": round(sc, 2), "label": label(sc),
                    "metrics": ms, "why": why})
    if not out:
        return None
    total = statistics.mean(p["score"] for p in out)
    return {"score": round(total, 2), "label": label(total), "pillars": out,
            "momentum_note": "الزخمُ من لقطة «تداول»: موقعُ السعر في نطاق 52 أسبوعاً وبعدُه عن قمّته وتغيّرُ اليوم"}


async def for_symbol(symbol: str) -> dict | None:
    from app.services import cache
    from app.services import tadawul_market as TM
    sym = str(symbol).replace(".SR", "").strip()
    ck = f"health:v3:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    rows = TM.usable_rows()[0] or {}
    if not rows:
        try:
            await TM.refresh()
        except Exception:                                          # noqa: BLE001
            pass
        rows = TM.usable_rows()[0] or {}
    me = rows.get(sym) or rows.get(sym + ".SR") or {}
    sector = me.get("sector_en")
    try:
        from app.data.universe import is_main
    except Exception:                                              # noqa: BLE001
        is_main = lambda s: True                                   # noqa: E731
    peers = [str(s).replace(".SR", "") for s, r in rows.items()
             if (r or {}).get("sector_en") == sector and is_main(str(s).replace(".SR", ""))]
    tk = f"health:table:{sector}"
    table = cache.get(tk)
    if table is None:
        table = {}
        for s in peers:
            r = rows.get(s) or rows.get(s + ".SR") or {}
            dps = None
            try:
                from app.services.tadawul_dividends import read as _div
                from datetime import date, timedelta
                d = await _div(s) or {}
                cut = (date.today() - timedelta(days=365)).isoformat()
                dps = sum(h["amount"] for h in (d.get("history") or []) if str(h.get("date")) >= cut) or None
            except Exception:                                      # noqa: BLE001
                pass
            m = metrics_of(s, r, dps)
            if m:
                table[s] = m
        cache.set(tk, table, 6 * 60 * 60)
    try:
        from app.services.statement_merge import archetype_of
        res = score(sym, table, archetype_of(sym))
        if res:
            res.update({"sector": sector, "peers": len(table)})
    except Exception as e:                                         # noqa: BLE001
        logger.warning("السلامةُ الماليةُ لـ{}: {}", sym, e)
        res = None
    cache.set(ck, res or {}, 6 * 60 * 60 if res else 30 * 60)
    return res
