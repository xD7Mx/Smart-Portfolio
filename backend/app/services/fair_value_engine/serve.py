"""تشغيلُ محرّك خصم التدفّقات على قوائمِنا المصدرية (D264).

## لماذا

المحرّكُ مبنيٌّ ومحروسٌ منذ زمن، لكنّه كان **معزولاً**: مدخلاتُه تُجلب
من ياهو مباشرةً (‏`fetch.py`)، ومعاييرُه ناقصةٌ فيمتنع. وقد اكتملت
المعايير: المعدَّلُ الخالي من المخاطر من صكٍّ سياديٍّ عشريّ (‏D249)،
والبيتا مقيسةٌ من سوقنا (‏D257)، والقوائمُ رسميةٌ مدقَّقةٌ حيث وصلت
(‏D263). فبقي أن يُوصَل **بقوائمنا** لا بمصدرٍ رابعٍ يخصّه.

## القاعدة

  · **البابُ الواحد**: القوائمُ تُقرأ من `market_service.get_financials`
    — نفسِه الذي تقرأ منه الدرجةُ وكلُّ شاشة. فلا يقيس المحرّكُ شركةً
    بأرقامٍ تخالف ما يعرضه الجدولُ فوقه.
  · **الرسميُّ يرفع الثقة، وغيرُه يخفضها درجة**: قوائمُ XBRL مدقّقةٌ
    موقَّعة، وقوائمُ المزوّد تقديرٌ — والفرقُ يُعلَن في الثقة لا يُبتلع.
  · **الامتناعُ جوابٌ**: ما نقصت بنودُه أو خرج عن حدّ المعقول يمتنع،
    ويُقال سببُه — ولا يُعرض رقمٌ ضعيفٌ باسمٍ قويّ.
"""
from __future__ import annotations

from loguru import logger

CACHE_TTL = 6 * 60 * 60


def _frame(periods: list[dict], mapping: dict[str, str]):
    """فتراتُنا ← جدولُ المحرّك بأسمائه: الأحدثُ عموداً أوّلَ كما يتوقّع."""
    import pandas as pd
    cols, data = [], {lbl: [] for lbl in mapping}
    for p in reversed(periods):                     # الأحدثُ أوّلاً
        cols.append(str(p.get("as_of") or p.get("year")))
        for lbl, key in mapping.items():
            data[lbl].append(p.get(key))
    df = pd.DataFrame(data, index=cols).T
    return df.dropna(how="all")


def build_fundamentals(symbol: str, fin: dict, *, price: float | None,
                       shares: float | None = None):
    """`Fundamentals` من قوائمنا — بلا نداءٍ خارجيٍّ واحد."""
    from .fetch import Fundamentals
    periods = [p for p in (fin.get("periods") or []) if isinstance(p, dict)]
    if not periods:
        return None
    income = _frame(periods, {
        "Total Revenue": "revenue",
        "Net Income": "net_income",
        "Interest Expense": "interest_expense",
        "EBIT": "ebit",
    })
    balance = _frame(periods, {
        "Stockholders Equity": "equity",
        "Total Debt": "total_debt",
        "Cash And Cash Equivalents": "ending_cash",
        "Ordinary Shares Number": "shares_outstanding",
    })
    cash = _frame(periods, {
        "Operating Cash Flow": "operating_cash_flow",
        "Capital Expenditure": "capex",
    })
    return Fundamentals(
        ticker=str(symbol), price=price, shares=shares, currency="SAR",
        fin_currency="SAR", income=income, balance=balance, cash=cash,
        info={"sharesOutstanding": shares} if shares else {},
        fetched_at=str(fin.get("as_of") or ""),
    )


