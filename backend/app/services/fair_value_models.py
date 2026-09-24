"""محرّكُ القيمة العادلة متعدّدُ النماذج (D468).

بأمر المالك: «طوِّر المحرّكَين ليكونا أقوى نسخةٍ في السوق — لا نقلّد بل نتفوّق».
وقِيس المحرّكُ القائم على العثيم (4001): مسارٌ واحدٌ نجا (4.45) بلا نطاق، و
«InvestingPro» خمسةَ عشرَ نموذجاً متوسّطُها البسيط 6.06 ونطاقُها 3.68–8.49،
والمحللون 5.48 (4.00–7.00). ووُجد في نماذجهم ما نتفوّق عليه:

  · **أقرانٌ أجانب** (Metro · Loblaw · Albertsons) لسوق تجزئةٍ سعوديّ —
    وأقرانُنا من **قطاع «تداول» الرسميّ** (23 مجموعةً صناعية) وحدَه.
  · **متوسّطٌ بسيطٌ** يساوي نموذجاً افترض هبوطَ الأرباح 98٪ بنموذجٍ سليم —
    ومتوسّطُنا وسيطُ كلّ عائلةٍ ثمّ أوزانٌ بحسب نمط الشركة، وما شذّ يُستبعَد
    ويُسمّى سببُه.
  · **ربحٌ لربعٍ استثنائيّ يُعامَل أبدياً** — ونحن نُطبّع: هامشُ السنوات
    الثلاث على إيراد الاثني عشر شهراً، فخسارةُ ربعِ تطبيق نظامٍ لا تُسعَّر
    خسارةً دائمة، ويُذكر ذلك.

كلُّ نموذجٍ يُعيد قيمتَه ونطاقَه (بحساسية كلفة رأس المال والنموّ أو ربيعَي
مضاعفات الأقران) وافتراضاتِه بمصادرها — فلا رقمَ بلا أصل.
المدخلاتُ من إفصاح XBRL الرسميّ ولقطة «تداول» وجدول توزيعات «تداول».
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

# ══ ثوابتُ السوق — من المحرّك القائم نفسِه، فلا مسطرتان ══
try:
    from app.services.fair_value import (RISK_FREE, EQUITY_PREMIUM,
                                         MAX_SUSTAINABLE_GROWTH, _required_return)
except Exception:                                                  # noqa: BLE001
    RISK_FREE, EQUITY_PREMIUM, MAX_SUSTAINABLE_GROWTH = 0.05, 0.05, 0.035

    def _required_return(beta):                                    # type: ignore
        return RISK_FREE + EQUITY_PREMIUM

TERMINAL_G = 0.025          # نموٌّ نهائيٌّ دون السقف المستدام: أبديةٌ متحفّظة
MIN_PEERS = 3
FIN_TYPES = {"bank", "insurance", "financial"}

# أوزانُ العائلات بحسب النمط — المصرفُ لا يُقيَّم بتدفّقٍ حرّ، والصندوقُ العقاريُّ بتوزيعه
FAMILY_WEIGHTS = {
    "financial": {"equity": 0.55, "multiples": 0.45},
    "reit": {"income": 0.55, "multiples": 0.45},
    "default": {"cashflow": 0.35, "equity": 0.25, "multiples": 0.40},
}
FAMILY_NAMES = {"cashflow": "التدفّقات المخصومة", "equity": "الأرباح والحقوق",
                "income": "التوزيعات", "multiples": "مضاعفاتُ الأقران السعوديين"}


@dataclass
class Inputs:
    symbol: str
    price: float
    shares: float
    annual: list[dict]                       # الأقدمُ أوّلاً
    ttm: dict                                # تدفّقاتُ آخر أربعة أرباع (أو آخرُ سنة)
    balance: dict                            # أحدثُ ميزانية
    ttm_source: str
    archetype: str | None = None
    sector: str | None = None
    beta: float | None = None
    dps_ttm: float | None = None             # توزيعاتُ اثني عشر شهراً من جدول «تداول»
    peers: dict = field(default_factory=dict)  # اسمُ المضاعف ← قائمةُ قيم الأقران
    peer_symbols: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _n(x) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


# ══ الأسسُ المشتركة ═══════════════════════════════════════════════════════
@dataclass
class Base:
    ke: float                # كلفةُ حقوق الملكية
    wacc: float
    tax: float
    net_debt: float
    rev: float               # إيرادُ اثني عشر شهراً
    margin_n: float | None   # هامشُ صافي الربح المطبَّع
    ebit_margin_n: float | None
    fcf_margin_n: float | None
    ocf: float | None
    ni_n: float | None       # صافي ربحٍ مطبَّع
    ebit_n: float | None
    bvps: float | None
    roe_n: float | None
    growth: float            # نموُّ الإيراد السنويّ المقيَّد
    notes: list[str]


def base_of(i: Inputs) -> Base | None:
    a = i.annual[-3:]
    rev = _n(i.ttm.get("revenue")) or _n(a[-1].get("revenue") if a else None)
    if not rev or rev <= 0 or not i.shares or i.shares <= 0:
        return None
    notes: list[str] = []

    def margin(key):
        ms = [p[key] / p["revenue"] for p in a
              if _n(p.get(key)) is not None and _n(p.get("revenue")) and p["revenue"] > 0]
        return statistics.mean(ms) if ms else None

    m_ni, m_ebit = margin("net_income"), margin("ebit")
    fcfs = [(_n(p.get("operating_cash_flow")) or 0) - (_n(p.get("capex")) or 0) for p in a
            if _n(p.get("operating_cash_flow")) is not None]
    m_fcf = (statistics.mean([f / p["revenue"] for f, p in zip(fcfs, a) if _n(p.get("revenue"))])
             if fcfs else None)
    ttm_m = (_n(i.ttm.get("net_income")) or 0) / rev
    if m_ni is not None and abs(ttm_m - m_ni) > max(0.02, abs(m_ni) * 0.5):
        notes.append(f"هامشُ صافي الربح لاثني عشر شهراً {ttm_m*100:.1f}٪ يبعد عن متوسّط ثلاث "
                     f"سنوات {m_ni*100:.1f}٪ — طُبِّع على المتوسّط كي لا تُسعَّر سنةٌ استثنائيةٌ أبدياً")
    # كلفةُ حقوق الملكية وكلفةُ رأس المال
    ke = _required_return(i.beta)
    b = i.balance
    debt = _n(b.get("total_debt")) or 0.0
    cash = _n(b.get("ending_cash")) or 0.0
    int_exp = _n(i.ttm.get("interest_expense"))
    kd = min(max((int_exp / debt) if (int_exp and debt > 0) else RISK_FREE + 0.015, 0.03), 0.10)
    pre, ni = _n(i.ttm.get("pretax_income")), _n(i.ttm.get("net_income"))
    tax = min(max(1 - ni / pre, 0.0), 0.25) if (pre and ni is not None and pre > 0) else 0.10
    mcap = i.price * i.shares
    wacc = (mcap * ke + debt * kd * (1 - tax)) / (mcap + debt) if (mcap + debt) > 0 else ke
    eq = _n(b.get("equity"))
    bvps = eq / i.shares if eq and eq > 0 else None
    rois = [p["net_income"] / p["equity"] for p in a
            if _n(p.get("net_income")) is not None and _n(p.get("equity")) and p["equity"] > 0]
    roe_n = statistics.mean(rois) if rois else None
    revs = [p["revenue"] for p in a if _n(p.get("revenue")) and p["revenue"] > 0]
    g = ((revs[-1] / revs[0]) ** (1 / (len(revs) - 1)) - 1) if len(revs) >= 2 else 0.03
    g = min(max(g, 0.0), 0.12)
    return Base(ke=ke, wacc=max(wacc, RISK_FREE + 0.02), tax=tax, net_debt=debt - cash, rev=rev,
                margin_n=m_ni, ebit_margin_n=m_ebit, fcf_margin_n=m_fcf,
                ocf=_n(i.ttm.get("operating_cash_flow")),
                ni_n=(m_ni * rev) if m_ni is not None else ni,
                ebit_n=(m_ebit * rev) if m_ebit is not None else _n(i.ttm.get("ebit")),
                bvps=bvps, roe_n=roe_n, growth=g, notes=notes)


def _model(key, family, name, value, low, high, assumptions, note=None):
    if value is None or value <= 0:
        return None
    vals = [x for x in (low, value, high) if x is not None and x > 0]
    return {"key": key, "family": family, "name": name, "value": round(value, 2),
            "low": round(min(vals), 2), "high": round(max(vals), 2),
            "assumptions": assumptions, "note": note}


# ══ عائلةُ التدفّقات المخصومة ══════════════════════════════════════════════
def _fcff_value(bs: Base, shares, years, g1, r, tv_mult=None):
    """قيمةُ السهم من تدفّقٍ حرٍّ للمنشأة: نموٌّ يتلاشى خطّياً إلى النهائيّ."""
    if bs.fcf_margin_n is None or bs.fcf_margin_n <= 0:
        return None
    rev, pv = bs.rev, 0.0
    for t in range(1, years + 1):
        gt = g1 + (TERMINAL_G - g1) * (t - 1) / max(years - 1, 1)
        rev *= 1 + gt
        pv += rev * bs.fcf_margin_n / (1 + r) ** t
    if tv_mult is not None:
        tv = rev * tv_mult
    else:
        if r - TERMINAL_G < 0.02:
            return None
        tv = rev * bs.fcf_margin_n * (1 + TERMINAL_G) / (r - TERMINAL_G)
    ev = pv + tv / (1 + r) ** years
    return (ev - bs.net_debt) / shares


def cashflow_models(i: Inputs, bs: Base) -> list[dict]:
    out = []
    ev_s = i.peers.get("ev_sales") or []
    for years in (5, 10):
        v = _fcff_value(bs, i.shares, years, bs.growth, bs.wacc)
        lo = _fcff_value(bs, i.shares, years, max(bs.growth - 0.01, 0), bs.wacc + 0.005)
        hi = _fcff_value(bs, i.shares, years, bs.growth + 0.01, bs.wacc - 0.005)
        out.append(_model(f"dcf_gordon_{years}", "cashflow", f"تدفّقٌ حرٌّ مخصوم {years} سنوات · نموٌّ نهائيّ",
                          v, lo, hi,
                          [("كلفةُ رأس المال", f"{bs.wacc*100:.2f}%", f"{(bs.wacc-0.005)*100:.2f}–{(bs.wacc+0.005)*100:.2f}%"),
                           ("هامشُ التدفّق الحرّ المطبَّع", f"{(bs.fcf_margin_n or 0)*100:.1f}%", "متوسّطُ ثلاث سنوات"),
                           ("نموُّ الإيراد الابتدائيّ", f"{bs.growth*100:.1f}%", "يتلاشى إلى النهائيّ"),
                           ("النموُّ النهائيّ", f"{TERMINAL_G*100:.1f}%", "")]))
        if len(ev_s) >= MIN_PEERS:
            m, q1, q3 = statistics.median(ev_s), _pct(ev_s, .25), _pct(ev_s, .75)
            v = _fcff_value(bs, i.shares, years, bs.growth, bs.wacc, tv_mult=m)
            lo = _fcff_value(bs, i.shares, years, bs.growth, bs.wacc + 0.005, tv_mult=q1)
            hi = _fcff_value(bs, i.shares, years, bs.growth, bs.wacc - 0.005, tv_mult=q3)
            out.append(_model(f"dcf_exit_{years}", "cashflow", f"تدفّقٌ حرٌّ مخصوم {years} سنوات · مضاعفُ خروج",
                              v, lo, hi,
                              [("كلفةُ رأس المال", f"{bs.wacc*100:.2f}%", "±0.5%"),
                               ("مضاعفُ خروج EV/الإيراد", f"{m:.2f}x", f"{q1:.2f}–{q3:.2f}x · أقرانٌ سعوديون"),
                               ("نموُّ الإيراد الابتدائيّ", f"{bs.growth*100:.1f}%", "")]))
    # قيمةُ قوّة الأرباح: ربحُ التشغيل المطبَّع بعد الضريبة ÷ كلفة رأس المال، بلا نموّ
    if bs.ebit_n and bs.ebit_n > 0:
        f = lambda r: (bs.ebit_n * (1 - bs.tax) / r - bs.net_debt) / i.shares
        out.append(_model("epv", "cashflow", "قيمةُ قوّة الأرباح (EPV)", f(bs.wacc),
                          f(bs.wacc + 0.01), f(max(bs.wacc - 0.01, RISK_FREE + 0.01)),
                          [("ربحُ التشغيل المطبَّع", f"{bs.ebit_n/1e6:,.0f} مليون", "هامشُ ثلاث سنوات × إيرادِ 12 شهراً"),
                           ("كلفةُ رأس المال", f"{bs.wacc*100:.2f}%", "±1%"),
                           ("صافي الدين", f"{bs.net_debt/1e6:,.0f} مليون", "شاملٌ التزاماتِ الإيجار")]))
    return [m for m in out if m]


# ══ عائلةُ الأرباح والحقوق والتوزيعات ═════════════════════════════════════
def equity_models(i: Inputs, bs: Base) -> list[dict]:
    out = []
    ke = bs.ke
    # الدخلُ المتبقّي: الدفتريةُ + فائضُ العائد يتلاشى إلى كلفة الحقوق في عشر سنوات
    if bs.bvps and bs.roe_n is not None:
        def ri(k, roe0):
            bv, v = bs.bvps, bs.bvps
            payout = min(max((i.dps_ttm or 0) / (bs.ni_n / i.shares), 0), 1) if (bs.ni_n and bs.ni_n > 0) else 0
            for t in range(1, 11):
                roe = roe0 + (k - roe0) * t / 10
                v += (roe - k) * bv / (1 + k) ** t
                bv *= 1 + roe * (1 - payout)
            return v
        out.append(_model("residual_income", "equity", "الدخلُ المتبقّي (عشر سنوات · عائدٌ يتلاشى)",
                          ri(ke, bs.roe_n), ri(ke + 0.005, bs.roe_n - 0.01), ri(ke - 0.005, bs.roe_n + 0.01),
                          [("العائدُ على الحقوق المطبَّع", f"{bs.roe_n*100:.1f}%", "متوسّطُ ثلاث سنوات"),
                           ("كلفةُ حقوق الملكية", f"{ke*100:.2f}%", "±0.5%"),
                           ("الدفتريةُ للسهم", f"{bs.bvps:.2f}", "أحدثُ ميزانية")]))
    # التوزيعات: نموٌّ مستقرّ ومرحلتان — من جدول توزيعات «تداول» الرسميّ
    d0 = i.dps_ttm
    if d0 and d0 > 0:
        g_s = min(max((bs.roe_n or 0) * (1 - min(d0 / (bs.ni_n / i.shares), 1)) if (bs.ni_n and bs.ni_n > 0) else 0, 0),
                  MAX_SUSTAINABLE_GROWTH)
        f1 = lambda k, g: d0 * (1 + g) / (k - g) if k - g > 0.02 else None
        out.append(_model("ddm_stable", "income", "خصمُ التوزيعات · نموٌّ مستقرّ", f1(ke, g_s),
                          f1(ke + 0.005, max(g_s - 0.0025, 0)), f1(ke - 0.005, g_s + 0.0025),
                          [("توزيعاتُ 12 شهراً", f"{d0:.2f}", "جدولُ توزيعات «تداول»"),
                           ("النموُّ المستدام", f"{g_s*100:.2f}%", "العائدُ × نسبةِ الاحتجاز"),
                           ("كلفةُ حقوق الملكية", f"{ke*100:.2f}%", "±0.5%")]))

        def f2(k, g_hi):
            v, d = 0.0, d0
            for t in range(1, 6):
                d *= 1 + g_hi
                v += d / (1 + k) ** t
            return v + (d * (1 + g_s) / (k - g_s)) / (1 + k) ** 5 if k - g_s > 0.02 else None
        gh = min(bs.growth, 0.10)
        out.append(_model("ddm_two_stage", "income", "خصمُ التوزيعات · مرحلتان", f2(ke, gh),
                          f2(ke + 0.005, max(gh - 0.01, 0)), f2(ke - 0.005, gh + 0.01),
                          [("نموُّ خمس سنوات", f"{gh*100:.1f}%", "نموُّ الإيراد المقيَّد"),
                           ("النموُّ المستدام بعدها", f"{g_s*100:.2f}%", ""),
                           ("كلفةُ حقوق الملكية", f"{ke*100:.2f}%", "±0.5%")]))
    return [m for m in out if m]


# ══ عائلةُ مضاعفات الأقران السعوديين ══════════════════════════════════════
def multiple_models(i: Inputs, bs: Base) -> list[dict]:
    out = []
    sh = i.shares
    per_share = {
        "pe": (bs.ni_n / sh if bs.ni_n else None, "مكرّرُ الربحية", "ربحيةُ السهم المطبَّعة"),
        "pb": (bs.bvps, "مضاعفُ الدفترية", "الدفتريةُ للسهم"),
        "ps": (bs.rev / sh, "مضاعفُ المبيعات", "مبيعاتُ السهم"),
        "pocf": (bs.ocf / sh if bs.ocf else None, "مضاعفُ التدفّق التشغيليّ", "تدفّقٌ تشغيليٌّ للسهم"),
    }
    for key, (base, name, label) in per_share.items():
        xs = i.peers.get(key) or []
        if not base or base <= 0 or len(xs) < MIN_PEERS:
            continue
        m, q1, q3 = statistics.median(xs), _pct(xs, .25), _pct(xs, .75)
        out.append(_model(f"peer_{key}", "multiples", name, base * m, base * q1, base * q3,
                          [(label, f"{base:.2f}", ""), ("وسيطُ الأقران", f"{m:.2f}x", f"{q1:.2f}–{q3:.2f}x · {len(xs)} أقران")]))
    for key, base, name, label in (("ev_ebit", bs.ebit_n, "مضاعفُ قيمة المنشأة/الربح التشغيليّ", "الربحُ التشغيليّ المطبَّع"),
                                   ("ev_sales", bs.rev, "مضاعفُ قيمة المنشأة/الإيراد", "إيرادُ 12 شهراً")):
        xs = i.peers.get(key) or []
        if not base or base <= 0 or len(xs) < MIN_PEERS:
            continue
        m, q1, q3 = statistics.median(xs), _pct(xs, .25), _pct(xs, .75)
        f = lambda mult: (base * mult - bs.net_debt) / sh
        out.append(_model(f"peer_{key}", "multiples", name, f(m), f(q1), f(q3),
                          [(label, f"{base/1e6:,.0f} مليون", ""),
                           ("وسيطُ الأقران", f"{m:.2f}x", f"{q1:.2f}–{q3:.2f}x · {len(xs)} أقران"),
                           ("صافي الدين", f"{bs.net_debt/1e6:,.0f} مليون", "")]))
    return [m for m in out if m]


# ══ التجميع: وسيطُ كلّ عائلةٍ ثمّ أوزانُ النمط ═══════════════════════════════
def aggregate(models: list[dict], price: float, archetype: str | None) -> dict:
    kind = "financial" if archetype in FIN_TYPES else "reit" if archetype == "reit" else "default"
    weights = dict(FAMILY_WEIGHTS[kind])
    # ما شذّ عن **عائلته** يُستبعَد ويُسمّى — لا عن وسيط النماذج كلِّها: العائلاتُ
    # تختلف بطبيعتها (مضاعفاتُ سوقٍ مرتفعةٌ مقابل خصمٍ متحفّظ)، وقِيس أنّ المقارنةَ
    # بالكلّ تُسقط عائلةَ الحقوق بأكملها. والشاذُّ داخلَ العائلة افتراضٌ معطوب.
    excluded = []
    by_fam: dict[str, list[dict]] = {}
    for m in models:
        by_fam.setdefault(m["family"], []).append(m)
    keep = []
    for fam, ms in by_fam.items():
        if len(ms) < 3:
            keep += ms
            continue
        med = statistics.median([m["value"] for m in ms])
        for m in ms:
            if m["value"] > med * 2.5 or m["value"] < med / 2.5:
                excluded.append({**m, "excluded": f"يبعد عن وسيط عائلته ({med:.2f}) أكثرَ من ضعفين ونصف"})
            else:
                keep.append(m)
    models = keep
    fams: dict[str, list[dict]] = {}
    for m in models:
        fam = "equity" if m["family"] == "income" and kind == "default" else m["family"]
        fams.setdefault(fam, []).append(m)
    summary, tot_w, acc, lo_acc, hi_acc = [], 0.0, 0.0, 0.0, 0.0
    for fam, ms in fams.items():
        w = weights.get(fam, 0.0)
        if w <= 0:
            continue
        v = statistics.median([m["value"] for m in ms])
        lo = statistics.median([m["low"] for m in ms])
        hi = statistics.median([m["high"] for m in ms])
        summary.append({"family": fam, "name": FAMILY_NAMES.get(fam, fam), "value": round(v, 2),
                        "low": round(lo, 2), "high": round(hi, 2), "weight": w, "models": len(ms)})
        tot_w += w; acc += w * v; lo_acc += w * lo; hi_acc += w * hi
    if tot_w <= 0:
        return {"value": None, "families": [], "excluded": excluded}
    value = acc / tot_w
    low, high = lo_acc / tot_w, hi_acc / tot_w
    all_v = [m["value"] for m in models]
    disp = ((_pct(all_v, .75) - _pct(all_v, .25)) / value) if len(all_v) >= 4 and value else None
    uncertainty = ("منخفض" if disp is not None and disp < 0.25 else
                   "معتدل" if disp is not None and disp < 0.5 else "مرتفع")
    if len(fams) < 2:
        uncertainty = "مرتفع"
    return {"value": round(value, 2), "low": round(min(low, value), 2), "high": round(max(high, value), 2),
            "upside": round((value / price - 1) * 100, 2) if price else None,
            "uncertainty": uncertainty, "dispersion": round(disp, 3) if disp is not None else None,
            "families": summary, "excluded": excluded, "weights_kind": kind}


def value(i: Inputs) -> dict:
    bs = base_of(i)
    if not bs:
        return {"value": None, "reason": "لا إيرادَ أو لا عددَ أسهمٍ موثوق في الإفصاح"}
    fin = i.archetype in FIN_TYPES
    models = ([] if fin or i.archetype == "reit" else cashflow_models(i, bs)) \
        + equity_models(i, bs) + multiple_models(i, bs)
    agg = aggregate(models, i.price, i.archetype)
    return {**agg, "price": i.price, "models": models, "count": len(models),
            "notes": bs.notes + i.notes, "peers": i.peer_symbols, "sector": i.sector,
            "ttm_source": i.ttm_source,
            "rates": {"ke": round(bs.ke, 4), "wacc": round(bs.wacc, 4), "tax": round(bs.tax, 3)}}


# ══ جمعُ المدخلات من المصادر الرسمية ══════════════════════════════════════
def _shares_of(annual: list[dict], quarterly: list[dict]) -> float | None:
    """عددُ الأسهم من صافي الربح ÷ ربحية السهم (يُحصّن من خطأ الوحدة: الآلاف)."""
    cands = []
    for p in (quarterly[-4:] + annual[-2:])[::-1]:
        ni, eps = _n(p.get("net_income")), _n(p.get("eps"))
        if ni and eps and abs(eps) > 1e-6:
            cands.append(abs(ni / eps))
    if not cands:
        return None
    ref = statistics.median(cands)
    for p in quarterly[::-1]:
        s = _n(p.get("shares_outstanding"))
        if s and ref / 1.5 <= s <= ref * 1.5:
            return s
    return ref


def _ttm_of(quarterly: list[dict], annual: list[dict]) -> tuple[dict, str]:
    q = quarterly[-4:]
    keys = ("revenue", "net_income", "ebit", "operating_cash_flow", "capex", "interest_expense", "pretax_income")
    if len(q) == 4 and all(_n(p.get("revenue")) for p in q):
        from datetime import date
        d = [date.fromisoformat(str(p["as_of"])[:10]) for p in q]
        if (d[-1] - d[0]).days <= 300:
            return ({k: sum(_n(p.get(k)) or 0 for p in q) for k in keys},
                    f"أربعةُ أرباعٍ حتى {q[-1]['as_of']}")
    a = annual[-1] if annual else {}
    return ({k: _n(a.get(k)) for k in keys}, f"سنةُ {a.get('year')}")


def _peer_multiples(sym: str, peers: list[str], rows: dict) -> dict:
    from app.services.tadawul_xbrl import for_symbol as X
    out: dict[str, list[float]] = {k: [] for k in ("pe", "pb", "ps", "pocf", "ev_ebit", "ev_sales")}
    for s in peers:
        px = _n((rows.get(s) or rows.get(s + ".SR") or {}).get("price"))
        if not px:
            continue
        try:
            an, qu = X(s, "annual") or [], X(s, "quarterly") or []
        except Exception:                                          # noqa: BLE001
            continue
        if not an:
            continue
        sh = _shares_of(an, qu)
        if not sh:
            continue
        ttm, _ = _ttm_of(qu, an)
        bal = (qu or an)[-1]
        mcap = px * sh
        ev = mcap + (_n(bal.get("total_debt")) or 0) - (_n(bal.get("ending_cash")) or 0)
        eq, rev, ni = _n(bal.get("equity")), _n(ttm.get("revenue")), _n(ttm.get("net_income"))
        ebit, ocf = _n(ttm.get("ebit")), _n(ttm.get("operating_cash_flow"))
        for k, v, lo, hi in (("pe", mcap / ni if ni and ni > 0 else None, 0, 60),
                             ("pb", mcap / eq if eq and eq > 0 else None, 0, 15),
                             ("ps", mcap / rev if rev and rev > 0 else None, 0, 20),
                             ("pocf", mcap / ocf if ocf and ocf > 0 else None, 0, 60),
                             ("ev_ebit", ev / ebit if ebit and ebit > 0 else None, 0, 60),
                             ("ev_sales", ev / rev if rev and rev > 0 else None, 0, 20)):
            if v is not None and lo < v <= hi:
                out[k].append(round(v, 3))
    return out


async def gather(symbol: str) -> Inputs | None:
    from app.services import tadawul_market as TM
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services.statement_merge import archetype_of
    sym = str(symbol).replace(".SR", "").strip()
    rows = TM.usable_rows()[0] or {}
    if not rows:
        try:
            await TM.refresh()
        except Exception:                                          # noqa: BLE001
            pass
        rows = TM.usable_rows()[0] or {}
    me = rows.get(sym) or rows.get(sym + ".SR") or {}
    price = _n(me.get("price"))
    annual, quarterly = X(sym, "annual") or [], X(sym, "quarterly") or []
    if not price or not annual:
        return None
    shares = _shares_of(annual, quarterly)
    if not shares:
        return None
    ttm, src = _ttm_of(quarterly, annual)
    sector = me.get("sector_en")
    try:
        from app.data.universe import is_main
    except Exception:                                              # noqa: BLE001
        is_main = lambda s: True                                   # noqa: E731
    peers = sorted(str(s).replace(".SR", "") for s, r in rows.items()
                   if (r or {}).get("sector_en") == sector and str(s).replace(".SR", "") != sym
                   and is_main(str(s).replace(".SR", "")))
    from app.services import cache
    ck = f"fvm:peers:{sector}"
    pm = cache.get(ck)
    if pm is None:
        pm = _peer_multiples(sym, peers, rows)
        cache.set(ck, pm, 6 * 60 * 60)
    dps = None
    try:
        from app.services.tadawul_dividends import read as _div
        from datetime import date, timedelta
        d = await _div(sym) or {}
        cut = (date.today() - timedelta(days=365)).isoformat()
        amt = [h["amount"] for h in (d.get("history") or []) if str(h.get("date")) >= cut]
        dps = sum(amt) if amt else None
    except Exception as e:                                         # noqa: BLE001
        logger.debug("توزيعات {}: {}", sym, e)
    beta = None
    try:
        from app.services.sector_betas import beta_for
        bt = beta_for(sector) if sector else None
        beta = bt[0] if bt else None
    except Exception:                                              # noqa: BLE001
        pass
    return Inputs(symbol=sym, price=price, shares=shares, annual=annual, ttm=ttm,
                  balance=(quarterly or annual)[-1], ttm_source=src, archetype=archetype_of(sym),
                  sector=sector, beta=beta, dps_ttm=dps, peers=pm, peer_symbols=peers)


async def for_symbol(symbol: str) -> dict | None:
    from app.services import cache
    ck = f"fvm:v1:{symbol}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    try:
        i = await gather(symbol)
        res = value(i) if i else None
    except Exception as e:                                         # noqa: BLE001
        logger.warning("المحرّكُ المتعدّد لـ{}: {}", symbol, e)
        res = None
    cache.set(ck, res or {}, 6 * 60 * 60 if res else 30 * 60)
    return res
