"""طبقةُ البيانات المعياريّة — بين مصدرٍ متقلّبٍ ومحرّكٍ ثابت.

## لماذا طبقة

المحرّكُ كان يبحث عن أسماء ياهو مباشرةً، فصار كلُّ تغيّرٍ في المصدر
عطباً في القرار: `ebitda` تغيب فتُستبدل بالربح التشغيليّ، و`eps` تغيب
فيسقط النموُّ كلُّه، و`dividends_paid` تغيب فتُقرأ «صفرَ توزيع». وقِيس
أثرُ ذلك على السوق: التقييمُ قام لصفرٍ من ‎268 والنموُّ لسبعَ عشرة.

فبينهما طبقةٌ واحدة:

    خامُ ياهو → توحيدُ الأسماء → تدقيقُ الإشارة والوحدة
    → اشتقاقُ ما يصحّ رياضياً فقط → عرضُه للمحرّك

والمحرّكُ بعدها لا يعرف ياهو ولا أسماءه. يسأل عن بندٍ معياريّ فيُجاب
بقيمةٍ وحالة، ولا يُجاب أبداً بقيمةٍ مصنوعة.

## الحالاتُ ثلاثٌ لا رابع

    CALCULATED     رقمٌ ورد أو اشتُقّ من واردٍ اشتقاقاً صحيحاً
    NOT_AVAILABLE  لم يصل، ولا يُقدَّر
    NOT_APPLICABLE لا معنى له في بنية هذه القائمة

ولا «صفرٌ كاذب» ولا «بديلٌ صامت»: البديلُ إن استُعمل **يُسمّى باسمه**
ويُسجَّل مصدرُه، فيقرأ المدقّقُ من أين جاء كلُّ رقم.

## تدقيقُ الإشارة — لماذا يلزم

مصدرُنا يُبلّغ المصروفَ الرأسماليّ والتوزيعاتِ سالبةً أحياناً وموجبةً
أخرى، والدَّينَ موجباً دوماً. وحسابٌ لا يوحّد الإشارةَ يُخرج تدفّقاً
حرّاً موجباً لشركةٍ تنزف، أو رافعةً سالبة. فتُوحَّد هنا مرّةً: ما هو
تدفّقٌ خارجٌ يُخزَّن بقيمته المطلقة ويُطرح حيث يجب.
"""

from __future__ import annotations

CALCULATED = "CALCULATED"
NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"


# ── توحيدُ الأسماء ───────────────────────────────────────────────────
# لكلّ بندٍ معياريّ أسماؤه المحتملة في المصدر، بالترتيب. وأوّلُ ما يصل
# رقماً يُعتمد، ويُسجَّل الاسمُ الذي جاء منه.
ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "total_revenue", "totalRevenue"),
    "net_income": ("net_income", "netIncome", "net_income_common"),
    "eps": ("eps", "diluted_eps", "basic_eps"),
    "operating_income": ("operating_income", "operatingIncome", "ebit"),
    "gross_profit": ("gross_profit", "grossProfit"),
    "depreciation": ("depreciation", "depreciation_amortization",
                     "depreciationAndAmortization", "d_and_a"),
    "ebitda": ("ebitda", "normalized_ebitda"),
    "interest_expense": ("interest_expense", "interestExpense"),
    "total_assets": ("total_assets", "totalAssets"),
    "total_equity": ("total_equity", "equity", "stockholders_equity"),
    "total_liabilities": ("total_liabilities", "totalLiabilities"),
    "total_debt": ("total_debt", "totalDebt"),
    "cash": ("ending_cash", "cash", "cash_and_equivalents"),
    "current_assets": ("current_assets", "currentAssets"),
    "current_liabilities": ("current_liabilities", "currentLiabilities"),
    "inventory": ("inventory",),
    "operating_cash_flow": ("operating_cash_flow", "operatingCashFlow"),
    "capex": ("capex", "capital_expenditure", "capitalExpenditure"),
    "free_cash_flow": ("free_cash_flow", "freeCashFlow"),
    "dividends_paid": ("dividends_paid", "cash_dividends_paid"),
    "shares_outstanding": ("shares_outstanding", "sharesOutstanding",
                           "share_issued", "ordinary_shares_number"),
}

