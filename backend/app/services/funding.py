"""تمويلُ الشراء: كم منه من «إعادة الاستثمار» وكم من السيولة (‏D730 · بأمر المالك 2026-11-14).

قال المالك: «أنا أضع عدد الأسهم… والتطبيق يحسب مباشرةً كم نصيبها من إعادة الاستثمار… بالسعر الذي نفّذتُ به لا بآخر
إغلاق… لازم نخرج بصفر أخطاء». فالتقسيمُ هنا وحده — تقرؤه المعاينةُ قبل التأكيد ويُعاد حسابُه عند الحفظ نفسِه، فما يراه
المالك هو ما يُسجَّل أو لا يُسجَّل شيء.

القواعد (وكلٌّ منها يسدّ ثغرة):
  ١ نصيبُ الشركة بالريال من جدول «التوزيع النسبي» نفسِه (‏allocation.split_need) — لا حسابٌ ثانٍ يخالفه.
  ٢ الأسهمُ بسعر التنفيذ الفعليّ (+ نصيبها من العمولة)، لا بآخر إغلاق.
  ٣ أسهمٌ صحيحة تُقرَّب للأسفل: لا يُنفَق من الحوض أكثرُ من نصيب الشركة، وما بقي منه يبقى فيه.
  ٤ شراءٌ بتاريخٍ ماضٍ لا يأخذ من الحوض إلا ما لا يُنقص تمويلَ شراءٍ موسومٍ بعده (‏reinvest_headroom).
  ٥ صفٌّ واحدٌ لتنفيذٍ واحد (كما في كشف الوسيط)، والشقُّ الممَوَّل أسهمٌ لا مبلغ: فتعديلُ السعر لاحقاً يتبعه المبلغُ وحده.
"""
from __future__ import annotations

import math

REINVEST_TAGS = ("REINVEST", "DIVIDEND", "PROFIT")


def _typ(t) -> str:
    v = getattr(t, "transaction_type", None)
    return str(getattr(v, "value", v) or "")


def reinvested_amount(t) -> float:
    """ما موّله حوضُ إعادة الاستثمار من عمليةٍ مسجَّلة — المصدرُ الواحد لكلّ من يجمع المشتريات الموسومة.

    بلا وسم ⇒ صفر. بوسمٍ بلا ‏reinvest_qty ⇒ الإجماليّ كلّه (السجلُّ القديم كما كان). وبتقسيمٍ ⇒ الإجماليّ × الأسهمُ
    الممَوَّلة ÷ الكمية — أي أسهمُها بسعرها ونصيبُها من العمولة بالنسبة نفسِها، فيبقى الشقّان مساويَين للإجماليّ تماماً."""
    if _typ(t) != "BUY" or getattr(t, "funding_source", None) not in REINVEST_TAGS:
        return 0.0
    total = float(getattr(t, "total_amount", 0) or 0)
    rq = getattr(t, "reinvest_qty", None)
    if rq is None:
        return total
    q = float(getattr(t, "quantity", 0) or 0)
    if q <= 0:
        return 0.0
    return total * min(max(float(rq), 0.0), q) / q


def split_qty(qty: float, price: float, fees: float, allowance: float) -> int:
    """كم سهماً من ‏qty يموّله مبلغُ ‏allowance بسعر التنفيذ — صحيحٌ مقرَّبٌ للأسفل، ولا يتجاوز الكمية."""
    qty, price, fees, allowance = float(qty or 0), float(price or 0), float(fees or 0), float(allowance or 0)
    if qty <= 0 or price <= 0 or allowance <= 0:
        return 0
    unit = price + fees / qty
    return int(max(0, min(math.floor(qty), math.floor(allowance / unit + 1e-9))))


async def auto_split(db, company_id: int, qty: float, price: float, fees: float, when) -> dict:
    """التقسيمُ الآليّ لشراءٍ قبل تسجيله — يُستدعى من المعاينة ومن الحفظ بالمدخلات نفسِها فيعطي الجوابَ نفسَه."""
    from app.api.v1.endpoints.allocation import company_reinvest_share
    from app.services.portfolio_return import reinvest_headroom
    share = await company_reinvest_share(db, company_id)
    head = await reinvest_headroom(db, when)
    allowance = max(0.0, min(share, head))
    rq = split_qty(qty, price, fees, allowance)
    qty = float(qty or 0)
    unit = (float(price or 0) + (float(fees or 0) / qty if qty else 0.0))
    total = qty * float(price or 0) + float(fees or 0)
    rei_amt = total * rq / qty if qty else 0.0
    return {
        "reinvest_qty": rq,
        "liquidity_qty": qty - rq,
        "reinvest_amount": round(rei_amt, 2),
        "liquidity_amount": round(total - rei_amt, 2),
        "company_share": round(share, 2),       # نصيبُ الشركة بالريال كما في «التوزيع النسبي»
        "headroom": round(head, 2),             # ما يحتمله الحوضُ في تاريخ العملية
        "unit_cost": round(unit, 6),
    }


def funding_suffix(t) -> str:
    """وصفُ تمويل الشراء في السجلّ وكشف الحساب — من موضعٍ واحد: «(إعادة استثمار)» للشراء كلّه،
    و«(منها N سهم إعادة استثمار)» للشراء المقسَّم (‏D730). وبلا وسم: لا شيء."""
    if _typ(t) != "BUY" or getattr(t, "funding_source", None) not in REINVEST_TAGS:
        return ""
    rq, q = getattr(t, "reinvest_qty", None), float(getattr(t, "quantity", 0) or 0)
    if rq is not None and float(rq) < q:
        return f" (منها {float(rq):g} سهم إعادة استثمار)"
    return " (إعادة استثمار)"
