"""القيمةُ العادلة بحسب النموذج الاقتصاديّ — نسبيّةً إلى القطاع.

## التسلسل

    بياناتُ ياهو الخام → النموذجُ القطاعيّ → القيمةُ العادلة
    → السعرُ مقابلها → درجةُ التقييم

و«القيمةُ العادلة» هنا **ليست حقلاً يُقرأ** من المصدر ولا هدفَ محلّلين:
هي ناتجُ نموذجٍ معلَنٍ بمدخلاتٍ معدودة. ولكلّ نموذجٍ طريقتُه، ولا
تُستعمل طريقةٌ لا تناسب بنيةَ القائمة:

  · **FINANCIAL** — السعرُ إلى الدفتريّ مسنداً بالعائد على حقوق الملكية.
    فالمصرفُ يُقيَّم على رأس ماله وعلى ما يولّده منه: بنكٌ عائدُه ضِعفُ
    وسيط قطاعه يستحقّ مضاعفاً دفترياً أعلى بالقدر نفسه. والمضاعفُ
    الربحيّ تحقّقٌ ثانويّ لا أساس.
  · **REIT** — السعرُ إلى الأموال من العمليات حين تكون موثوقة، وإلّا
    فالدفتريُّ **تقريباً** لصافي الأصول. ولا يُسمّى صافيَ أصولٍ: تقريبٌ
    يُعلَن اسمُه، لأن صافي الأصول الحقيقيّ تقييمٌ عقاريّ لا يصلنا.
  · **CYCLICAL** — أرباحٌ معياريةٌ عبر الدورة. وسنةُ القاع تُظهر الشركةَ
    غاليةً بمضاعفٍ آنيّ وهي أرخصُ ما تكون اقتصادياً، فالمضاعفُ الآنيّ
    لا يكون حَكَماً هنا.
  · **OPERATING** — المضاعفُ الربحيّ أو قيمةُ المنشأة إلى الأرباح
    التشغيلية. والتدفّقُ المخصوم لا يُستعمل إلّا حيث يصلح.
  · **REAL_ESTATE** — الدفتريُّ تقريباً لصافي الأصول، ثم المضاعفُ الربحيّ.

## ولماذا نسبيّاً إلى القطاع

المضاعفُ المطلق («دون ‎12 رخيص») حكمٌ لا سندَ له في سوقٍ بعينه. والوسيطُ
القطاعيّ مسطرةٌ من السوق نفسه، بحدٍّ أدنى ثلاثةِ أقران (المادة ٣٩) —
ودونها لا يُعرض مرجعٌ ولا يُخترع.
"""

from __future__ import annotations

from app.data.economic_models import (CYCLICAL, FINANCIAL, OPERATING,
                                      REAL_ESTATE, REIT)

# أقلُّ وسيطِ عائدٍ يصلح مقاماً في `PB_ROE` — شرطُ صلاحيةٍ لا حكمُ جودة.
MIN_MEDIAN_ROE = 5.0

AVAILABLE = "AVAILABLE"
UNAVAILABLE = "UNAVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"


def _n(d: dict | None, k: str):
    v = (d or {}).get(k)
    if isinstance(v, dict):
        v = v.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v == v and abs(v) != float("inf") else None


def _per_share(periods: list[dict] | None, line: str) -> float | None:
    if not periods:
        return None
    last = periods[-1]
    v, sh = _n(last, line), _n(last, "shares_outstanding")
    if v is None or not sh or sh <= 0:
        return None
    return v / sh


# ── ترتيبُ الطرق لكلّ نموذج ─────────────────────────────────────────
# أوّلُ طريقةٍ تكتمل مدخلاتُها هي المستعمَلة، والباقي يُسجَّل مُتاحاً أو
# غير متاح — فيرى المدقّقُ لماذا اختيرت هذه لا تلك.
# ══ لكلّ طريقةٍ اسمٌ صريحٌ يُعرض ══ (المادة ٦)
# البديلُ لا يلبس اسمَ الأصل: إن تعذّرت الأرباحُ قبل الإهلاك فالتقييمُ
# يُسمّى `PB_MEDIAN` لا `EV_EBITDA` محسوباً على مقامٍ آخر. فيرى القارئ
# **بماذا** قُيّمت الشركة، ولا يُقارَن تقييمٌ دفتريّ بآخرَ ربحيّ وكأنهما
# طريقةٌ واحدة.
PB_ROE = "PB_ROE"
PE_MEDIAN = "PE_MEDIAN"
PE_MID_CYCLE = "PE_MID_CYCLE"
P_FFO = "P_FFO"
NAV_PROXY = "NAV_PROXY"
EV_EBITDA = "EV_EBITDA"
PB_MEDIAN = "PB_MEDIAN"