# بنودٌ تُخزَّن بقيمتها المطلقة لأنها تدفّقاتٌ خارجة: المصدرُ يقلب
# إشارتَها بين شركةٍ وأخرى، والحسابُ يطرحها صراحةً حيث يجب.
_OUTFLOWS = ("capex", "dividends_paid", "interest_expense")
# وبنودٌ لا تكون سالبةً بحالٍ — سالبُها خطأُ مصدرٍ لا واقعةُ شركة.
_NEVER_NEGATIVE = ("revenue", "total_assets", "total_debt", "cash",
                   "inventory", "shares_outstanding", "current_assets",
                   "current_liabilities", "total_liabilities")


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v == v and abs(v) != float("inf") else None


def normalize_period(raw: dict) -> tuple[dict, dict]:
    """فترةٌ واحدة موحَّدةَ الأسماء مدقَّقةَ الإشارة — و(القيم، المصادر)."""
    out: dict = {}
    src: dict = {}
    for canon, names in ALIASES.items():
        for name in names:
            v = _num((raw or {}).get(name))
            if v is None:
                continue
            if canon in _NEVER_NEGATIVE and v < 0:
                # سالبٌ حيث لا يكون السالب: يُطرح ولا يُصحَّح بالقيمة
                # المطلقة — تصحيحُه اختراعٌ لرقمٍ لم يُبلَّغ.
                continue
            out[canon] = abs(v) if canon in _OUTFLOWS else v
            src[canon] = name
            break
    if raw.get("year") is not None:
        out["year"] = raw["year"]
    return out, src


def normalize(periods: list[dict] | None) -> tuple[list[dict], dict]:
    """السلسلةُ كلُّها موحَّدة، ومعها خريطةُ مصادر كلّ بند."""
    rows, sources = [], {}
    for p in (periods or []):
        r, s = normalize_period(p)
        rows.append(r)
        for k, v in s.items():
            sources.setdefault(k, v)
    return rows, sources


def series(rows: list[dict], key: str) -> list[float]:
    """قيمُ بندٍ عبر الفترات — الواردةُ وحدها، بترتيبها."""
    return [r[key] for r in rows if isinstance(r.get(key), (int, float))]


# ══ الاشتقاقاتُ المسموحة ══
#
# ولا يُشتقّ إلّا ما يصحّ رياضياً: مقامٌ موجبٌ غيرُ صفر، وبسطٌ وارد.
# ونتيجةٌ لا معنى لها (مضاعفُ ربحيةٍ على خسارة) تُعاد `None` ولا تُعرض
# رقماً كبيراً — فالكبيرُ يُقرأ رخصاً وهو انعدامُ معنى.

def ebitda_of(row: dict) -> tuple[float | None, str]:
    """الأرباحُ قبل الإهلاك — بندٌ واردٌ أو ربحٌ تشغيليٌّ **مع** إهلاك.

    ولا يُستبدل الربحُ التشغيليّ بها عند غياب الإهلاك: ذلك تسميةُ رقمٍ
    باسم رقمٍ آخر، ويُنشر مضاعفٌ محسوبٌ على مقامٍ ليس هو.
    """
    v = _num(row.get("ebitda"))
    if v is not None:
        return v, "ebitda"
    op, dep = _num(row.get("operating_income")), _num(row.get("depreciation"))
    if op is None or dep is None:
        return None, NOT_AVAILABLE
    return op + abs(dep), "operating_income + depreciation"


def net_debt_of(row: dict) -> float | None:
    d = _num(row.get("total_debt"))
    if d is None:
        return None
    return d - (_num(row.get("cash")) or 0.0)


def per_share(row: dict, key: str) -> float | None:
    v, sh = _num(row.get(key)), _num(row.get("shares_outstanding"))
    if v is None or not sh or sh <= 0:
        return None
    return v / sh


def eps_of(row: dict) -> tuple[float | None, str]:
    """ربحيةُ السهم — البندُ الوارد، أو الربحُ على عدد الأسهم.

    والاشتقاقُ مكافئٌ رياضياً للأصل لا قريبٌ منه، فيُسمح به ويُسمّى.
    """
    v = _num(row.get("eps"))
    if v is not None:
        return v, "eps"
    v = per_share(row, "net_income")
    return (v, "net_income ÷ shares") if v is not None else (None, NOT_AVAILABLE)


def cagr(first: float | None, last: float | None, years: int) -> float | None:
    """نموٌّ مركّب — ولا يُحسب من أساسٍ غيرِ موجب.

    والأساسُ السالب يجعل الجذرَ عديمَ المعنى، ونتيجتُه رقمٌ يُقرأ نموّاً
    وهو ليس شيئاً. فيُعاد `None` صراحةً.
    """
    if first is None or last is None or years <= 0:
        return None
    if first <= 0 or last <= 0:
        return None
    return round(((last / first) ** (1 / years) - 1) * 100, 2)


