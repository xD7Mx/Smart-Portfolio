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

# ══ أوزانُ العائلات بالقياس لا بالتخمين ══ (fvm_measure.py على 140 ورقةً لها هدفُ محللين)
# الوزنُ عكسُ وسيط خطأ العائلة لكلّ نمط، مقرَّباً. والمصرفُ لا تدفّقَ حرّاً له.
FAMILY_WEIGHTS_BY_ARCH = {
    "bank": {"equity": 0.64, "multiples": 0.36},
    "financial": {"equity": 0.56, "multiples": 0.44},
    "insurance": {"equity": 0.24, "multiples": 0.76},
    "reit": {"income": 0.55, "multiples": 0.45},
    "asset_light": {"cashflow": 0.45, "equity": 0.21, "multiples": 0.34},
    "capital_infra": {"cashflow": 0.34, "equity": 0.31, "multiples": 0.35},
    "commodity": {"cashflow": 0.46, "equity": 0.21, "multiples": 0.33},
    "consumer_cyclical": {"cashflow": 0.34, "equity": 0.23, "multiples": 0.43},
    "consumer_defensive": {"cashflow": 0.31, "equity": 0.22, "multiples": 0.47},
    "contracting": {"cashflow": 0.42, "equity": 0.17, "multiples": 0.41},
    "re_developer": {"cashflow": 0.63, "equity": 0.18, "multiples": 0.19},
}
FAMILY_WEIGHTS = {"default": {"cashflow": 0.38, "equity": 0.22, "multiples": 0.40},
                  "financial": FAMILY_WEIGHTS_BY_ARCH["financial"], "reit": FAMILY_WEIGHTS_BY_ARCH["reit"]}

# ══ المزيجُ مع المحرّك المُعايَر ══ (قِيس: الجديدُ وحده 37٪ والقائمُ 39٪ والمزيجُ 31٪)
# حصّةُ النماذج الجديدة لكلّ نمط — أفضلُ α في القياس، والباقي للمحرّك القائم
# المعايَر على السوق السعوديّ شهوراً (وهو الأدقّ في المصارف والبنية التحتية).
# أُعيد اشتقاقُها بعد مجموعات القطاعات المقيسة (D473): الجديدُ وحده 24٪ والقائمُ 35٪.
BLEND_ALPHA = {"bank": 0.75, "financial": 0.25, "capital_infra": 0.25,
               "insurance": 1.0, "consumer_cyclical": 0.75, "commodity": 1.0, "re_developer": 1.0,
               "consumer_defensive": 0.75, "contracting": 0.75, "asset_light": 1.0}
DEFAULT_ALPHA = 0.75

# ══ نظريةُ المالك: «كلُّ قطاعٍ بما يليق به» ══ (D470)
# النماذجُ لا تُطبَّق كلُّها على الجميع: الصندوقُ العقاريُّ يُقيَّم بتوزيعه وصافي
# أصوله (و«InvestingPro» نفسُه يعرض له أربعةَ نماذج لا خمسةَ عشر)، والمصرفُ
# بعائد حقوقه، والدوريُّ بهوامشَ مطبَّعةٍ لا بربحِ سنةٍ واحدة، والبرمجياتُ لا
# تُقاس بدفتريةٍ لا تحمل أصولَها. والمفتاحُ مجموعةُ «تداول» الصناعيةُ الرسمية.
_ALL = {"dcf_gordon_5", "dcf_gordon_10", "dcf_exit_5", "dcf_exit_10", "epv", "residual_income",
        "ddm_stable", "ddm_two_stage", "peer_pe", "peer_pb", "peer_ps", "peer_pocf",
        "peer_ev_ebit", "peer_ev_sales", "peer_yield"}