async def value_for_symbol(symbol: str, *, price: float | None = None) -> dict | None:
    """قيمةُ الشركة بخصم التدفّقات — أو None إن امتنع المحرّك.

    ولا يُنادى مصدرٌ خارجيّ: القوائمُ من البابِ الواحد، والسعرُ ممرَّرٌ من
    المستدعي (هو نفسُه سعرُ الشاشة)، والمعاييرُ من ملفّها وقراءاتِها الحيّة.
    """
    from app.services import cache
    sym = str(symbol or "").replace(".SR", "").strip()
    if not sym:
        return None
    ck = f"dcf:{sym}:{round(price or 0, 2)}"
    hit = cache.get(ck)
    if hit is not None:
        return hit or None

    from app.services.market_data import market_service
    from .engine import value_company
    from .params import ParamsError, load_params

    fin = await market_service.get_financials(f"{sym}.SR", allow_supplement=False)
    if not fin or not fin.get("periods"):
        return None
    # ══ عددُ الأسهم من فتراتنا نفسِها ══
    # أوّلُ تشغيلٍ للحارس: المحرّكُ امتنع دائماً لأن عددَ الأسهم غائب —
    # كنتُ أطلبه من كاشٍ قد يكون فارغاً. وهو حقلٌ في **فتراتنا** أصلاً
    # (‏`shares_outstanding`، تقرؤه الحوكمةُ والمقاييسُ القطاعية)، فيُقرأ
    # منها: أحدثُ فترةٍ تحمله. وما لم يوجد فيها يُطلب من الكاش، وما لم
    # يوجد أصلاً يمتنع المحرّكُ — ولا يُقدَّر عددُ أسهمِ شركة.
    shares = None
    for _p in reversed(fin.get("periods") or []):
        v = _p.get("shares_outstanding") if isinstance(_p, dict) else None
        if isinstance(v, (int, float)) and v > 0:
            shares = float(v)
            break
    if shares is None:
        try:
            info = cache.get(f"fund:yahoo:{sym}") or {}
            v = info.get("shares_outstanding") or info.get("sharesOutstanding")
            shares = float(v) if isinstance(v, (int, float)) and v > 0 else None
        except Exception:                                         # noqa: BLE001
            shares = None
    f = build_fundamentals(sym, fin, price=price, shares=shares)
    if f is None:
        return None
    # ══ اعتماديٌّ لا تجريبيّ ══ (D279)
    # كان التشغيلُ بـ`allow_unverified=True, allow_stale=True` — وهو وضعُ
    # **التجربة** بنصِّ الميثاق: «مخرجاتُها تُعلَّم غيرَ اعتمادية». وُضع يومَ
    # كانت المعاييرُ ناقصةً ليعمل المحرّكُ أصلاً، ثمّ اكتملت المعايير
    # (‏D249 · D257 · D264) و**نسيتُ أن أرفع العلَم** — فبقي الرقمُ يُعرض
    # باسمٍ اعتماديٍّ وهو مولودٌ في وضع التجربة. وهذا ما سمّاه المالكُ
    # إخفاقاً، وهو كذلك.
    #
    # والآن يُطلب الوضعُ الصارم: معاييرُ موثَّقةٌ غيرُ شائخة. وإن لم تكن
    # كذلك **يمتنع المحرّك** ويُقال سببُه — ولا يُهبَط سرّاً إلى التجربة،
    # لأن هبوطاً صامتاً يعيد العطبَ نفسَه بعد شهر.
    try:
        p = load_params()
        out = value_company(sym, f, p)
    except ParamsError as e:
        logger.warning("DCF {} امتنع — المعايير ليست اعتمادية: {}", sym, e)
        cache.set(ck, {}, CACHE_TTL)
        return None
    except Exception as e:                                        # noqa: BLE001
        logger.debug("DCF {}: {}: {}", sym, type(e).__name__, e)
        return None
    if out.get("abstained") or not out.get("value"):
        cache.set(ck, {}, CACHE_TTL)                # امتناعٌ يُحفَظ كامتناع
        return None

    # ══ مصدرُ القوائم يرفع الثقةَ أو يخفضها ══
    # قوائمُ XBRL مدقّقةٌ موقَّعة، وقوائمُ المزوّد تقديرٌ — فالفرقُ يُعلَن.
    src = str(fin.get("source") or "")
    if "XBRL" not in src:
        order = ["مرتفعة", "متوسطة", "منخفضة"]
        i = order.index(out["confidence"]) if out.get("confidence") in order else 2
        out["confidence"] = order[min(i + 1, 2)]
        out.setdefault("notes", []).append("قوائمُ مزوّدٍ لا إفصاحٌ رسميّ")
    else:
        out.setdefault("notes", []).append("قوائمُ رسميةٌ مدقَّقة")
    rng = out.get("range") or {}
    res = {
        "value": out["value"],
        "low": rng.get("low") if isinstance(rng, dict) else None,
        "high": rng.get("high") if isinstance(rng, dict) else None,
        "confidence": out.get("confidence"),
        "model": out.get("model"),
        "notes": out.get("notes") or [],
        "statements_source": src or "ياهو",
        "entry_price": out.get("entry_price"),
        "margin_of_safety": out.get("margin_of_safety"),
    }
    cache.set(ck, res, CACHE_TTL)
    return res