def cagr_best(rows: list[dict], key: str, want: int = 5,
              floor: int = 2) -> tuple[float | None, int | None]:
    """أطولُ نافذةٍ صالحة وعددُ سنواتها — ‎5 ثم ‎3 ثم ‎2 (المادة ٩).

    والطرفُ الأخير يُثبَّت على آخر فترةٍ ورد فيها البند؛ تحريكُه يغيّر
    معنى «الأحدث». ونافذةٌ دون سنتين لا تُنتج اتّجاهاً.
    """
    idx = [i for i, r in enumerate(rows)
           if isinstance(r.get(key), (int, float))]
    if len(idx) < 2:
        return None, None
    end = idx[-1]
    for start in idx:
        yrs = end - start
        if yrs < floor or yrs > want:
            continue
        v = cagr(rows[start].get(key), rows[end].get(key), yrs)
        if v is not None:
            return v, yrs
    return None, None


# ══ طبقةُ التوزيعات ══ (المادة ١٠)
#
# لا يُبنى التوزيعُ على `dividends_paid` وحده: يغيب عن كثيرٍ من الشركات
# فتُقرأ «لا توزيع» وهي توزّع. فالترتيب: نصيبُ السهم المعلَن من بيانات
# السوق، ثم المدفوعُ من قائمة التدفّقات مقسوماً على الأسهم. وما تعذّر
# يبقى `NOT_AVAILABLE` ولا يصير صفراً.

def dividends(rows: list[dict], info: dict | None,
              price: float | None) -> dict:
    """التوزيعُ بحالته: نصيبُ السهم · العائد · التاريخ · الاستدامة."""
    info = info or {}
    out: dict = {}

    dps = _num(info.get("dividend_per_share"))
    dps_src = "dividend_per_share"
    if dps is None or dps <= 0:
        d = _num((rows or [{}])[-1].get("dividends_paid")) if rows else None
        sh = _num((rows or [{}])[-1].get("shares_outstanding")) if rows else None
        if d and sh and sh > 0:
            dps, dps_src = abs(d) / sh, "dividends_paid ÷ shares"
        else:
            dps, dps_src = None, NOT_AVAILABLE
    out["dps"] = dps
    out["dps_source"] = dps_src

    if dps and price and price > 0:
        out["dividend_yield"] = round(dps / price * 100, 2)
        out["dividend_yield_status"] = CALCULATED
    else:
        out["dividend_yield"] = None
        out["dividend_yield_status"] = NOT_AVAILABLE

    # ── التاريخُ يُقرأ من بندٍ **ورد** ──
    # سلسلةٌ لم تصل تعني «لا نعلم»، وسلسلةٌ وردت أصفاراً تعني «لم توزّع».
    seen = [r["dividends_paid"] for r in (rows or [])
            if isinstance(r.get("dividends_paid"), (int, float))]
    if seen:
        out["dividend_years"] = sum(1 for d in seen if d != 0)
        out["dividend_years_status"] = CALCULATED
    else:
        out["dividend_years"] = None
        out["dividend_years_status"] = NOT_AVAILABLE

    g, span = cagr_best(rows or [], "dividends_paid", want=5)
    out["dividend_growth"] = g
    out["dividend_growth_status"] = CALCULATED if g is not None else NOT_AVAILABLE
    out["dividend_growth_years"] = span

    # ── الاستدامة: التوزيعُ إلى الربح، ولا تُحسب على خسارة ──
    div = [abs(r["dividends_paid"]) for r in (rows or [])[-2:]
           if isinstance(r.get("dividends_paid"), (int, float))
           and r["dividends_paid"]]
    ni = [r["net_income"] for r in (rows or [])[-2:]
          if isinstance(r.get("net_income"), (int, float)) and r["net_income"] > 0]
    if div and ni:
        out["payout_ratio"] = round(
            (sum(div) / len(div)) / (sum(ni) / len(ni)) * 100, 1)
        out["payout_ratio_status"] = CALCULATED
    else:
        out["payout_ratio"] = None
        out["payout_ratio_status"] = (
            NOT_APPLICABLE if div and not ni else NOT_AVAILABLE)
    return out