_DCF = {"dcf_gordon_5", "dcf_gordon_10", "dcf_exit_5", "dcf_exit_10"}
_DDM = {"ddm_stable", "ddm_two_stage"}
MODEL_SETS = {
    "REITs": ("الصناديق العقارية: التوزيعُ وصافي الأصول", _DDM | {"peer_yield", "peer_pb", "peer_ps"}),
    "Banks": ("المصارف: عائدُ الحقوق والتوزيع", {"residual_income", "peer_pe", "peer_pb"} | _DDM),
    "Insurance": ("التأمين: الحقوقُ وعائدُها", {"residual_income", "peer_pb", "peer_pe"}),
    "Financial Services": ("الخدمات المالية: الحقوقُ والأرباح", {"residual_income", "peer_pe", "peer_pb"} | _DDM),
    "Real Estate Mgmt & Dev't": ("التطوير العقاري: الأصولُ والتدفّقُ الطويل",
                                 {"peer_pb", "residual_income", "dcf_gordon_10", "dcf_exit_10", "peer_pe"}),
    "Energy": ("الطاقة: هوامشُ مطبَّعةٌ عبر الدورة", _DCF | {"epv", "peer_ev_ebit", "peer_ev_sales", "peer_pb", "residual_income", "peer_pe"} | _DDM),
    "Materials": ("المواد الأساسية: هوامشُ مطبَّعةٌ عبر الدورة", _DCF | {"epv", "peer_ev_ebit", "peer_ev_sales", "peer_pb", "residual_income"}),
    "Utilities": ("المرافق: تدفّقٌ منتظمٌ وتوزيع", _DCF | _DDM | {"peer_ev_ebit", "peer_pe", "peer_pb", "residual_income"}),
    "Telecommunication Services": ("الاتصالات: تدفّقٌ منتظمٌ وتوزيع", _DCF | _DDM | {"peer_ev_ebit", "peer_ev_sales", "peer_pe", "epv"}),
    "Software & Services": ("البرمجيات: الأرباحُ والمبيعات لا الدفترية", _DCF | {"epv", "peer_pe", "peer_ev_ebit", "peer_ps", "peer_pocf", "peer_ev_sales"}),
    "Health Care Equipment & Svc": ("الرعاية الصحية: الأرباحُ والتدفّق", _DCF | {"epv", "peer_pe", "peer_ev_ebit", "peer_ps", "peer_pocf"}),
    "Pharma, Biotech & Life Science": ("الأدوية: الأرباحُ والتدفّق", _DCF | {"epv", "peer_pe", "peer_ev_ebit", "peer_ps", "peer_pocf"}),
}
_FULL = _ALL - {"peer_yield"}
MODEL_SETS.update({
    "Capital Goods": ("السلع الرأسمالية: التدفّقُ والربحُ التشغيليّ والأصول",
                      _DCF | {"epv", "peer_ev_ebit", "peer_pe", "peer_pb", "peer_pocf", "residual_income"}),
    "Commercial & Professional": ("الخدمات التجارية والمهنية: أصولٌ خفيفة — الأرباحُ والتدفّق",
                                  _DCF | {"epv", "peer_pe", "peer_ev_ebit", "peer_pocf", "peer_ps"}),
    "Transportation": ("النقل: كثيفُ الأصول — مضاعفاتُ المنشأة والتدفّق",
                       _DCF | {"peer_ev_ebit", "peer_ev_sales", "peer_pb", "peer_pe", "residual_income"}),
    "Consumer Durables": ("السلع المعمّرة والملابس: النموذجُ الكامل", _FULL),
    "Consumer Services": ("الخدمات الاستهلاكية: الأرباحُ والتدفّق", _DCF | {"epv", "peer_ev_ebit", "peer_pe", "peer_ps", "peer_pocf"}),
    "Media": ("الإعلام والترفيه: الأرباحُ والمبيعات", _DCF | {"peer_ev_ebit", "peer_pe", "peer_ps", "peer_pocf"}),
    "Consumer Discretionary": ("تجزئة السلع الكمالية: النموذجُ الكامل", _FULL),
    "Consumer Staples": ("تجزئة السلع الأساسية: النموذجُ الكامل وعائدُ التوزيع", _ALL),
    "Food & Beverages": ("الأغذية والمشروبات: دفاعيٌّ — كاملٌ مع التوزيع", _ALL),
    "Household & Personal": ("المنتجات المنزلية والشخصية: كاملٌ مع التوزيع", _ALL),
    "Technology Hardware": ("أجهزة التقنية: الأرباحُ والمبيعات", _DCF | {"peer_pe", "peer_ev_ebit", "peer_ps"}),
})
for _k in ("Banks", "Utilities", "Telecommunication Services", "Energy"):
    MODEL_SETS[_k] = (MODEL_SETS[_k][0], MODEL_SETS[_k][1] | {"peer_yield"})