METHODS: dict[str, tuple[str, ...]] = {
    FINANCIAL:   (PB_ROE, PE_MEDIAN),
    REIT:        (P_FFO, NAV_PROXY),
    CYCLICAL:    (PE_MID_CYCLE, EV_EBITDA, PB_MEDIAN),
    OPERATING:   (PE_MEDIAN, EV_EBITDA),
    REAL_ESTATE: (NAV_PROXY, PE_MEDIAN),
}

_LABEL = {
    PB_ROE: "الدفتريُّ مسنداً بالعائد على حقوق الملكية",
    PE_MEDIAN: "المضاعفُ الربحيّ على وسيط القطاع",
    P_FFO: "السعرُ إلى الأموال من العمليات",
    NAV_PROXY: "تقريبُ صافي الأصول (دفتريٌّ — وليس صافيَ أصولٍ مقوَّماً)",
    PE_MID_CYCLE: "المضاعفُ على أرباحٍ معياريةٍ عبر الدورة",
    EV_EBITDA: "قيمةُ المنشأة إلى الأرباح قبل الإهلاك",
    PB_MEDIAN: "الدفتريُّ على وسيط القطاع",
}


def _try(method: str, features: dict, periods: list[dict] | None,
         medians: dict) -> tuple[float | None, list[str], list[str]]:
    """(القيمةُ العادلة، المدخلاتُ التي وصلت، التي لم تصل)."""
    have: list[str] = []
    gone: list[str] = []

    def need(name: str, v):
        (have if v is not None else gone).append(name)
        return v

    if method == PB_ROE:
        bvps = need("القيمة الدفترية للسهم", _per_share(periods, "total_equity")
                    or _per_share(periods, "equity"))
        roe = need("العائد على حقوق الملكية", _n(features, "roe"))
        m_pb = need("وسيط الدفتريّ", medians.get("p_b"))
        m_roe = need("وسيط العائد", medians.get("roe"))
        if None in (bvps, roe, m_pb, m_roe) or roe <= 0:
            return None, have, gone
        # ══ مقامٌ يقارب الصفر ليس مرجعاً ══ (كشفه المالك — D135)
        # النسبةُ `roe ÷ وسيط القطاع` تنفجر حين يكون الوسيطُ ضئيلاً:
        # قطاعُ التأمين وسيطُ عائده ‎1.0٪، فشركةٌ عائدُها ‎10.5٪ تُعطي
        # نسبةَ ‎10.5 يقصّها الحدُّ إلى ‎3.0 — فيصير **القصُّ** هو ما
        # يحدّد القيمة لا البيانات، وتخرج الشركاتُ كلُّها عند السقف
        # نفسه فلا تفرّق الطريقةُ بينها.
        #
        # فيُشترط للطريقة مقامٌ ذو معنى: وسيطُ عائدٍ يبلغ ‎5٪ على الأقلّ
        # — وهو ليس حكماً على جودة القطاع بل **شرطُ صلاحيةِ القسمة**.
        # ودونه تسقط الطريقةُ وتُجرَّب التي تليها في النموذج، ويُعلَن
        # السببُ بدل أن يُنشر رقمٌ مصدرُه حدُّ القصّ.
        if m_roe < MIN_MEDIAN_ROE:
            gone.append(f"وسيطُ عائد القطاع {m_roe:.1f}٪ دون "
                        f"{MIN_MEDIAN_ROE:.0f}٪ — مقامٌ لا يصلح مرجعاً")
            return None, have, gone
        ratio = min(max(roe / m_roe, 0.25), 3.0)
        return round(bvps * m_pb * ratio, 2), have, gone

    if method == PE_MEDIAN:
        last = (periods or [{}])[-1] if periods else {}
        eps = need("ربحية السهم", _n(last, "eps")
                   or _per_share(periods, "net_income"))
        m_pe = need("وسيط المضاعف الربحيّ", medians.get("p_e"))
        if eps is None or m_pe is None or eps <= 0:
            return None, have, gone
        return round(eps * m_pe, 2), have, gone

    if method == PE_MID_CYCLE:
        neps = need("الربحية المعيارية", _n(features, "normalized_eps"))
        m_pe = need("وسيط المضاعف الربحيّ", medians.get("p_e"))
        if neps is None or m_pe is None or neps <= 0:
            return None, have, gone
        return round(neps * m_pe, 2), have, gone

    if method == P_FFO:
        ffo_ps = need("الأموال من العمليات للسهم", _per_share(periods, "_ffo"))
        m = need("وسيط السعر إلى الأموال", medians.get("p_ffo"))
        if ffo_ps is None or m is None or ffo_ps <= 0:
            return None, have, gone
        return round(ffo_ps * m, 2), have, gone

    if method in (NAV_PROXY, PB_MEDIAN):
        bvps = need("القيمة الدفترية للسهم", _per_share(periods, "total_equity")
                    or _per_share(periods, "equity"))
        m_pb = need("وسيط الدفتريّ", medians.get("p_b"))
        if bvps is None or m_pb is None or bvps <= 0:
            return None, have, gone
        return round(bvps * m_pb, 2), have, gone

    if method == EV_EBITDA:
        last = (periods or [{}])[-1] if periods else {}
        eb = _n(last, "ebitda")
        if eb is None:
            op, dep = _n(last, "operating_income"), _n(last, "depreciation")
            eb = (op + abs(dep)) if (op is not None and dep is not None) else None
        eb = need("الأرباح قبل الإهلاك", eb)
        m = need("وسيط قيمة المنشأة", medians.get("ev_ebitda"))
        sh = need("الأسهم القائمة", _n(last, "shares_outstanding"))
        debt = _n(last, "total_debt")
        cash = _n(last, "ending_cash") or 0.0
        if None in (eb, m, sh) or eb <= 0 or sh <= 0 or debt is None:
            return None, have, gone
        equity_v = eb * m - (abs(debt) - cash)
        if equity_v <= 0:
            return None, have, gone
        return round(equity_v / sh, 2), have, gone

    return None, have, gone