# ══ مجموعاتٌ اعتُمدت بالقياس خارج العيّنة (D473 · fvm_sector_fit.py) ══
# لا تُستبدل مجموعةٌ إلا إن فازت على أوراقٍ لم تُختر بها (ترك واحد) بفارقٍ
# لا يقلّ عن نقطتين، وبعيّنةٍ ≥ 5، وبثلاثة نماذج على الأقلّ ضمن حدود النظرية.
MODEL_SETS.update({
    "Capital Goods": ("السلع الرأسمالية: التدفّقُ بمضاعف الخروج وقيمةُ المنشأة إلى المبيعات",
                      {"dcf_exit_5", "dcf_exit_10", "peer_ev_sales"}),
    "Consumer Services": ("الخدمات الاستهلاكية: التدفّقُ بمضاعف الخروج والتدفّقُ التشغيليّ للأقران",
                          {"dcf_exit_5", "dcf_exit_10", "peer_pocf"}),
    "Food & Beverages": ("الأغذية والمشروبات: التدفّقُ والقوّةُ الإيرادية والتوزيع",
                         {"dcf_exit_5", "dcf_exit_10", "epv", "ddm_two_stage"}),
    "Insurance": ("التأمين: التوزيعُ والأقساطُ المكتتبة", _DDM | {"peer_ps"}),
    "Banks": ("المصارف: التوزيعُ المرحليّ ومكرّرُ الربح وعائدُ الأقران", {"ddm_two_stage", "peer_pe", "peer_yield"}),
    "Energy": ("الطاقة: التدفّقُ الطويل والمبيعاتُ والأصول", {"dcf_gordon_10", "peer_ev_sales", "peer_pb"}),
})

ARCH_SETS = {"bank": MODEL_SETS["Banks"], "insurance": MODEL_SETS["Insurance"],
             "financial": MODEL_SETS["Financial Services"], "reit": MODEL_SETS["REITs"]}


def model_set(sector: str | None, archetype: str | None) -> tuple[str, set]:
    """المجموعةُ بالاسم الرسميّ (ومطابقةِ البادئة: «تداول» تختصر بعضَ الأسماء)،
    ثمّ بالنمط، ثمّ الكاملُ لقطاعٍ جديدٍ لم يُعرَف — ولا تُظلَم ورقةٌ لغياب اسمها."""
    sec = (sector or "").strip()
    if sec in MODEL_SETS:
        return MODEL_SETS[sec]
    for k, v in MODEL_SETS.items():
        if sec and (sec.startswith(k) or k.startswith(sec)):
            return v
    return ARCH_SETS.get(archetype or "") or ("النموذجُ الكامل (قطاعٌ لم يُصنَّف بعد)", _ALL)


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
    stale_days: int | None = None            # عمرُ أحدث قوائم منشورة بالأيام


STALE_WARN, STALE_STOP = 274, 456            # تسعةُ أشهرٍ للتحذير وخمسةَ عشرَ للامتناع
MIN_MODELS = 3                               # أدنى عددٍ من النماذج الصالحة لنشر قيمة
SIM_FLOOR = 0.5                              # حصّةُ القرين الثابتة؛ والباقي بتشابهه (fvm_sim_floor.py)
FIN_BAN = {"dcf_gordon_5", "dcf_gordon_10", "dcf_exit_5", "dcf_exit_10", "epv",
           "peer_ev_ebit", "peer_ev_sales", "peer_pocf"}   # المصرفُ والتأمينُ لا تدفّقَ حرٌّ ولا قيمةَ منشأة


def _n(x) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _wq(xs: list, q: float) -> float:
    """كمّيةٌ مرجَّحة: القيمُ أزواجُ (قيمة، وزن) أو أرقامٌ بوزنٍ واحد."""
    pts = sorted((x if isinstance(x, tuple) else (x, 1.0)) for x in xs)
    tot = sum(w for _, w in pts) or 1.0
    acc = 0.0
    for v, w in pts:
        acc += w
        if acc / tot >= q:
            return v
    return pts[-1][0]


def _vals(xs: list) -> list[float]:
    return [x[0] if isinstance(x, tuple) else x for x in xs]


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
        # الوسيطُ لا المتوسّط: سنةٌ استثنائيةٌ واحدة (ربحُ توزيعِ حصّةٍ أو بيعِ أصل) لا
        # تُعمَّم على الأبد — قِيس: صافولا 2024 رفع المتوسّطَ إلى 17٪ والوسيطُ 4٪ (D474).
        return statistics.median(ms) if ms else None

    m_ni, m_ebit = margin("net_income"), margin("ebit")
    fcfs = [(_n(p.get("operating_cash_flow")) or 0) - (_n(p.get("capex")) or 0) for p in a
            if _n(p.get("operating_cash_flow")) is not None]
    m_fcf = (statistics.median([f / p["revenue"] for f, p in zip(fcfs, a) if _n(p.get("revenue"))])
             if fcfs else None)
    ttm_m = (_n(i.ttm.get("net_income")) or 0) / rev
    if m_ni is not None and abs(ttm_m - m_ni) > max(0.02, abs(m_ni) * 0.5):
        notes.append(f"هامشُ صافي الربح لاثني عشر شهراً {ttm_m*100:.1f}٪ يبعد عن متوسّط ثلاث "
                     f"سنوات {m_ni*100:.1f}٪ — طُبِّع على الوسيط كي لا تُسعَّر سنةٌ استثنائيةٌ أبدياً")
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
    roe_n = statistics.median(rois) if rois else None
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
            m, q1, q3 = _wq(ev_s, .5), _wq(ev_s, .25), _wq(ev_s, .75)
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
        # ══ فائضُ العائد لا يتلاشى إلى الصفر ══ (قِيس: وسيطُ النسبة إلى هدف المحللين 0.41)
        # تلاشيه الكاملُ في عشر سنوات بلا قيمةٍ نهائية يجعل كلَّ شركةٍ «دفتريةً
        # وقليلاً»، وذلك ينفي كلَّ ميزةٍ تنافسية. فيتلاشى إلى ثلثه ويبقى أبدياً
        # بنموٍّ نهائيّ — وهو نهجُ الدخل المتبقّي بقيمةٍ نهائية المعتاد.
        def ri(k, roe0):
            bv, v = bs.bvps, bs.bvps
            payout = min(max((i.dps_ttm or 0) / (bs.ni_n / i.shares), 0), 1) if (bs.ni_n and bs.ni_n > 0) else 0
            roe_inf = k + (roe0 - k) / 3
            roe = roe0
            for t in range(1, 11):
                roe = roe0 + (roe_inf - roe0) * t / 10
                v += (roe - k) * bv / (1 + k) ** t
                bv *= 1 + roe * (1 - payout)
            if k - TERMINAL_G > 0.02:
                v += (roe - k) * bv / (k - TERMINAL_G) / (1 + k) ** 10
            return v
        out.append(_model("residual_income", "equity", "الدخلُ المتبقّي (فائضٌ يتلاشى إلى ثلثه · قيمةٌ نهائية)",
                          ri(ke, bs.roe_n), ri(ke + 0.005, bs.roe_n - 0.01), ri(ke - 0.005, bs.roe_n + 0.01),
                          [("العائدُ على الحقوق المطبَّع", f"{bs.roe_n*100:.1f}%", "متوسّطُ ثلاث سنوات"),
                           ("كلفةُ حقوق الملكية", f"{ke*100:.2f}%", "±0.5%"),
                           ("الدفتريةُ للسهم", f"{bs.bvps:.2f}", "أحدثُ ميزانية")]))
    # التوزيعات: نموٌّ مستقرّ ومرحلتان — من جدول توزيعات «تداول» الرسميّ
    d0 = i.dps_ttm
    # ══ خصمُ التوزيعات لمن يوزّع فعلاً ══ (قِيس: وسيطُ النسبة 0.47 على الكلّ)
    # من يحتجز أغلبَ ربحه لا تقيس توزيعاتُه قيمتَه — قيمتُه فيما احتجز.
    payout0 = (d0 / (bs.ni_n / i.shares)) if (d0 and bs.ni_n and bs.ni_n > 0) else None
    if d0 and d0 > 0 and payout0 is not None and payout0 >= 0.45:
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
        m, q1, q3 = _wq(xs, .5), _wq(xs, .25), _wq(xs, .75)
        out.append(_model(f"peer_{key}", "multiples", name, base * m, base * q1, base * q3,
                          [(label, f"{base:.2f}", ""), ("وسيطُ الأقران", f"{m:.2f}x", f"{q1:.2f}–{q3:.2f}x · {len(xs)} أقران")]))
    ys = i.peers.get("yield") or []
    if i.dps_ttm and i.dps_ttm > 0 and len(ys) >= MIN_PEERS:
        m, q1, q3 = _wq(ys, .5), _wq(ys, .25), _wq(ys, .75)
        out.append(_model("peer_yield", "multiples", "عائدُ التوزيع مقابل الأقران", i.dps_ttm / m,
                          i.dps_ttm / q3, i.dps_ttm / q1,
                          [("توزيعاتُ 12 شهراً", f"{i.dps_ttm:.2f}", "جدولُ توزيعات «تداول»"),
                           ("وسيطُ عائد الأقران", f"{m*100:.2f}%", f"{q1*100:.2f}–{q3*100:.2f}% · {len(ys)} أقران")]))
    for key, base, name, label in (("ev_ebit", bs.ebit_n, "مضاعفُ قيمة المنشأة/الربح التشغيليّ", "الربحُ التشغيليّ المطبَّع"),
                                   ("ev_sales", bs.rev, "مضاعفُ قيمة المنشأة/الإيراد", "إيرادُ 12 شهراً")):
        xs = i.peers.get(key) or []
        if not base or base <= 0 or len(xs) < MIN_PEERS:
            continue
        m, q1, q3 = _wq(xs, .5), _wq(xs, .25), _wq(xs, .75)
        f = lambda mult: (base * mult - bs.net_debt) / sh
        out.append(_model(f"peer_{key}", "multiples", name, f(m), f(q1), f(q3),
                          [(label, f"{base/1e6:,.0f} مليون", ""),
                           ("وسيطُ الأقران", f"{m:.2f}x", f"{q1:.2f}–{q3:.2f}x · {len(xs)} أقران"),
                           ("صافي الدين", f"{bs.net_debt/1e6:,.0f} مليون", "")]))
    return [m for m in out if m]