def valuation_report(model: str | None, features: dict,
                     periods: list[dict] | None, medians: dict | None,
                     price: float | None) -> dict:
    """تقريرُ التقييم لشركةٍ واحدة — الطريقةُ ومدخلاتُها ونتيجتُها.

    ولا يُخفى ما لم يصل: كلُّ طريقةٍ تُذكر بحالتها، والمستعمَلةُ أوّلُ
    ما اكتملت مدخلاتُه بترتيب نموذجها.
    """
    out: dict = {
        "valuation_method": None, "valuation_method_label": None,
        "valuation_inputs_available": [], "valuation_inputs_missing": [],
        "fair_value": None, "current_price": price,
        "upside_pct": None, "valuation_confidence": UNAVAILABLE,
        "methods_tried": [],
    }
    if model is None:
        out["valuation_confidence"] = NOT_APPLICABLE
        return out
    medians = medians or {}

    for m in METHODS.get(model, ()):
        fv, have, gone = _try(m, features, periods, medians)
        out["methods_tried"].append(
            {"method": m, "label": _LABEL[m],
             "status": AVAILABLE if fv is not None else UNAVAILABLE,
             "missing": gone})
        if fv is not None and out["fair_value"] is None:
            out.update({"valuation_method": m,
                        "valuation_method_label": _LABEL[m],
                        "valuation_inputs_available": have,
                        "valuation_inputs_missing": gone,
                        "fair_value": fv})

    if out["fair_value"] is None:
        first = out["methods_tried"][0] if out["methods_tried"] else {}
        out["valuation_inputs_missing"] = first.get("missing", [])
        return out

    if isinstance(price, (int, float)) and price > 0:
        out["upside_pct"] = round((out["fair_value"] / price - 1) * 100, 1)
    # الثقةُ في التقييم: طريقتان اكتملتا تُصدّق إحداهما الأخرى.
    ok = sum(1 for t in out["methods_tried"] if t["status"] == AVAILABLE)
    out["valuation_confidence"] = ("مرتفعة" if ok >= 2
                                   else "متوسطة" if out["upside_pct"] is not None
                                   else "منخفضة")
    return out