# ══ التجميع: وسيطُ كلّ عائلةٍ ثمّ أوزانُ النمط ═══════════════════════════════
def aggregate(models: list[dict], price: float, archetype: str | None) -> dict:
    kind = "financial" if archetype in FIN_TYPES else "reit" if archetype == "reit" else "default"
    weights = dict(FAMILY_WEIGHTS_BY_ARCH.get(archetype or "", FAMILY_WEIGHTS[kind]))
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
        # التوزيعُ عائلةٌ مستقلّةٌ للريت وحده؛ وفي غيره يُضمّ إلى الحقوق — وإلا
        # عُرض نموذجُه ووزنُه صفرٌ في المصارف والتأمين (D473).
        fam = "equity" if m["family"] == "income" and kind != "reit" else m["family"]
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
    # ══ قوائمُ قديمة لا تُقيَّم بها ورقةٌ اليوم (D474) ══ (قِيس: 1320 بقوائم 2021)
    if i.stale_days is not None and i.stale_days > STALE_STOP:
        return {"value": None, "reason": f"أحدثُ قوائم منشورة لدينا ({i.ttm_source}) أقدمُ من خمسة عشر شهراً — "
                                         "لا تُقيَّم ورقةٌ اليوم بقوائمَ قديمة", "price": i.price}
    set_name, allowed = model_set(i.sector, i.archetype)
    every = cashflow_models(i, bs) + equity_models(i, bs) + multiple_models(i, bs)
    # ══ نموذجٌ بعشرة أضعاف السعر أو عُشره خطأُ مدخلاتٍ لا رأيٌ ══
    # (قِيس: 1321 خرج بخمسة ملياراتٍ للسهم — عددُ أسهمٍ بوحدةٍ مغلوطة)
    sane = lambda m: i.price / 10 <= m["value"] <= i.price * 10    # noqa: E731
    models = [m for m in every if m["key"] in allowed]
    bad = [m for m in models if not sane(m)]
    models = [m for m in models if m not in bad]
    extra_notes = []
    # ══ لا قيمةَ من نموذجٍ أو اثنين (D474) ══ (قِيس: 2070 بنموذجٍ واحد، و8313 بلا نموذج)
    # إن لم تُنتج مجموعةُ القطاع ثلاثةَ نماذجَ صالحة تُستكمل من النموذج الكامل
    # ضمن حدود النظرية، ويُعلَن ذلك.
    if len(models) < MIN_MODELS:
        pool = _ALL - (FIN_BAN if i.archetype in FIN_TYPES else set())
        more = [m for m in every if m["key"] in pool and m["key"] not in allowed and sane(m)]
        if more:
            models = models + more
            extra_notes.append(f"مجموعةُ القطاع أنتجت {len(models) - len(more)} نموذجاً صالحاً فقط — "
                               f"استُكملت بـ{len(more)} من النموذج الكامل")
    agg = aggregate(models, i.price, i.archetype)
    if any(n.startswith(("إدراجٌ حديث", "سجلٌّ قصير")) for n in i.notes) or extra_notes:
        agg["uncertainty"] = "مرتفع"
    if i.stale_days is not None and i.stale_days > STALE_WARN:
        agg["uncertainty"] = "مرتفع"
        extra_notes.append(f"أحدثُ قوائم منشورة ({i.ttm_source}) أقدمُ من تسعة أشهر — الثقةُ أدنى")
    agg["excluded"] = agg.get("excluded", []) + [
        {**m, "excluded": "يبعد عن السعر عشرةَ أضعاف — خطأُ مدخلاتٍ أرجحُ من رأي"} for m in bad]
    return {**agg, "price": i.price, "models": models, "count": len(models),
            "notes": bs.notes + i.notes + extra_notes, "peers": i.peer_symbols, "sector": i.sector, "model_set": set_name,
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


async def _peer_yields(peers: list[str], rows: dict) -> dict[str, float]:
    """عائدُ توزيع الأقران لاثني عشر شهراً من جدول «تداول» الرسميّ."""
    from app.services.tadawul_dividends import read as _div
    from datetime import date, timedelta
    cut = (date.today() - timedelta(days=365)).isoformat()
    out: dict[str, float] = {}
    for s in peers:
        px = _n((rows.get(s) or rows.get(s + ".SR") or {}).get("price"))
        try:
            d = await _div(s) or {}
        except Exception:                                          # noqa: BLE001
            continue
        amt = sum(h["amount"] for h in (d.get("history") or []) if str(h.get("date")) >= cut)
        if px and amt > 0 and 0 < amt / px < 0.25:
            out[s] = round(amt / px, 5)
    return out


def _peer_multiples(sym: str, peers: list[str], rows: dict) -> dict:
    from app.services.tadawul_xbrl import for_symbol as X
    out: dict[str, list] = {k: [] for k in ("pe", "pb", "ps", "pocf", "ev_ebit", "ev_sales")}
    out["_rec"] = {}
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
                out["_rec"].setdefault(s, {"rev": rev, "margin": (ni / rev) if (ni is not None and rev) else None})[k] = round(v, 3)
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
    notes: list[str] = []
    # ══ الإدراجُ الحديثُ لا يُظلَم ══ (بأمر المالك: «محرّكٌ يستوعب الاكتتابات»)
    # شركةٌ أُدرجت قبل أن تُصدر قوائمَ سنوية: تُبنى سنتُها من أحدث أرباعها
    # بدل الامتناع، ويُعلَن قصرُ السجلّ ويرتفع عدمُ اليقين — لا تُسعَّر بسجلٍّ لا تملكه.
    if not annual and len(quarterly) >= 2:
        q = quarterly[-4:]
        k = 4 / len(q)
        syn = {key: sum(_n(x.get(key)) or 0 for x in q) * k
               for key in ("revenue", "net_income", "ebit", "operating_cash_flow", "capex", "interest_expense", "pretax_income")}
        syn.update({key: q[-1].get(key) for key in ("equity", "total_debt", "ending_cash", "total_assets", "shares_outstanding", "as_of")})
        syn["eps"] = (syn["net_income"] / _n(q[-1].get("shares_outstanding"))) if _n(q[-1].get("shares_outstanding")) else None
        syn["year"] = str(q[-1].get("as_of"))[:4]
        annual = [syn]
        notes.append(f"إدراجٌ حديث: لا قوائمَ سنويةً بعد — بُنيت السنةُ من {len(q)} أرباع")
    elif 0 < len(annual) < 3:
        notes.append(f"سجلٌّ قصير: {len(annual)} سنةٌ منشورة فقط — المتوسّطاتُ أقلُّ ثباتاً")
    if not price or not annual:
        return None
    shares = _shares_of(annual, quarterly)
    if not shares:
        return None
    ttm, src = _ttm_of(quarterly, annual)
    stale = None
    try:
        from datetime import date
        last = max(str(x.get("as_of") or f"{x.get('year')}-12-31")[:10] for x in (quarterly[-1:] + annual[-1:]))
        stale = (date.today() - date.fromisoformat(last)).days
    except Exception:                                              # noqa: BLE001
        pass
    sector = me.get("sector_en")
    try:
        from app.data.universe import is_main
    except Exception:                                              # noqa: BLE001
        is_main = lambda s: True                                   # noqa: E731
    # ══ جدولُ القطاع يُبنى لكلّ أعضائه ويُحذف منه صاحبُ الطلب عند كلّ قراءة (D474) ══
    # كان يُبنى باستثناء أوّلِ طالبٍ وحده ثمّ يُخزَّن للقطاع، فوجد كلُّ من بعده
    # نفسَه بين أقرانه — وبوزن التشابه (١ مقابل ٠٫٠٥) صار مضاعفُه هو «الوسيط»
    # فخرجت القيمةُ مساويةً لسعره تماماً (قِيس: 2330 و1201).
    members = sorted(str(s).replace(".SR", "") for s, r in rows.items()
                     if (r or {}).get("sector_en") == sector and is_main(str(s).replace(".SR", "")))
    peers = [p for p in members if p != sym]
    from app.services import cache
    ck = f"fvm:peers:v4:{sector}"
    table = cache.get(ck)
    if table is None:
        table = _peer_multiples(sym, members, rows)
        table["_yield"] = await _peer_yields(members, rows)
        cache.set(ck, table, 6 * 60 * 60)
    pm = {"_rec": {k: v for k, v in (table.get("_rec") or {}).items() if k != sym},
          "yield": [v for k, v in (table.get("_yield") or {}).items() if k != sym]}
    # ══ الأقرانُ بتشابه النشاط لا بالقطاع وحده ══ (بأمر المالك: «قارنتَ العثيم بالأدوية»)
    # «تداول» تضع الصيدلياتِ مع البقالة في مجموعةٍ واحدة (معيار GICS) — وهو
    # تصنيفٌ رسميٌّ لا نخالفه؛ لكنّ هامشَ الصيدلية غيرُ هامش البقالة. فيُوزن
    # كلُّ قرينٍ بقربه في الحجم (الإيراد) والهامش: الأقربُ يحمل الوزنَ الأكبر.
    rev0, ni0 = _n(ttm.get("revenue")), _n(ttm.get("net_income"))
    m0 = (ni0 / rev0) if (ni0 is not None and rev0 and rev0 > 0) else None
    import math
    weights = {}
    for p_sym, rec in (pm.get("_rec") or {}).items():
        w = 1.0
        if rev0 and rev0 > 0 and rec.get("rev") and rec["rev"] > 0:
            w *= math.exp(-abs(math.log(rev0 / rec["rev"])) / 1.5)
        if m0 is not None and rec.get("margin") is not None:
            w *= math.exp(-abs(m0 - rec["margin"]) / 0.06)
        # كلُّ قرينٍ يحمل حصّةً ثابتة والتشابهُ يزيدها — لا يحكم قرينٌ واحدٌ القطاعَ (D475)
        weights[p_sym] = SIM_FLOOR + (1 - SIM_FLOOR) * w
    pw = {k: [(rec[k], weights[ps]) for ps, rec in (pm.get("_rec") or {}).items() if k in rec]
          for k in ("pe", "pb", "ps", "pocf", "ev_ebit", "ev_sales")}
    pw["yield"] = pm.get("yield") or []
    peers = sorted(peers, key=lambda x: -weights.get(x, 0))
    pm = pw
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
                  sector=sector, beta=beta, dps_ttm=dps, peers=pm, peer_symbols=peers, notes=notes,
                  stale_days=stale)


def blend(res: dict, calibrated: dict | None, archetype: str | None, dy: float | None) -> dict:
    """المرجّحُ النهائيّ: النماذجُ الجديدة والمحرّكُ المُعايَر بحصّةٍ مقيسةٍ لكلّ نمط،
    والهدفُ لاثني عشر شهراً = القيمة × (1 + كلفةِ الحقوق − عائدِ التوزيع)."""
    new_v = res.get("value")
    old_v = _n((calibrated or {}).get("value"))
    a = BLEND_ALPHA.get(archetype or "", DEFAULT_ALPHA)
    res["models_value"] = new_v
    if new_v and old_v and old_v > 0:
        v = a * new_v + (1 - a) * old_v
        lo_o = _n(calibrated.get("low")) or old_v
        hi_o = _n(calibrated.get("high")) or old_v
        res["low"] = round(min(a * res["low"] + (1 - a) * lo_o, v), 2)
        res["high"] = round(max(a * res["high"] + (1 - a) * hi_o, v), 2)
        res["value"] = round(v, 2)
        # حصّةُ صفرٍ لا تُعرض عائلةً — ما لا يدخل القيمةَ لا يُرى كأنه يدخلها (D473)
        res["families"] = [dict(f, weight=round(f["weight"] * a, 3)) for f in res.get("families", [])] + ([
            {"family": "calibrated", "name": "المحرّكُ المُعايَر على السوق السعوديّ", "value": round(old_v, 2),
             "low": round(lo_o, 2), "high": round(hi_o, 2), "weight": round(1 - a, 3), "models": None}] if a < 1 else [])
        res["blend"] = {"alpha": a, "calibrated": round(old_v, 2)}
    elif old_v and not new_v:
        res["value"], res["low"], res["high"] = round(old_v, 2), _n(calibrated.get("low")), _n(calibrated.get("high"))
    if res.get("value") and res.get("price"):
        res["upside"] = round((res["value"] / res["price"] - 1) * 100, 2)
        ke = (res.get("rates") or {}).get("ke") or RISK_FREE + EQUITY_PREMIUM
        res["target_12m"] = round(res["value"] * (1 + ke - (dy or 0)), 2)
        res["target_12m_upside"] = round((res["target_12m"] / res["price"] - 1) * 100, 2)
    return res


def _calibrated(sym: str) -> dict | None:
    """القيمةُ المنشورةُ من المحرّك القائم (لقطةُ الفرز) — بنطاقها إن وُجد."""
    try:
        from app.services.market_screener import get_cached_screener
        for r in get_cached_screener() or []:
            if str(r.get("symbol")).replace(".SR", "") == sym:
                v = _n(r.get("fair_value"))
                return {"value": v, "low": _n(r.get("fair_value_low")), "high": _n(r.get("fair_value_high")),
                        "dy": _n(r.get("dividend_yield"))} if v else None
    except Exception:                                              # noqa: BLE001
        pass
    return None


async def for_symbol(symbol: str) -> dict | None:
    from app.services import cache
    sym = str(symbol).replace(".SR", "").strip()
    ck = f"fvm:v11:{sym}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None
    try:
        i = await gather(sym)
        res = value(i) if i else None
        if res is not None:
            cal = _calibrated(sym)
            dy = (i.dps_ttm / i.price) if (i and i.dps_ttm and i.price) else None
            res = blend(res, cal, i.archetype if i else None, dy)
    except Exception as e:                                         # noqa: BLE001
        logger.warning("المحرّكُ المتعدّد لـ{}: {}", sym, e)
        res = None
    cache.set(ck, res or {}, 6 * 60 * 60 if res else 30 * 60)
    return res
