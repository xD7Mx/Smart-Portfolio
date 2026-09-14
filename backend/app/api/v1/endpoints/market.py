import asyncio
import hashlib as _hashlib
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.response import success_response
from app.core.auth import require_owner
from app.models.market import MarketNews, MarketEvent, Watchlist, WatchlistGroup

router = APIRouter()
# مسارٌ عامٌّ للبثّ المباشر وحدَه (‏EventSource لا يُرسل رؤوساً · D290).
public_router = APIRouter()


def _normalize_symbol(symbol: str) -> str:
    """Saudi tickers are pure digits on Yahoo as e.g. 2222.SR."""
    s = symbol.strip().upper()
    if s.isdigit() and not s.endswith(".SR"):
        return f"{s}.SR"
    return s


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


@router.get("/history/{symbol}")
async def get_price_history(symbol: str, range: str = "3mo"):
    """Daily close history for charts — cached 24h per symbol."""
    from app.services.market_data import market_service
    if range not in ("1mo", "3mo", "6mo", "1y", "2y", "5y"):
        range = "6mo"
    points = None
    if hasattr(market_service.primary, "get_history"):
        points = await market_service.primary.get_history(_normalize_symbol(symbol), range)
    return success_response(data=points or [])


@router.get("/library")
async def get_market_library():
    """Sahmak monthly company library (empty until API paths confirmed)."""
    from app.services import sahmak_library
    lib = await sahmak_library.company_library()
    return success_response(data=lib)


@router.get("/company/{symbol}")
async def get_company_analysis(symbol: str, db: AsyncSession = Depends(get_db)):
    """Full automatic analysis (no button): live price + full multi-year
    financial statements + technical verdict + strengths/weaknesses +
    sector-relative valuation + AI score/100 + investment decision. The
    financial score/verdict here are the EXACT SAME statement-based
    analysis as the governance page — never a separate opinion. Cached 24h
    so a page open costs no extra calls."""
    from app.services.analysis import analyze_company
    ysym = _normalize_symbol(symbol)
    data = await analyze_company(ysym, db=db)
    if not data:
        # ══ السببُ يُقال ولا يُنسب إلى الرمز ══
        # كانت الرسالة «لا توجد بيانات لهذا الرمز حالياً» — وهي نسبةُ نقصٍ
        # إلى الورقة المالية. ورآها المالك على «صندوق البلاد التقني» بعد
        # مسحٍ للسوق استنفد حصّةَ ياهو اليومية، فظنّ الصندوق بلا بيانات
        # وهو مسعَّرٌ على ياهو نفسه (‏25.50 ريالاً في صورته).
        # والفرقُ حاسم: الأولى تدفعه إلى حذف الورقة، والثانية تقول له
        # «انتظر» — وهي الصادقة.
        from app.services.usage_tracker import usage as _usage
        u = _usage("yahoo")
        if u.get("daily_limit") and u.get("daily_used", 0) >= u["daily_limit"]:
            reason = (f"حصّةُ مصدرنا اليومية نفدت ({u['daily_used']}/"
                      f"{u['daily_limit']}) — الرمزُ سليم، والبياناتُ تعود "
                      f"مع تجدّد الحصّة.")
        else:
            reason = ("لم تصلنا بياناتُ هذا الرمز من مصدرنا الآن — "
                      "قد يكون المصدر محدوداً بالنداء مؤقّتاً.")
        from app.data.saudi_directory import name_of as _name_of
        return success_response(data={
            "symbol": symbol, "name": _name_of(symbol) or symbol,
            "unavailable_reason": reason,
        })
    data["symbol"] = symbol
    # Flatten common fundamentals to the top level so existing UI keeps working.
    f = data.get("fundamentals") or {}
    for k in ("market_cap", "revenue", "net_income", "eps", "pe_ratio", "roe", "roa",
              "profit_margin", "dividend_yield", "week52_low", "week52_high",
              "avg_volume", "target_mean_price"):
        data.setdefault(k, f.get(k))
    # ══ عائدُ التوزيعات من المُنتِج الواحد ══ (D223)
    # كانت الصفحةُ تأخذ رقمَ المزوّد وحدَه، والفرزُ يسقط إلى حسابٍ آخر متى
    # غاب — فرقمان تحت اسمٍ واحد. الآن الترتيبُ نفسُه في الموضعين، ويعود
    # المصدرُ مع الرقم.
    try:
        from app.services.dividend_yield import resolve as _dy_resolve
        _dy, _dy_src = _dy_resolve(symbol, data.get("price"))
        if _dy is not None:
            data["dividend_yield"] = _dy
            data["dividend_yield_source"] = _dy_src
            if isinstance(data.get("fundamentals"), dict):
                data["fundamentals"]["dividend_yield"] = _dy
    except Exception:                                             # noqa: BLE001
        pass
    data["overall_score"] = data.get("ai_score")
    # Sharia compliance for ANY market stock — same layered source the
    # portfolio uses (Maqasid → Argaam), so the market lookup shows the
    # crescent badge exactly like a held company does.
    try:
        from app.services import maqasid
        r = maqasid.rating(symbol)
        if r and r.get("status"):
            data["sharia_status"] = r["status"]
            data["sharia_source"] = r.get("source")
    except Exception:
        pass

    # ══ درجةٌ واحدة تُحسب مرّةً واحدة ══ (عطبٌ رآه المالك)
    # كان هذا الموضع يستدعي `evaluate_company` **مرّةً ثانية** بعد أن
    # حسب `analyze_company` الدرجةَ نفسها في السطر الأول — استجابةٌ واحدة
    # فيها حسابان لسؤالٍ واحد. وتعليقُ هذا الموضع نفسه كان يَعِد بـ«مصدر
    # حقيقة واحد، لا درجة ثانية» بينما الشيفرةُ تحته تُنتج الثانية.
    #
    # ولا يكفي أن يتّحد المحرّك (‏D043): الاستدعاءان يمرّران **قطاعين**
    # من مصدرين مختلفين وحالةَ شركةٍ في أحدهما دون الآخر، فيفترق الحكم
    # ولو اتّحد الحاسب. ورأى المالك أثرَه: شارةٌ في الترويسة تقول 72
    # وبطاقةٌ تحتها تقول 57 — للشركة نفسها في الشاشة نفسها.
    #
    # فالدرجةُ تُقرأ الآن ممّا حُسب فعلاً. ولا يمكن أن تفترق لأنها ليست
    # رقمين: هي الرقمُ نفسه معروضاً في موضعين.
    _fin = data.get("financial") or {}
    data["governance"] = {
        "evaluable": data.get("evaluable"),
        "score": _fin.get("score"),
        "finance_score": _fin.get("score"),
        "narrative": _fin.get("verdict"),
        "decision": (data.get("decision") or {}).get("label"),
    }
    return success_response(data=data)


def _quarterly_view(data: dict) -> dict:
    """الصيغة المالية المعتمدة للأرباع: الحالي · السابق · المماثل.

    هكذا تُقرأ النتائج الربعية في تداول وأرقام وفي أيّ إفصاحٍ رسميّ، ولسببٍ
    وجيه: مقارنةُ ربعٍ بالذي قبله تكشف **الزخم**، ومقارنتُه بمماثله قبل سنة
    تُحيّد **الموسمية**. وشركةٌ يرتفع ربعها عن سابقه وينخفض عن مماثله ليست
    نامية — هي في موسمها القويّ وحسب. وجدولٌ يعرض ستّة أرباعٍ متتالية بلا
    هذا التمييز يترك القارئ يحسبها بنفسه.

    والمماثل يُطابَق **بالتاريخ لا بالموضع**: ربعٌ ناقصٌ في السلسلة (وهو وارد
    من المصدر) يجعل «قبل أربعة صفوف» يشير إلى ربعٍ آخر — فيُقارَن الربع
    الثاني بالثالث ويُسمّى مماثلاً. فيُبحث عن الشهر نفسه قبل سنة بهامش شهر.
    """
    periods = sorted((data.get("periods") or []),
                     key=lambda x: x.get("as_of") or "")
    if not periods:
        return {"periods": [], "years": [], "frequency": "quarterly"}
    current = periods[-1]
    previous = periods[-2] if len(periods) >= 2 else None

    def _ym(p):
        a = p.get("as_of") or ""
        return (int(a[:4]), int(a[5:7])) if len(a) >= 7 else None

    year_ago = None
    cur = _ym(current)
    if cur:
        for p in periods[:-1]:
            ym = _ym(p)
            if ym and ym[0] == cur[0] - 1 and abs(ym[1] - cur[1]) <= 1:
                year_ago = p
                break

    FIELDS = ("revenue", "net_income", "eps", "equity", "book_value", "debt_ratio",
              "operating_cash_flow", "ending_cash", "free_cash_flow",
              "interest_coverage")

    def _chg(a, b):
        # النسبة تُحسب على القيمة المطلقة للأساس: أساسٌ سالب (خسارة) يقلب
        # إشارة النسبة فيُقرأ التحسّن تراجعاً.
        out = {}
        for f in FIELDS:
            x, y = (a or {}).get(f), (b or {}).get(f)
            out[f] = (round((x - y) / abs(y) * 100, 1)
                      if x is not None and y not in (None, 0) else None)
        return out

    cols = [c for c in (year_ago, previous, current) if c is not None]
    return {
        "frequency": "quarterly",
        "periods": cols,
        "years": [c["year"] for c in cols],
        "labels": {"current": current.get("year"),
                   "previous": (previous or {}).get("year"),
                   "year_ago": (year_ago or {}).get("year")},
        # تغيّران لا واحد: المتتالي يقيس الزخم، والسنويّ يُحيّد الموسمية.
        "changes_qoq": _chg(current, previous) if previous else {},
        "changes_yoy": _chg(current, year_ago) if year_ago else {},
        # `changes` يبقى للتوافق مع أيّ قارئٍ قديم — ويحمل السنويّ لأنه
        # المقياس الذي يُبنى عليه الحكم عادةً.
        "changes": _chg(current, year_ago) if year_ago else (
            _chg(current, previous) if previous else {}),
        "verdict": None, "verdict_tone": None, "investment_phase": False,
    }


def _quarterly_from_argaam(sym: str) -> dict | None:
    """نتيجةُ الربع من «أرقام» — ربحٌ صافٍ لفترتين بأسمائهما (D253 · D259).

    وهي **ليست قائمةً كاملة**: «أرقام» تنشر صافيَ ربح الربع ومقارنتَه
    بمماثله، لا الإيرادَ والتدفّقَ والميزانية. فتُعرض بما هي، ويُعلَن
    مصدرُها ونوعُها — ولا يُملأ فراغٌ باشتقاقٍ ولا يُسمّى ما ليس قائمةً
    قائمةً. وتُستبدَل كلُّها حين تصل طبقةُ XBRL الرسمية.
    """
    try:
        from app.services.argaam_results import for_symbol
        rec = (for_symbol(sym) or {}).get("quarter")
    except Exception:                                             # noqa: BLE001
        rec = None
    if not isinstance(rec, dict):
        return None
    prev, cur = rec.get("prev"), rec.get("current")
    if prev is None and cur is None:
        return None
    # أرقامُ «أرقام» بملايين الريالات — والجدولُ يعرض بالريال كبقيّة القوائم.
    def _m(v):
        return round(float(v) * 1_000_000, 2) if isinstance(v, (int, float)) else None

    cols = []
    if prev is not None:
        cols.append({"year": rec.get("prev_label") or "المماثل", "net_income": _m(prev)})
    if cur is not None:
        cols.append({"year": rec.get("current_label") or "الربع الحالي",
                     "net_income": _m(cur)})
    return {
        "frequency": "quarterly",
        "source": "أرقام",
        "kind": "net_income_only",
        "periods": cols,
        "years": [c["year"] for c in cols],
        "changes": {"net_income": rec.get("change_pct")},
        "changes_yoy": {"net_income": rec.get("change_pct")},
        "changes_qoq": {},
        "verdict": None, "verdict_tone": None, "investment_phase": False,
    }


@router.get("/financials/{symbol}")
async def get_company_financials(symbol: str, period: str = "annual"):
    """Three-year income/balance/cashflow with YoY change + section grouping +
    a deterministic, rule-based executive verdict — powers the governance
    report and is the exact same real basis the AI's finance score uses."""
    from app.services.market_data import market_service
    sym = _normalize_symbol(symbol)
    # الربعيّ مسارٌ مستقلّ (‏get_quarterly_financials): السنويُّ يُغذّي محرّك
    # الحوكمة، فلا يُقحَم فيه تبديلُ تردّدٍ يخصّ العرض وحده.
    if period == "quarterly":
        # ══ الربعيُّ بترتيب الطبقات ══ (D259 · بأمر المالك)
        # «تداول ثمّ أرقام وبالأخير ياهو — وأتمنّى ألّا نصل لياهو لأنه لا
        # يدعم الربع سنوي». فتُقرأ الطبقاتُ بترتيبها، ويُعلَن مصدرُ ما
        # عُرض مع الأرقام — لا يُخلط مصدران بلا بيان.
        view = _quarterly_from_argaam(sym)
        if not view:
            q = await market_service.get_quarterly_financials(sym)
            if not q or not q.get("periods"):
                return success_response(
                    data=None, message="لا توجد قوائم ربعية متاحة لهذا الرمز.")
            view = _quarterly_view(q)
        # والربعيُّ يأخذ الخلاصةَ نفسَها — طلبها المالكُ للفترتين معاً،
        # ولا مبرّرَ لشاشةٍ تحلّل السنويَّ وتصمت عن الربعيّ.
        from app.services.financial_brief import brief as _brief
        _b = await _brief(view.get("periods") or [], kind="quarterly", symbol=sym)
        view["verdict"] = _b["line"]
        view["verdict_by"] = _b["by"]
        view["signals"] = _b["signals"]
        # واللونُ من الحكم الحتميّ لا من نصِّ النموذج — شريطٌ يخضرّ فوق
        # جملةٍ تحذّر عطبٌ وقعنا فيه قبلاً (D151).
        from app.services.scores import financial_verdict as _fv
        from app.services.scores import verdict_tone as _vt
        _qp = view.get("periods") or []
        view["verdict_tone"] = _vt(_fv(_qp)) if _qp else None
        return success_response(data=view)
    data = await market_service.get_financials(sym)
    if not data or not data.get("periods"):
        return success_response(data=None, message="لا توجد قوائم مالية متاحة لهذا الرمز حالياً.")

    periods = data["periods"]
    latest, prev = periods[-1], (periods[-2] if len(periods) >= 2 else None)

    def yoy(field):
        if not prev:
            return None
        a, b = latest.get(field), prev.get(field)
        if a is None or not b:
            return None
        return round((a - b) / abs(b) * 100, 1)

    # ══ الحكمُ واللونُ والدرجة من المحرّك الأصليّ ══ (بأمر المالك · D151)
    # هذا الجدولُ عينُه هو ما بُنيت عليه القواعد: نموُّ الإيراد وجودةُ
    # الأرباح والمديونيةُ والتغطية. فالحكمُ يُشتقّ منه بقاعدةٍ حتمية،
    # واللونُ من الحكم نفسِه لا من رقمٍ آخر — فلا يخضرّ شريطٌ فوق جملةٍ
    # تحذّر. وكان اللونُ يأتي من `composite_finance_score` والجملةُ من
    # سردٍ آخر، فانفصل ثلاثتُها عن الجدول الذي تحتها.
    from app.services.scores import (is_investment_phase, financial_verdict,
                                     verdict_tone as _tone,
                                     _finance_score_from_periods)
    verdict = financial_verdict(periods)
    verdict_tone = _tone(verdict)
    # ══ الخلاصةُ: جيمناي ثمّ القاعديّ ══ (D278 · بأمر المالك)
    # اللونُ يبقى من الحكم الحتميّ (لا يُلوَّن شريطٌ برأي نموذج)، والجملةُ
    # تصير تحليلاً مقيساً: كلُّ رقمٍ في سطر جيمناي يُطابَق بما حُسب، وما
    # لم يُطابِق رُدّ السطرُ كلُّه وكُتب القاعديّ.
    from app.services.financial_brief import brief as _brief
    _b = await _brief(periods, kind="annual", symbol=sym)
    health = _finance_score_from_periods(periods)
    return success_response(data={
        "symbol": symbol,
        "years": [p["year"] for p in periods],
        "periods": periods,
        "changes": {k: yoy(k) for k in (
            "revenue", "net_income", "eps", "equity", "book_value", "debt_ratio",
            "operating_cash_flow", "ending_cash", "free_cash_flow", "interest_coverage",
        )},
        "verdict": _b["line"],
        "verdict_tone": verdict_tone,
        "verdict_by": _b["by"],
        "verdict_rule": verdict,          # الحكمُ الحتميُّ كما هو — لا يُفقَد
        "signals": _b["signals"],
        # الدرجةُ تُعرض مع الجدول الذي بُنيت عليه — نفسُ رقم صفحة الشركة
        # وقسم السوق وبطاقة الحوكمة.
        "finance_score": health,
        "investment_phase": is_investment_phase(periods),
    })


@router.get("/dividends/{symbol}")
async def get_company_dividends(symbol: str):
    """Dividend profile: frequency, last-10-years history, and an upcoming/last
    distribution note (e.g. 'أحقية قادمة بعد يومين' / 'آخر توزيع قبل أسبوعين')."""
    from app.services.market_data import market_service
    from datetime import date
    data = await market_service.get_dividends(_normalize_symbol(symbol))
    if not data:
        return success_response(data=None, message="لا توجد بيانات توزيعات متاحة لهذا الرمز حالياً.")

    # last 10 announced years, aggregated per year
    from collections import defaultdict
    by_year = defaultdict(float)
    for h in data.get("history", []):
        by_year[h["year"]] += h["amount"]
    years = sorted(by_year.keys())[-10:]
    yearly = [{"year": y, "amount": round(by_year[y], 3)} for y in years]

    # note about the next ex/eligibility date or the last distribution
    note = None
    today = date.today()
    ref = data.get("ex_date") or data.get("pay_date")
    try:
        if ref:
            d = date.fromisoformat(ref)
            days = (d - today).days
            if days > 0:
                note = {"type": "upcoming", "text": f"أحقية/توزيع قادم بعد {days} يوم ({ref})"}
            elif days == 0:
                note = {"type": "today", "text": f"يوم الأحقية اليوم ({ref})"}
            else:
                note = {"type": "past", "text": f"آخر أحقية قبل {abs(days)} يوم ({ref})"}
    except Exception:
        note = None
    if not note and data.get("history"):
        last = data["history"][-1]
        try:
            days = (today - date.fromisoformat(last["date"])).days
            note = {"type": "past", "text": f"آخر توزيع معلن قبل {days} يوم ({last['date']}) بقيمة {last['amount']} للسهم"}
        except Exception:
            pass

    return success_response(data={
        "symbol": symbol,
        "frequency": data.get("frequency"),
        "ex_date": data.get("ex_date"),
        "pay_date": data.get("pay_date"),
        "yearly": yearly,
        "recent": data.get("history", [])[-8:][::-1],
        "note": note,
    })


@router.get("/ownership/{symbol}")
async def get_company_ownership(symbol: str):
    """هيكلُ الملكية — النِّسَبُ العامّة، ومعها كبارُ الملاك بأسمائهم (D276).

    ══ بطاقةٌ واحدةٌ لا بطاقتان ══
    البطاقةُ قائمةٌ منذ زمنٍ وتعرض ثلاثَ نسبٍ مجمّعة. وبناءُ بطاقةٍ ثانيةٍ
    لكبار الملاك كان سيكرّر المعنى في شاشةٍ واحدة — وهو العطبُ الذي أطارده
    في الأرقام، فلا أرتكبه في الشاشات. فتُضاف القراءةُ المفصَّلةُ إلى
    الاستجابة نفسِها، وتظهر تحت الشريط إن وُجدت.

    ولا جلبَ هنا: يُقرأ المحفوظُ من الجدولة فقط. وما لم يُقرأ يغيب.
    """
    from app.services.market_data import market_service
    from app.services.ownership import reading as argaam_reading
    from app.services.tadawul_ownership import reading as tadawul_reading

    sym = _normalize_symbol(symbol)
    data = await market_service.get_ownership(sym) or {}

    # ══ تداول ← أرقام، بندًا بندًا ══ (D277)
    # الرسميُّ يتقدّم، ولا يُلغي غيابُ بندٍ فيه قراءةَ الطبقة التالية لبندٍ
    # آخر: المطابقةُ لكلّ بندٍ على حدة — وأوّلُ من نطق يملأه.
    for rec in (tadawul_reading(sym), argaam_reading(sym)):
        if not rec:
            continue
        for key in ("major_holders", "board", "foreign", "insider_deals",
                    "estimates"):
            if rec.get(key) and not data.get(key):
                data[key] = rec[key]
                data.setdefault("detail_sources", {})[key] = rec.get("source")
        data.setdefault("detail_as_of", rec.get("as_of"))
    if data.get("detail_sources"):
        data["detail_source"] = " · ".join(
            dict.fromkeys(data["detail_sources"].values()))
    return success_response(data=data)

async def _portfolio_symbols(db: AsyncSession) -> list[str]:
    # من حيازات المحفظة النشطة (Holding معزول بالمحفظة) لا من دليل الشركات
    # العام — فتتفاعل أخبار المحفظة ومفكرتها مع تبديل المحفظة ووضع التوحيد.
    from app.models.portfolio import Company, Holding
    result = await db.execute(
        select(Company.symbol)
        .join(Holding, Holding.company_id == Company.id)
        .where(Company.status != "ARCHIVED")
        .distinct()
    )
    return [row[0] for row in result.all()]


@router.get("/overview")
async def market_overview(db: AsyncSession = Depends(get_db)):
    """Live tickers (each cached 15 min): TASI index, Brent crude, plus the
    weekly foreign-investor net flow (CMA only publishes this weekly, never
    live — see fetch_weekly_foreign_flow)."""
    import asyncio as _aio

    # ══ اللحظيةُ تبدأ من هنا ══ (D289)
    # هذا أكثرُ المسارات نداءً (اللسانُ وشاشةُ السوق)، فهو موضعُ إيقاظ
    # اللقطة: تُجدَّد إن شاخت أكثرَ من خمس ثوانٍ، ولا يُنتظَر التجديد.
    from app.services.tadawul_market import ensure_fresh as _ensure
    _ensure()
    from app.services.market_data import market_service
    from app.services.news_fetcher import fetch_weekly_foreign_flow
    tasi, brent, flow = await _aio.gather(
        market_service.get_price("^TASI.SR"),
        market_service.get_price("BZ=F"),   # Brent crude futures (USD)
        fetch_weekly_foreign_flow(),
    )
    # Real traded value = real price × real share volume from the same Yahoo
    # quote — not a separate liquidity feed (Tadawul doesn't expose one free),
    # so it's marked as an estimate rather than an official figure.
    if tasi and tasi.get("volume"):
        tasi["traded_value_est"] = round(tasi["price"] * tasi["volume"])

    # ══ اللسانُ مباشرٌ من المؤشّر نفسِه ══ (D252)
    # ياهو يتأخّر عند المزوّد ونخزّنه ربعَ ساعةٍ فوق ذلك — فيُعرض رقمٌ ليس
    # رقمَ السوق الآن. وخدمةُ مؤشّر «تداول» تعطيه بلا تأخير. فيُقدَّم
    # السعرُ والتغيّرُ منها، ويبقى **حجمُ التداول** من ياهو لأن الخدمةَ لا
    # تنشره — ولا يُخترع: ما لا مصدرَ له يبقى كما كان.
    try:
        from app.services.tadawul_market import index_quote
        live = await index_quote()
    except Exception:                                             # noqa: BLE001
        live = None
    if live:
        tasi = {**(tasi or {}), **{k: v for k, v in live.items() if v is not None}}
        if tasi.get("volume"):
            tasi["traded_value_est"] = round(tasi["price"] * tasi["volume"])

    # Reliability floor: persist every good ticker; when the free source
    # fails (rate limit/outage/restart), serve the last good copy with its
    # capture timestamp instead of an empty market screen.
    from app.services import lastgood
    if tasi:
        lastgood.save("market:tasi", tasi)
    else:
        tasi = lastgood.load("market:tasi", max_age_seconds=7 * 24 * 3600)
    if brent:
        lastgood.save("market:brent", brent)
    else:
        brent = lastgood.load("market:brent", max_age_seconds=7 * 24 * 3600)
    if flow:
        lastgood.save("market:flow", flow)
    else:
        flow = lastgood.load("market:flow", max_age_seconds=21 * 24 * 3600)

    return success_response(data={
        "tasi": tasi,
        "brent": brent,
        "flow": flow,
        "status": "ok" if (tasi or brent) else "unavailable",
    })

_movers_build: "asyncio.Task | None" = None


@router.get("/movers")
async def get_market_movers():
    """Full-market top gainers/losers + advancer/decliner counts — served
    from the hourly scheduled snapshot (see app/services/market_movers.py),
    never computed live per-request (a full scan hits Yahoo, the site's one
    shared unofficial price source, once per company — doing that on every
    page view risks it rate-limiting/blocking the server, breaking prices
    everywhere else on the site too). If the job hasn't run yet (fresh
    install before the first scheduled run), computes it once here so the
    page isn't stuck empty until the next scheduled time."""
    from app.services.market_movers import get_cached_market_movers, compute_market_movers
    from app.services import lastgood
    global _movers_build
    snapshot = get_cached_market_movers()
    if snapshot is None:
        # لا مسحَ كاملاً داخل الطلب: مئات النداءات على مهلة المتصفّح تُنهي
        # الطلب بخطأ ثم يعيد react-query المحاولة، فتبقى البطاقة هيكلاً بلا
        # نهاية. يُطلق البناء في الخلفية مرّةً واحدة، ويُخدَم الطلب فوراً من
        # آخر لقطةٍ سليمة (أو حالةِ «لا بيانات» المعلنة أدناه).
        if _movers_build is None or _movers_build.done():
            _movers_build = asyncio.create_task(compute_market_movers())
        snapshot = None
    if snapshot and (snapshot.get("gainers") or snapshot.get("losers")):
        lastgood.save("market:movers", snapshot)
    else:
        # Live scan unavailable (source outage/rate limit, or the scheduled
        # scan hasn't run yet) — serve the LAST successful close with its
        # capture timestamp. No age cap: a month-old close is real data and
        # infinitely better than an empty "not computed yet" screen, which
        # the owner rightly considers an operational failure. The frontend
        # labels it honestly as "آخر إغلاق" via _stale_since.
        snapshot = lastgood.load("market:movers") or snapshot
    return success_response(data=snapshot or {"gainers": [], "losers": [], "advancers": 0, "decliners": 0, "unchanged": 0, "total": 0})


_screener_build: "asyncio.Task | None" = None


@router.get("/screener")
async def get_screener():
    """Whole-market technical screener dataset (فرز الأسهم) — one compact row
    per company (price, SMA50/200, RSI, 52w range, MA distances/flags). Served
    from the daily scheduled scan (see app/services/market_screener.py), or من
    آخر لقطةٍ سليمة.

    **لا يُحسب المسح داخل الطلب.** كان يفعل: مسحٌ كاملٌ لمئات الشركات على
    مهلة الطلب، فيتجاوز مهلة المتصفّح (٣٠ ثانية) ويعيد react-query المحاولة،
    فتظلّ البطاقة هيكلاً لا ينتهي — وهو بالضبط ما نهى عنه المجلس: لكل بطاقة
    نهاية واحدة من ثلاث (بيانات · لا بيانات بسببها · خطأ صريح). الآن يُطلق
    البناء في الخلفية مرّةً واحدة، ويعود الطلب فوراً بحالةٍ معلنة."""
    global _screener_build
    from app.services.market_screener import get_cached_screener, compute_screener
    rows = get_cached_screener()
    if rows is not None:
        # ══ الحقولُ المشتقّةُ تُنعَش عند التقديم ══ (D226)
        # اللقطةُ تحفظ ما كلّف شبكةً (سعرٌ ومتوسّطاتٌ وRSI)، والمشتقُّ من
        # مخزنٍ محلّيٍّ يُقرأ الآن — فلا يخالف الجدولُ صفحةَ السهم بين
        # مسحةٍ وأخرى.
        from app.services.market_screener import refresh_derived_cached
        try:
            rows = await refresh_derived_cached(rows)
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"إنعاشُ حقول الفرز تعذّر: {type(e).__name__}: {e}")
        return success_response(data={"rows": rows, "state": "ready"})

    if _screener_build is None or _screener_build.done():
        _screener_build = asyncio.create_task(compute_screener())
    return success_response(data={"rows": [], "state": "building"})


async def _ensure_news(db: AsyncSession):
    """Populate the news feed on first view instead of waiting for the daily job."""
    have = (await db.execute(select(MarketNews.id).limit(1))).scalar_one_or_none()
    if have is None:
        try:
            from app.services.content_engine import refresh_news
            await refresh_news(db)  # respects the 1h guard; startup usually did this
        except Exception:
            pass


@router.get("/summary")
async def get_market_summary(db: AsyncSession = Depends(get_db)):
    """Live TASI market pulse — a professional brief about the index environment
    (NOT the user's portfolio), computed on a schedule: pre-open (09:30) and at
    the top of every trading hour through the close, Gemini-first with a
    rule-based fallback. This endpoint just serves the last cached pulse (no
    live Gemini per view); if none exists yet (fresh boot), it computes one now."""
    from app.services.ai_content import get_market_brief_snapshot, refresh_market_brief
    snap = get_market_brief_snapshot()
    if snap is None:
        snap = await refresh_market_brief(db)
    return success_response(data=snap)


async def _fallback_price_ticker(db: AsyncSession) -> list:
    """Last-resort ticker content when BOTH real news (Google News RSS) and
    the AI digest are unavailable (e.g. Google blocking this server's IP,
    or the Gemini key/quota being down) — never an empty strip, but also
    never invented text. Built entirely from live prices the app already
    fetches and displays elsewhere on the page, so it's exactly as real as
    any other number on the site, just phrased as a headline."""
    from app.models.portfolio import Company, Holding
    from app.services.market_data import market_service

    rows = (await db.execute(
        select(Company.symbol, Company.company_name)
        .join(Holding, Holding.company_id == Company.id)
        .where(Company.status != "ARCHIVED")
        .limit(12)
    )).all()
    items = []
    for symbol, name in rows:
        price = await market_service.get_price(_normalize_symbol(symbol))
        if not price or price.get("price") is None:
            continue
        chg = price.get("change_pct") or 0
        arrow = "▲" if chg >= 0 else "▼"
        items.append({
            "id": f"price-{symbol}",
            "headline": f"{name} ({symbol}): {price['price']:.2f} ﷼ {arrow} {chg:+.2f}%",
            "summary": None, "company": symbol, "source": "أسعار حية",
            "category": "أسواق", "trusted": True, "url": None,
            "published": None,
        })
    return items


@router.get("/news")
async def get_news(portfolio_only: bool = False, lang: str = "ar", db: AsyncSession = Depends(get_db)):
    """`portfolio_only=true` powers "أخبار المحفظة" — real headlines scoped to
    the companies actually held (by symbol), not the full market feed.
    `lang=en`: أخبار إنجليزية حقيقية عن السوق (لوضع English) — تُجلب مباشرة
    بذاكرة مؤقتة ولا تمسّ قاعدة البيانات."""
    if lang == "en" and not portfolio_only:
        from app.services.news_fetcher import fetch_market_news_en
        items = await fetch_market_news_en()
        return success_response(data=[{
            "id": None, "headline": it["headline"], "summary": it.get("summary"),
            "company": it.get("company"), "source": it.get("source"), "url": it.get("url"),
            "category": it.get("category"), "trusted": it.get("trusted", False),
            "published": it["published"].isoformat() if it.get("published") else None,
        } for it in items])
    await _ensure_news(db)
    symbols = await _portfolio_symbols(db) if portfolio_only else None
    if portfolio_only and not symbols:
        return success_response(data=[])
    # Strictly newest-first by publish date/time (source reputation is only a
    # tiebreaker for items sharing the exact same timestamp). Both feeds are
    # UNLIMITED — every stored headline (the 14-day retention window is the
    # only real bound); the portfolio feed is naturally scoped by symbol.
    query = select(MarketNews)
    if symbols:
        query = query.where(MarketNews.company_symbol.in_(symbols))
    query = query.order_by(MarketNews.published_at.desc().nullslast(), (MarketNews.importance == "HIGH").desc())
    result = await db.execute(query)
    news = result.scalars().all()
    if news:
        return success_response(data=[{"id": n.id, "headline": n.headline, "summary": n.summary, "company": n.company_symbol, "source": n.provider, "url": n.url, "category": n.category, "trusted": n.importance == "HIGH", "published": n.published_at.isoformat() if n.published_at else None} for n in news])
    if portfolio_only:
        return success_response(data=[])
    from app.services.ai_content import market_news
    ai_items = await market_news(await _portfolio_symbols(db))
    if ai_items:
        return success_response(data=ai_items)
    return success_response(data=await _fallback_price_ticker(db))

@router.get("/events-market")
async def get_events_market_wide():
    """General market calendar (major Tadawul companies) — independent of
    the user's own portfolio, for the Market page's own calendar."""
    from app.services.content_engine import market_wide_events
    return success_response(data=await market_wide_events())


@router.get("/event-detail/{detail_id}")
async def get_event_detail(detail_id: str):
    """نصّ الإعلان الكامل — مقدار التوزيع، جدول أعمال الجمعية، نسبة المنحة.

    يُطلب عند فتح بطاقة الإعلان لا مع كل تحديثٍ للمفكرة: نصٌّ لا يُقرأ لا
    يُجلب. وعند التعذّر يُعاد `null` صريحاً فتقول البطاقة «غير متوفّرة» —
    ولا تُختلق تفاصيل.
    """
    from app.services.argaam_calendar import fetch_detail
    return success_response(data={"text": await fetch_detail(detail_id)})


@router.get("/argaam-ids")
async def get_argaam_ids():
    """خريطة رمز تداول ← رابط صفحة الشركة في «أرقام».

    تُبنى تلقائياً من صفحةٍ تحمل السوق كلَّه، وتُحفظ فتدوم عند انقطاع
    المصدر. تُخدَم مع لحظة بنائها — فالواجهة تعرف عمرها ولا تعرضه لحظياً.
    """
    from app.services.argaam_ids import build, snapshot, BASE
    await build()
    snap = snapshot()
    return success_response(data={
        "base": BASE + "/ar/company/companyoverview/marketid/3/companyid/",
        "ids": snap["ids"], "built_at": snap["built_at"], "count": len(snap["ids"]),
    })


@router.get("/directory")
async def company_directory():
    """دليلُ الشركات — السوقُ كلُّه في نداءٍ واحد (D256).

    بأمر المالك: زرٌّ بجانب البحث في «نبض السوق». والدليلُ يُجمع من
    مصادرِه بترتيبها: **اسمُنا المنسَّق وقطاعُه وحكمُه الشرعيّ** من دليل
    التطبيق (وفوقه طبقةُ مزامنة «تداول» التي تُضيف المُدرَج الجديد وتوسم
    الموقوف)، **ورابطُ «أرقام»** من خريطة المعرِّفات المقيسة — فمن لا
    معرِّفَ له لا يُختلق له رابطٌ ولا يُفتح له بحثٌ باسمه.

    ولا سعرَ هنا: هذا دليلُ هويّةٍ لا شاشةُ تداول، وخلطُهما يجعل الفتحةَ
    ثقيلةً بلا حاجة.
    """
    from app.data.saudi_directory import SAUDI_DIRECTORY, is_suspended, suspended_since
    from app.services.argaam_ids import snapshot as _ids, url_for
    # `snapshot()` يعيد {ids, built_at} لا الخريطةَ نفسَها — والفرقُ
    # يُخرج رابطاً لكلّ الشركات أو لا أحد. كشفه الحارسُ في أوّل تشغيل.
    ids = (_ids() or {}).get("ids") or {}
    rows = []
    for sym, row in sorted(SAUDI_DIRECTORY.items()):
        if not isinstance(row, dict):
            continue
        rows.append({
            "symbol": sym,
            "name": row.get("name") or sym,
            "sector": row.get("sector"),
            # ولا حكمَ شرعياً هنا: دليلُ التطبيق لا يحمله (مصدرُه «مقاصد»
            # ويُعرض في صفحة السهم) — وحقلٌ يُقرأ من حيث لا وجودَ له يُخرج
            # «غير متوفّر» لكلّ الشركات فيبدو عطباً وهو اختلاقُ حقل.
            "logo": row.get("logo"),
            "argaam_url": url_for(sym, ids),
            "suspended": bool(is_suspended(sym)),
            "suspended_since": suspended_since(sym),
        })
    return success_response(data={"count": len(rows), "companies": rows})


@router.get("/sectors")
async def get_sector_analysis():
    """التحليل القطاعي: أداء كل قطاع عبر ٣ش/٦ش/سنة/٣س/٥س + متوسط عائد
    توزيعاته + عدد شركاته. يُحسب مجدولاً ويُخدَم من المخزّن (بلا نداء حيّ)."""
    from app.services.sector_analysis import get_cached_sector_analysis
    return success_response(data=get_cached_sector_analysis() or [])


@router.post("/sectors/rebuild", dependencies=[Depends(require_owner)])
async def rebuild_sectors():
    """بناء التحليل القطاعي فوراً (للمالك)."""
    from app.services.sector_analysis import compute_sector_analysis
    rows = await compute_sector_analysis()
    return success_response(data={"sectors": len(rows or [])})


@router.get("/news/resolve")
async def resolve_news_url(u: str):
    """يتحقّق أن رابط الخبر يفتح فعلاً ويُعيد وجهته النهائية.

    روابط «جوجل نيوز» تمرّ عبر مُحوِّل، وبعض الناشرين يحجب أو يحذف المقال —
    فيرى المستخدم صفحة خطأ بعد أن ينقر من تطبيقنا (إحراج). نتبع التحويلات
    هنا مرّة واحدة عند فتح الخبر، فإن فشل نُعيد url=None فتُخفي الواجهة زرّ
    «المصدر» بدل أن تقود المستخدم إلى خطأ. النتيجة مُخزَّنة ٦ ساعات."""
    from app.services import cache
    import httpx, ipaddress, socket
    from urllib.parse import urlparse
    if not u or not u.startswith(("http://", "https://")):
        return success_response(data={"url": None})

    # ── حماية SSRF ──────────────────────────────────────────────────────
    # هذه النقطة تجلب رابطاً يأتي من البيانات؛ بلا ضبط يمكن توجيهها لعناوين
    # داخلية (localhost / 10.x / 169.254.169.254 لبيانات السحابة) فتتحوّل إلى
    # أداة مسح للشبكة الداخلية. نحصرها في مضيفين عامّين فقط.
    def _public_host(raw: str) -> bool:
        try:
            host = urlparse(raw).hostname
            if not host:
                return False
            for fam, _, _, _, sa in socket.getaddrinfo(host, None):
                ip = ipaddress.ip_address(sa[0])
                if (ip.is_private or ip.is_loopback or ip.is_link_local
                        or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                    return False
            return True
        except Exception:
            return False

    if not _public_host(u):
        logger.warning("Blocked non-public news URL resolve attempt.")
        return success_response(data={"url": None})
    ck = f"newsurl:{u}"
    cached = cache.get(ck)
    if cached is not None:
        return success_response(data={"url": cached or None})

    final = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=8, headers=headers, follow_redirects=True) as client:
            r = await client.get(u)
            # 2xx/3xx ⇒ الوجهة موجودة. 4xx/5xx ⇒ محجوب أو محذوف.
            # نتحقّق من الوجهة النهائية أيضاً: التحويل قد ينتهي لعنوان داخلي.
            if r.status_code < 400 and _public_host(str(r.url)):
                final = str(r.url)
    except Exception as e:
        logger.debug(f"News URL resolve failed for {u[:60]}: {e}")
    cache.set(ck, final or "", 6 * 60 * 60)
    return success_response(data={"url": final})


@router.post("/screener/rebuild", dependencies=[Depends(require_owner)])
async def rebuild_screener():
    """بناء بيانات «فرز الأسهم» فوراً (للمالك) — بدل انتظار المهمّة المجدولة
    ٤ عصراً. تستغرق دقائق (نداء تاريخ لكل شركة، لا يُحسب على الحصّة)."""
    from app.services.market_screener import compute_screener
    rows = await compute_screener()
    return success_response(data={"rows": len(rows or [])})


@router.get("/tadawul-probe", dependencies=[Depends(require_owner)])
async def tadawul_probe():
    """أداة فحص (للمالك فقط): تعرض الاستجابة الخام من موقع «تداول» الرسمي +
    عدد ما فُهم منها، لضبط المُحلِّل على البنية الحقيقية عند أول تشغيل على
    السيرفر (المضيف محجوب عن بيئة التطوير). شغّلها مرّة وأرسل المُخرَج."""
    from app.services.tadawul_announcements import probe_tadawul
    return success_response(data=await probe_tadawul())


@router.get("/argaam-probe", dependencies=[Depends(require_owner)])
async def argaam_probe(db: AsyncSession = Depends(get_db)):
    """محكُّ مرآة «أرقام» الثلاثية: المفكرة · الإفصاحات · الأخبار.

    لماذا هذا المسار موجود: **لم يُقَس أيٌّ من هذه المُحلِّلات على صفحةٍ
    حيّة من بيئة التطوير** — شبكتُها محجوبة عن argaam.com (‏403 عند بوّابة
    الشبكة، قِيس). فالمُحلِّل مبنيٌّ على بنيةٍ مقيسةٍ سابقاً، وقد تتغيّر.

    وكشطُ صفحةٍ للبشر ينكسر صامتاً: يردّ صفراً فيبدو كأن لا أخبار. فهذا
    المسار يفرّق بين الحالتين — ويردّ، عند الفشل، **بصمةً بنيوية** من
    الصفحة (أطوال، وعدد الروابط، وعيّنة) تكفي لتصحيح المُحلِّل بلا تخمين.
    """
    import httpx as _hx
    from app.services.argaam_calendar import (
        BASE, UA, CAL_URL, DISC_URL, NEWS_URL,
        fetch_argaam_calendar, fetch_argaam_disclosures, fetch_argaam_news)

    async def probe(url: str, parser):
        r: dict = {"url": url}
        try:
            async with _hx.AsyncClient(timeout=30, follow_redirects=True,
                                       headers={"User-Agent": UA,
                                                "Accept-Language": "ar,en;q=0.8"}) as c:
                resp = await c.get(url)
            r["http"] = resp.status_code
            body = resp.text or ""
            r["bytes"] = len(body)
            r["article_links"] = body.count("/ar/article/articledetail/id/")
            r["company_entries"] = body.count("relf-Stocksymbol")
        except Exception as e:                                    # noqa: BLE001
            r["error"] = repr(e)
            return r
        try:
            rows = await parser()
            r["parsed"] = len(rows)
            r["sample"] = rows[:3]
            if not rows:
                # عيّنةٌ خامٌ تكفي لتصحيح التعبير النمطيّ من مخرَجٍ حقيقيّ
                i = body.find("/ar/article/articledetail/id/")
                r["raw_hint"] = body[max(0, i - 260): i + 260] if i > -1 else body[:400]
        except Exception as e:                                    # noqa: BLE001
            r["parser_error"] = repr(e)
        return r

    # ══ حالةُ المخزن — الجواب الذي كان ناقصاً ══
    # وُصل قارئُ الشركة بمخزن أرقام، فبدا أن المرآة تمّت. والمخزن نفسه قد
    # يكون فارغاً (المهمّة المجدولة لم تعمل، أو المصدر محجوب) — فيُقرأ
    # الوصلُ نجاحاً وهو أنبوبٌ بلا ماء. هذه الحقول تُظهر ذلك بلا لبس.
    from app.services.content_engine import _cal_load_store
    from app.models.portfolio import Company, Holding
    store = _cal_load_store()
    mine = [s for (s,) in (await db.execute(
        select(Company.symbol).join(Holding, Holding.company_id == Company.id)
        .where(Company.status != "ARCHIVED").distinct())).all() if s]
    by_src: dict = {}
    for ev in store.values():
        by_src[ev.get("source") or "—"] = by_src.get(ev.get("source") or "—", 0) + 1
    per_company = {s: sum(1 for ev in store.values() if str(ev.get("symbol")) == str(s))
                   for s in mine}

    return success_response(data={
        "note": "يُشغَّل على الخادم — بيئة التطوير محجوبة عن أرقام",
        "المخزن": {
            "إجمالي_الأحداث": len(store),
            "بحسب_المصدر": by_src,
            "شركات_محفظتك": per_company,
            "تفسير": ("المخزن فارغ ⇒ لا شيء يُعكس مهما صحّ الوصل: "
                      "المهمّة المجدولة لم تعمل بعد أو المصدر محجوب"
                      if not store else
                      "المخزن عامر — فإن بقيت المفكرة فارغة فالعلّة في الربط لا في المصدر"),
        },
        "المفكرة":   await probe(CAL_URL, lambda: fetch_argaam_calendar(weeks=2)),
        "الإفصاحات": await probe(DISC_URL.format(p=1), lambda: fetch_argaam_disclosures(pages=1)),
        "الأخبار":   await probe(NEWS_URL.format(p=1), lambda: fetch_argaam_news(pages=1)),
    })


@router.get("/calendar-verify", dependencies=[Depends(require_owner)])
async def calendar_verify(symbol: str = "", db: AsyncSession = Depends(get_db)):
    """**محكُّ «افتح في أرقام»** — يقارن ما تعرضه مفكرتنا لشركةٍ بما تعرضه
    صفحتُها في «أرقام»، ويردّ الفروق صريحةً.

    وهذا اختبارُ المالك نفسه، مُنفَّذاً آلياً: كان يفتح الزرّ ويقارن بعينه
    شركةً شركة. والمقارنة اليدوية تكشف الخطأ في الشركة التي فُتحت وحدها،
    وتسكت عن الباقي — فمرّت أخطاءٌ لأن أحداً لم يفتح تلك الشركة بعينها.

    يُشغَّل **على الخادم** لا في المختبر: شبكة التطوير محجوبة عن «أرقام»
    (‏403 عند البوّابة)، فلا يُقاس هذا هناك ولا يُدّعى أنه قِيس.

    بلا `symbol` يفحص كلّ شركات المحفظة ويردّ ملخّصاً بعدد المتطابق
    والزائد والناقص.
    """
    from app.services.argaam_calendar import fetch_argaam_calendar
    from app.services.argaam_ids import build as build_ids, url_for
    from app.services.content_engine import company_calendar
    from app.models.portfolio import Company, Holding

    if symbol:
        pairs = [(symbol, symbol)]
    else:
        rows = (await db.execute(
            select(Company.symbol, Company.company_name)
            .join(Holding, Holding.company_id == Company.id)
            .where(Company.status != "ARCHIVED").distinct()
        )).all()
        pairs = [(s, n or s) for s, n in rows if s]

    # مرجعُ «أرقام» يُجلب مرّةً واحدة للسوق كلّه ثمّ يُقسَّم على الشركات.
    try:
        ref_all = await fetch_argaam_calendar(weeks=4)
    except Exception as e:                                        # noqa: BLE001
        return success_response(data={"error": f"تعذّر بلوغ أرقام: {e!r}",
                                      "hint": "يُشغَّل على الخادم — شبكة التطوير محجوبة"})
    if not ref_all:
        return success_response(data={"error": "أرقام ردّ صفحةً بلا صفوف",
                                      "hint": "المُحلِّل ينكسر صامتاً إن تغيّر تصميم الصفحة"})

    try:
        await build_ids()
    except Exception:
        pass

    out = []
    for sym, name in pairs:
        theirs = [r for r in ref_all if str(r.get("symbol")) == str(sym)]
        try:
            mine_raw = await company_calendar(sym, name)
        except Exception as e:                                    # noqa: BLE001
            out.append({"symbol": sym, "error": repr(e)}); continue
        mine = [m for m in mine_raw if m.get("kind") != "معلومة"]

        def key(d):
            return (str(d.get("date") or d.get("published") or "")[:10],
                    _txt_key(d.get("title") or d.get("headline") or ""))
        mk, tk = {key(m) for m in mine}, {key(t) for t in theirs}
        out.append({
            "symbol": sym, "name": name,
            "argaam_url": url_for(sym),
            "ours": len(mine), "argaam": len(theirs),
            "matched": len(mk & tk),
            "only_ours": [f"{d} · {t}" for d, t in sorted(mk - tk)][:8],
            "only_argaam": [f"{d} · {t}" for d, t in sorted(tk - mk)][:8],
        })

    verdict = {
        "companies": len(out),
        "clean": sum(1 for r in out if not r.get("only_ours") and not r.get("only_argaam")),
        "extra_in_ours": sum(len(r.get("only_ours") or []) for r in out),
        "missing_from_ours": sum(len(r.get("only_argaam") or []) for r in out),
    }
    return success_response(data={"verdict": verdict, "companies": out})


def _txt_key(s: str) -> str:
    """مفتاحُ مقارنةٍ متسامح: الفروق في المسافات والتشكيل والترقيم ليست
    أخطاءً في البيانات، وعدُّها خطأً يُغرق التقرير بضجيجٍ يُخفي الحقيقيّ."""
    import re as _re, unicodedata
    t = unicodedata.normalize("NFKC", s or "")
    t = _re.sub(r"[\u064B-\u065F\u0640]", "", t)          # تشكيل وتطويل
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    t = _re.sub(r"[^\w\u0600-\u06FF]+", " ", t)
    return " ".join(t.split()).strip()[:60]


@router.get("/calendar-diagnose", dependencies=[Depends(require_owner)])
async def calendar_diagnose(symbol: str = "", db: AsyncSession = Depends(get_db)):
    """تشخيص المفكرة: **لماذا هي فارغة**، مصدراً مصدراً.

    المفكرة تُبنى من ثلاثة مصادر مستقلّة، وحين تفرغ لا تقول أيّها سقط — فيبدو
    الخلل في التطبيق وهو في الغالب حجبٌ عند المصدر أو بوّابة ترشيحٍ صارمة.
    هذا التقرير يفتح الصندوق: لكل مصدر عدد ما وصل، وعدد ما نجا من الترشيح،
    وسبب الرفض حين يُرفض.

    `symbol` اختياري — بدونه يفحص أول شركة في حيازاتك."""
    from app.services import cache
    from app.models.portfolio import Company, Holding
    report: dict = {"sources": {}}

    # الشركة موضع الفحص
    if not symbol:
        row = (await db.execute(
            select(Company.symbol, Company.company_name)
            .join(Holding, Holding.company_id == Company.id).limit(1)
        )).first()
        symbol, name = (row[0], row[1]) if row else ("2222", "أرامكو السعودية")
    else:
        name = symbol
    report["symbol"] = symbol

    # ١) إعلانات تداول الرسمية
    src: dict = {"role": "المصدر الرسمي (Saudi Exchange)"}
    try:
        from app.services.tadawul_announcements import (
            fetch_tadawul_announcements, DEFAULT_TADAWUL_URL, TADAWUL_JSON_URL, _raw_fetch)
        src["url"] = DEFAULT_TADAWUL_URL
        src["json_url_configured"] = bool(TADAWUL_JSON_URL)
        status, body = await _raw_fetch(DEFAULT_TADAWUL_URL)
        src["http_status"] = status
        src["body_length"] = len(body or "")
        src["looks_blocked"] = bool(status != 200 or "Access Denied" in (body or "")[:4000])
        allrows = await fetch_tadawul_announcements(force=True)
        src["items_total"] = len(allrows)
        src["items_for_symbol"] = sum(1 for r in allrows if r.get("symbol") == symbol)
    except Exception as e:                                        # noqa: BLE001
        src["error"] = repr(e)
    report["sources"]["tadawul"] = src

    # ٢) إعلانات RSS المجانية + بوّابة التاريخ (أكثر مواضع الفقد صمتاً)
    src = {"role": "Google News RSS + بوّابة تاريخ الحدث"}
    try:
        from app.services.news_fetcher import fetch_corporate_events
        from app.services.content_engine import calendar_event_date
        raw = await fetch_corporate_events([(symbol, name or symbol)]) or []
        src["items_fetched"] = len(raw)
        kept, rejected = [], []
        for it in raw:
            d = calendar_event_date(it.get("headline"), it.get("published"))
            (kept if d else rejected).append(it.get("headline"))
        src["passed_date_gate"] = len(kept)
        # السبب الأشيع: البوّابة تشترط تاريخاً **صريحاً داخل العنوان**، وأغلب
        # عناوين الأخبار لا تحمله — فتسقط كلها بصمت.
        src["rejected_no_explicit_date"] = len(rejected)
        src["rejected_sample"] = rejected[:3]
    except Exception as e:                                        # noqa: BLE001
        src["error"] = repr(e)
    report["sources"]["rss"] = src

    # ٣) بيانات المزوّد: توزيعات ومواعيد نتائج
    src = {"role": "بيانات السوق (توزيعات · مواعيد النتائج)"}
    try:
        from app.services.market_data import market_service
        ysym = f"{symbol}.SR" if str(symbol).isdigit() else symbol
        div = await market_service.get_dividends(ysym)
        src["dividends"] = {"received": bool(div),
                            "ex_date": (div or {}).get("ex_date"),
                            "pay_date": (div or {}).get("pay_date"),
                            "history_rows": len((div or {}).get("history") or [])}
        earn = await market_service.get_earnings_dates(ysym)
        src["earnings_next_date"] = (earn or {}).get("next_date")
    except Exception as e:                                        # noqa: BLE001
        src["error"] = repr(e)
    report["sources"]["provider"] = src

    # ٤) الحصيلة النهائية كما يراها التطبيق
    try:
        from app.services.content_engine import company_calendar
        cal = await company_calendar(symbol, name or symbol) or []
        real = [c for c in cal if (c.get("kind") or "") != "معلومة"]
        report["result"] = {"rows_returned": len(cal), "real_events": len(real),
                            "sample": real[:3]}
    except Exception as e:                                        # noqa: BLE001
        report["result"] = {"error": repr(e)}

    report["store"] = {"market_calendar_cached": bool(cache.get("market:calendar:full"))}
    return success_response(data=report)


@router.post("/tadawul-refresh", dependencies=[Depends(require_owner)])
async def tadawul_refresh():
    """تحديث فوري للمفكرة من المصدر الرسمي (للمالك) — يتجاوز الكاش ويدمج في
    المخزّن الثابت مباشرةً."""
    from app.services.content_engine import build_market_calendar_tadawul
    from app.services.tadawul_announcements import fetch_tadawul_announcements
    await fetch_tadawul_announcements(force=True)
    added = await build_market_calendar_tadawul()
    return success_response(data={"added": added})


@router.get("/events/{symbol}")
async def get_company_events(symbol: str, name: str = ""):
    """Per-company المفكرة — real announcements (strict corporate-action
    filter) MERGED with the company's factual dividend timeline (upcoming
    entitlement/payment dates + recent actually-paid distributions), so the
    tab is never an empty visual hole even for a quiet company. `name`
    (Arabic) comes from the caller's own directory lookup since Google News
    needs it to search well; falls back to the bare symbol if not given."""
    from app.services.content_engine import company_calendar
    return success_response(data=await company_calendar(symbol, name or symbol))


@router.get("/events")
async def get_events(db: AsyncSession = Depends(get_db)):
    """مفكرة المحفظة — the umbrella: every portfolio company's own calendar
    (announcements + factual dividend timeline, same source as each
    company's المفكرة tab) aggregated into one list, plus any stored
    calendar events. Never empty while the portfolio holds real companies."""
    import asyncio
    from app.services.content_engine import company_calendar
    from app.models.portfolio import Company, Holding

    # تتبع المحفظة النشطة: من الحيازات المعزولة لا من دليل الشركات العام —
    # فتتفاعل المفكرة مع تبديل المحفظة/التوحيد، وتفرغ عند المحفظة الصفرية.
    pairs = (await db.execute(
        select(Company.symbol, Company.company_name)
        .join(Holding, Holding.company_id == Company.id)
        .where(Company.status != "ARCHIVED").distinct()
    )).all()
    pairs = [(s, n) for s, n in pairs if s]

    # المفكرة تتبع المحفظة: إن كانت المحفظة فارغة (لا شركات — مثلاً بعد فورمات)
    # تُصبح المفكرة فارغة أيضًا، بلا أي تعبئة ذكاء أو أحداث مخزّنة.
    if not pairs:
        return success_response(data=[])

    out: list[dict] = []
    if pairs:
        results = await asyncio.gather(
            *(company_calendar(sym, name or sym) for sym, name in pairs),
            return_exceptions=True,
        )
        for (sym, name), items in zip(pairs, results):
            if isinstance(items, Exception):
                continue
            for it in items:
                if it.get("kind") == "معلومة":
                    continue  # per-company placeholder — noise at portfolio level
                out.append({
                    # مُعرِّفٌ ثابت: `hash()` على النصّ مُملَّحٌ لكل عملية،
                    # فكان مُعرِّف الصفّ يتبدّل مع كل طلب — والواجهة تبني
                    # القوائم بالمُعرِّف، فتُعيد تركيب البطاقات بلا سبب.
                    # وهو العطب نفسه الذي أفسد مفتاح مخزن المفكرة (D017).
                    "id": f"{sym}-{it.get('published') or ''}-"
                          f"{_hashlib.blake2s(it['headline'].encode('utf-8'), digest_size=5).hexdigest()}",
                    "type": it.get("kind"),
                    "title": it["headline"],
                    "symbol": sym,
                    "company_name": name,
                    "date": it.get("published"),
                    # صنفُ التاريخ (‏announced / event / undated) يُنقل كما
                    # هو. كان يسقط هنا: `company_calendar` يُنتجه و
                    # `get_events` يُعيد بناء الصفّ بحقولٍ مختارة فيُسقطه.
                    # وقناة صقر تفرز به الإفصاحات عن المفكرة، فكان الشرط
                    # `date_kind == "announced"` يقارن **بالعدم**: كلُّ صفّ
                    # يقع في المفكرة ولا يقع في الإفصاحات صفٌّ واحد — تبويب
                    # فارغ أبداً لا لأن لا شيء فيه، بل لأن مِصفاته عمياء.
                    "date_kind": it.get("date_kind"),
                    "url": it.get("url"),
                })

    # Stored calendar events (strictly-filtered announcements) fill in
    # anything the live merge didn't produce.
    result = await db.execute(select(MarketEvent).order_by(MarketEvent.event_date.desc()))
    seen_titles = {o["title"] for o in out}
    for e in result.scalars().all():
        if (e.description or "") in seen_titles:
            continue
        out.append({
            "id": e.id, "type": e.event_type, "title": e.description,
            "symbol": e.company_symbol, "date": e.event_date.isoformat() if e.event_date else None,
            # الأحداث المخزّنة إعلاناتٌ مُرشَّحة بالأصل (انظر توصيف الحقل)
            "date_kind": "announced",
        })

    out.sort(key=lambda x: x.get("date") or "", reverse=True)
    # ══ لا مفكرةَ مخترَعة ══
    # كان هنا سقوطٌ إلى `upcoming_events` — مُوجِّهٌ يقول للنموذج حرفياً
    # «اكتب 6 مواعيد **متوقعة**»، فيخترع أسماء شركاتٍ ورموزاً وتواريخ بلا
    # مصدر، وتُعرض في مفكرةٍ يخطّط المالك بها. وهو خرقٌ مباشر للخطّ الأحمر
    # الثاني في الميثاق: «ما لا مصدر له في التطبيق يُقال عنه غير متوفّر».
    # فالفراغ الصادق أفضل من امتلاءٍ كاذب — والواجهة تقول «لا مواعيد».
    return success_response(data=out)

@router.get("/economic-news")
async def get_economic_news(db: AsyncSession = Depends(get_db)):
    """Real stored economic/macro news (Google News). Self-populates on first view."""
    await _ensure_news(db)
    rows = (await db.execute(
        select(MarketNews).where(MarketNews.category == "اقتصاد")
        .order_by(MarketNews.published_at.desc().nullslast()).limit(8)
    )).scalars().all()
    if not rows:
        # no dedicated economic rows — show the freshest market news instead
        rows = (await db.execute(
            select(MarketNews).order_by(MarketNews.published_at.desc().nullslast()).limit(8)
        )).scalars().all()
    return success_response(data=[{
        "id": n.id, "headline": n.headline, "category": n.category or "اقتصاد",
        "impact": "محايد", "company": n.company_symbol, "source": n.provider,
        "url": n.url, "published": n.published_at.isoformat() if n.published_at else None,
    } for n in rows])


@router.get("/feedstock")
async def get_feedstock():
    """Saudi official feedstock (اللقيم) reference prices — government-set, not a
    live market. Shown as reference because they drive petrochem margins."""
    return success_response(data={
        "note": "أسعار اللقيم المرجعية — تُحدَّد حكومياً وتؤثر على هوامش البتروكيماويات",
        "items": [
            {"name": "الميثان (الغاز الطبيعي)", "price": 1.25, "unit": "$/MMBtu"},
            {"name": "الإيثان", "price": 0.75, "unit": "$/MMBtu"},
            {"name": "البروبان", "price": 430, "unit": "$/طن (مرتبط بأرامكو)"},
            {"name": "البيوتان", "price": 425, "unit": "$/طن (مرتبط بأرامكو)"},
        ],
    })


@router.get("/results")
async def get_financial_results(db: AsyncSession = Depends(get_db)):
    return success_response(data=[], message="Financial results feed.")

@router.get("/dividends")
async def get_market_dividends(db: AsyncSession = Depends(get_db)):
    return success_response(data=[], message="Dividend calendar.")


# ─── قوائم المراقبة (Watchlist groups) ────────────────────────
async def _ensure_default_group(db: AsyncSession) -> int:
    """يضمن وجود مجموعة افتراضية ويُسنِد إليها أي رموز بلا مجموعة. يعيد معرّفها."""
    grp = (await db.execute(
        select(WatchlistGroup).where(WatchlistGroup.is_default.is_(True))
    )).scalar_one_or_none()
    if grp is None:
        grp = (await db.execute(select(WatchlistGroup).order_by(WatchlistGroup.id))).scalars().first()
    if grp is None:
        # طلبان متزامنان عند أول فتحٍ للتطبيق يُنشئان المجموعة معاً، فيفشل
        # أحدهما. الخاسر يقرأ ما كتبه الرابح بدل أن ينهار.
        #
        # المحاولة الواحدة لم تكن تكفي: القراءة الثانية قد تسبق **إتمام** commit
        # الرابح بأجزاء من الثانية فتعود فارغة، فيُعاد رفع الخطأ وتسقط قائمة
        # المراقبة بـ500. نُعيد المحاولة قليلاً قبل الاستسلام.
        import asyncio as _aio
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                grp = WatchlistGroup(name="قائمتي", color="#3B82F6", is_default=True)
                db.add(grp)
                await db.commit()
                await db.refresh(grp)
                break
            except Exception as e:                                # noqa: BLE001
                last_err = e
                await db.rollback()
                await _aio.sleep(0.15 * (attempt + 1))
                grp = (await db.execute(
                    select(WatchlistGroup).order_by(WatchlistGroup.id))).scalars().first()
                if grp is not None:
                    break
        if grp is None:
            raise last_err or RuntimeError("تعذّر تهيئة مجموعة المراقبة الافتراضية")
    # إسناد الرموز القديمة (بلا مجموعة) للمجموعة الافتراضية
    await db.execute(
        Watchlist.__table__.update().where(Watchlist.group_id.is_(None)).values(group_id=grp.id)
    )
    await db.commit()
    return grp.id


def _serialize_group(g: WatchlistGroup) -> dict:
    return {"id": g.id, "name": g.name, "color": g.color or "#3B82F6",
            "is_default": bool(g.is_default), "sort_order": g.sort_order or 0}


@router.get("/watchlist/groups")
async def list_watchlist_groups(db: AsyncSession = Depends(get_db)):
    await _ensure_default_group(db)
    rows = (await db.execute(
        select(WatchlistGroup).order_by(WatchlistGroup.sort_order, WatchlistGroup.id)
    )).scalars().all()
    return success_response(data=[_serialize_group(g) for g in rows])


@router.get("/watchlist/membership")
async def watchlist_membership(symbol: str, db: AsyncSession = Depends(get_db)):
    """المجموعات التي ينتمي إليها رمزٌ بعينه — نداءٌ واحد بدل استعلام كل قائمة
    على حدة. تستهلكه نجمة صفحة الشركة لتعرض علامة صحّ أمام كل قائمة هو عضوٌ
    فيها، فتبقى الواجهة مطابقةً لقاعدة البيانات لا لتخمينٍ محلّي."""
    await _ensure_default_group(db)
    sym = (symbol or "").strip().upper()
    rows = (await db.execute(select(Watchlist.group_id).where(Watchlist.symbol == sym))).scalars().all()
    return success_response(data=[int(g) for g in rows if g is not None])


@router.post("/watchlist/groups", dependencies=[Depends(require_owner)])
async def create_watchlist_group(payload: dict, db: AsyncSession = Depends(get_db)):
    name = str((payload or {}).get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="اسم القائمة مطلوب.")
    g = WatchlistGroup(name=name, color=(payload.get("color") or "#3B82F6"), is_default=False)
    db.add(g); await db.commit(); await db.refresh(g)
    return success_response(data=_serialize_group(g), message="أُنشئت القائمة.")


@router.patch("/watchlist/groups/{group_id}", dependencies=[Depends(require_owner)])
async def update_watchlist_group(group_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(select(WatchlistGroup).where(WatchlistGroup.id == group_id))).scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="القائمة غير موجودة.")
    if payload.get("name") is not None:
        n = str(payload["name"]).strip()
        if not n:
            raise HTTPException(status_code=422, detail="اسم القائمة لا يمكن أن يكون فارغًا.")
        g.name = n
    if payload.get("color") is not None:
        g.color = payload["color"]
    await db.commit()
    return success_response(data=_serialize_group(g), message="حُدّثت القائمة.")


@router.delete("/watchlist/groups/{group_id}", dependencies=[Depends(require_owner)])
async def delete_watchlist_group(group_id: int, db: AsyncSession = Depends(get_db)):
    groups = (await db.execute(select(WatchlistGroup).order_by(WatchlistGroup.id))).scalars().all()
    if len(groups) <= 1:
        raise HTTPException(status_code=422, detail="لا يمكن حذف القائمة الوحيدة — أنشئ قائمة أخرى أولًا.")
    g = next((x for x in groups if x.id == group_id), None)
    if not g:
        raise HTTPException(status_code=404, detail="القائمة غير موجودة.")
    await db.execute(delete(Watchlist).where(Watchlist.group_id == group_id))
    was_default = g.is_default
    await db.execute(delete(WatchlistGroup).where(WatchlistGroup.id == group_id))
    if was_default:
        remaining = next(x for x in groups if x.id != group_id)
        remaining.is_default = True
    await db.commit()
    return success_response(message="حُذفت القائمة وشركاتها.")


# ─── قائمة المراقبة (رموز داخل مجموعة) ─────────────────────────
@router.get("/watchlist")
async def get_watchlist(group_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """شركات المتابعة مع أسعارها الحيّة — ضمن المجموعة المحدّدة (أو الافتراضية)."""
    from app.data import saudi_directory
    if group_id is None:
        group_id = await _ensure_default_group(db)
    rows = (await db.execute(
        select(Watchlist).where(Watchlist.group_id == group_id)
        .order_by(Watchlist.sort_order, Watchlist.created_at)
    )).scalars().all()
    if not rows:
        return success_response(data=[])
    from app.services.market_data import market_service
    ysyms = [_normalize_symbol(r.symbol) for r in rows]
    prices = {}
    try:
        prices = await market_service.get_prices(ysyms)
    except Exception:
        pass
    out = []
    for r in rows:
        p = prices.get(_normalize_symbol(r.symbol)) or {}
        out.append({
            "symbol": r.symbol,
            "name": r.name or saudi_directory.name_of(r.symbol) or r.symbol,
            "price": p.get("price"),
            "change": p.get("change"),
            "change_pct": p.get("change_pct"),
        })
    return success_response(data=out)


@router.post("/watchlist", dependencies=[Depends(require_owner)])
async def add_watchlist(payload: dict, db: AsyncSession = Depends(get_db)):
    from app.data import saudi_directory
    symbol = str((payload or {}).get("symbol") or "").strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="رمز الشركة مطلوب.")
    group_id = (payload or {}).get("group_id")
    if not group_id:
        group_id = await _ensure_default_group(db)
    existing = (await db.execute(
        select(Watchlist).where(Watchlist.symbol == symbol, Watchlist.group_id == group_id)
    )).scalar_one_or_none()
    if existing:
        return success_response(message="الشركة موجودة في هذه القائمة.")
    name = (payload.get("name") or saudi_directory.name_of(symbol) or symbol)
    db.add(Watchlist(symbol=symbol, name=name, group_id=group_id))
    await db.commit()
    return success_response(message="أُضيفت إلى القائمة.")


@router.delete("/watchlist/{symbol}", dependencies=[Depends(require_owner)])
async def remove_watchlist(symbol: str, group_id: int | None = None,
                           all_groups: bool = False, db: AsyncSession = Depends(get_db)):
    """يحذف الرمز من مجموعة **واحدة**: المحدّدة، أو الافتراضية عند إغفالها.

    سابقاً كان إغفال group_id يحذف الرمز من **كل** المجموعات دفعةً واحدة —
    فخّ حقيقي لمن يبني قوائم متعدّدة: إزالة من قائمةٍ تمسحه من الجميع بلا
    إنذار. الحذف الشامل صار فعلاً صريحاً يُطلَب بـ all_groups=true لا سلوكاً
    ضمنياً يقع بالخطأ."""
    q = delete(Watchlist).where(Watchlist.symbol == symbol.strip().upper())
    if not all_groups:
        if group_id is None:
            group_id = await _ensure_default_group(db)
        q = q.where(Watchlist.group_id == group_id)
    await db.execute(q)
    await db.commit()
    return success_response(message="حُذفت من القائمة.")


@router.get("/recommendations/{symbol}")
async def get_company_recommendations(symbol: str):
    """توصيات المحللين لشركة — من «أرقام» وحده، بمخزونٍ أسبوعيّ.

    كالمفكرة: المصدر واحد، والفراغ يبقى فراغاً. ولا يُدسّ إجماع ياهو مكان
    توصيةٍ لبيت خبرةٍ سعوديّ — فالفرق بين الاثنين هو نفسه الفرق الذي أراد
    المالك حسمه حين اختار «أرقام» مرجعاً.
    """
    from app.services import cache
    ck = f"argaam:recs:{symbol}"
    got = cache.get(ck)
    if got is None:
        from app.services.argaam_calendar import fetch_company_recommendations
        got = await fetch_company_recommendations(symbol)
        if got.get("rows"):
            cache.set(ck, got, 7 * 24 * 60 * 60)      # أسبوع
    return success_response(data={
        "rows": got.get("rows") or [],
        "url": got.get("url"),
        # لحظةُ القياس مطلوبة في كل ما يُعرض (بند ٢٤): توصيةٌ عمرها شهر
        # لا تُقرأ رأياً لليوم.
        "fetched_at": got.get("fetched_at"),
    })


@router.get("/recommendations-probe/{symbol}")
async def probe_company_recommendations(symbol: str):
    """أيُّ مسارٍ في «أرقام» يحمل التوصيات فعلاً — يُقاس ولا يُخمَّن.

    المختبر بلا إنترنت، فمسار الصفحة لم يُتحقّق منه إلا على خادم المالك.
    يُعيد هذا ما جُرّب ورمزَ استجابة كلٍّ وعدد ما قُرئ — فيُغلق السؤال
    بقياسٍ واحد بدل تخمينٍ يتكرّر.
    """
    from app.services.argaam_calendar import fetch_company_recommendations
    got = await fetch_company_recommendations(symbol)
    return success_response(data={
        "symbol": symbol, "المسار_الناجح": got.get("url"),
        "عدد_الصفوف": len(got.get("rows") or []),
        "عيّنة": (got.get("rows") or [])[:3],
        # الخلايا كما وصلت — بها يُبنى محلّلُ اسم بيت الخبرة والسعر
        # المستهدف على شكل الجدول الحقيقيّ لا على تخمينه.
        "خلايا_خام": got.get("خلايا_خام"),
        "ما_جُرّب": got.get("tried"),
    })


@router.get("/ratios-probe/{symbol}")
async def probe_company_ratios(symbol: str):
    """أتصل النِّسَبُ الرقابية من «أرقام» فعلاً — يُقاس ولا يُدّعى.

    كنّا نصف كفاية رأس المال والمتعثّرة والنسبة المجمّعة بأنها «خارج
    النطاق»، وهي منشورةٌ ربعياً. فالبندُ غائبٌ عن أنبوبنا لا عن السوق —
    وهذا المسبار يُظهر ما قُرئ وما لم يُقرأ وخلاياه الخام، فيُبنى المحلّل
    على شكل الجدول الحقيقيّ لا على تخمينه.
    """
    from app.services.argaam_calendar import fetch_company_ratios
    got = await fetch_company_ratios(_normalize_symbol(symbol).replace(".SR", ""))
    return success_response(data={
        "symbol": symbol, "الرابط": got.get("url"),
        "النِّسَب": got.get("ratios"),
        "خلايا_خام": got.get("خلايا_خام"),
    })


@router.get("/funds-probe")
async def probe_funds():
    """أللصناديق المتداولة بياناتٌ عند مصادرنا أصلاً — يُقاس ولا يُخمَّن.

    أضيفت صناديقُ السوق العشرة إلى الدليل، فرآها المالك **بلا قيمةٍ ولا
    صورة** وقال: إن لم تكن لها معلومات فلا تضعها. وهو محقّ — صفٌّ فارغ
    أسوأ من غيابٍ صريح.
    ولا أستطيع قياس ذلك من المختبر (بلا إنترنت)، فهذا المسبار يمرّ على
    الرموز العشرة ويقول لكلٍّ منها بالضبط: أجاء سعرٌ من ياهو؟ وكم نقطة
    تاريخٍ؟ وأله معرّفٌ في «أرقام»؟ وكم صفّاً قرأناه من صفحته؟
    فيُبنى القرار — تبقى أم تُحذف أم تُجلب من «أرقام» — على قياسٍ واحد.
    """
    from app.services.market_data import market_service
    from app.services.argaam_calendar import fetch_company_page
    from app.services.argaam_ids import snapshot as _snap
    from app.data.saudi_directory import SAUDI_DIRECTORY

    ids = (_snap().get("ids") or {})
    syms = [s for s, v in SAUDI_DIRECTORY.items()
            if v.get("sector") == "صناديق المؤشرات المتداولة"]
    rows = []
    for sym in sorted(syms):
        ysym = f"{sym}.SR"
        price = hist = None
        try:
            p = await market_service.get_price(ysym)
            price = (p or {}).get("price")
        except Exception as e:                                    # noqa: BLE001
            price = f"خطأ: {str(e)[:40]}"
        try:
            h = await market_service.get_history(ysym, "1mo")
            hist = len(h or [])
        except Exception:                                         # noqa: BLE001
            hist = None
        arg = None
        if sym in ids:
            try:
                got = await fetch_company_page(sym, ids[sym])
                arg = {"معرّف": ids[sym],
                       "صفوف_المفكرة": len(got.get("calendar") or [])}
            except Exception as e:                                # noqa: BLE001
                arg = {"معرّف": ids[sym], "خطأ": str(e)[:40]}
        rows.append({"الرمز": sym,
                     "الاسم": (SAUDI_DIRECTORY[sym] or {}).get("name"),
                     "سعر_ياهو": price, "نقاط_التاريخ": hist,
                     "أرقام": arg or "لا معرّف"})
    return success_response(data={
        "عدد": len(rows),
        "له_سعر": sum(1 for r in rows if isinstance(r["سعر_ياهو"], (int, float))),
        "الصفوف": rows,
    })


@router.get("/fair-value-coverage")
async def fair_value_coverage(scope: str = "portfolio", limit: int = 400,
                              db: AsyncSession = Depends(get_db)):
    """كم شركةً في المحفظة تُحسب لها قيمةٌ عادلة فعلاً — ولماذا تتعذّر البقية.

    سأل المالك: أهي أداةٌ يُبنى عليها قرار أم ديكور؟ والجواب الصادق يُقاس
    ولا يُقال: هذا المسار يمرّ على كل شركةٍ يملكها ويُخرج عدد المسارات
    المتاحة لكلٍّ وتاريخ أرقامها. فإن كانت التغطية ضعيفة عُرف ذلك بالرقم،
    ولم يُكتشف بعد قرارٍ بُني على فراغ.
    """
    from app.services.analysis import analyze_company
    from app.models.portfolio import Company, Holding
    import asyncio

    # ══ النطاق: المحفظة أم السوق كلّه ══ (بأمر المالك)
    # سأل: أجاهزٌ القرار لكل شركةٍ في السوق؟ وكان هذا المسار يقيس ما يملكه
    # وحده — فيُجيب عن سؤالٍ غير الذي سُئل. والقياس الذي لا يغطّي محلّ
    # السؤال لا يصلح جواباً عنه.
    if scope == "market":
        from app.data.market_universe import MARKET_UNIVERSE
        from app.api.v1.endpoints.holdings import yahoo_symbol
        from app.data.universe import main_market
        pairs = [(yahoo_symbol(sym), meta.get("name_ar") or sym)
                 for sym, meta in list(main_market(MARKET_UNIVERSE).items())[:limit]]
    else:
        pairs = (await db.execute(
            select(Company.symbol, Company.company_name)
            .join(Holding, Holding.company_id == Company.id).distinct()
        )).all()
    out = []
    for sym, name in pairs:
        try:
            # مسحُ السوق لا ينفق حصّة «سهمك» النادرة — ياهو وحده، كما في
            # محرّك الحوكمة. والتغطيةُ المقيسة هكذا هي التغطية الحقيقية
            # لمن يتصفّح السوق، لا تغطيةٌ مثالية لا تتحقّق إلا بحصّة.
            a = await analyze_company(sym, name, db=db,
                                      allow_supplement=(scope != "market"))
        except Exception as e:                                    # noqa: BLE001
            out.append({"symbol": sym, "خطأ": str(e)[:80]})
            continue
        fv = (a or {}).get("fair_value_detail") or {}
        out.append({
            "symbol": sym, "name": name,
            "القيمة_العادلة": fv.get("value"),
            "عدد_المسارات": len(fv.get("methods") or []),
            "المسارات": [m["name"] for m in (fv.get("methods") or [])],
            "الثقة": fv.get("confidence"),
            "تاريخ_الأرقام": fv.get("asof"),
            "عمرها_أياماً": fv.get("age_days"),
            "سبب_التعذّر": fv.get("unavailable_reason"),
        })
    have = [r for r in out if r.get("القيمة_العادلة") is not None]
    deep = [r for r in have if (r.get("عدد_المسارات") or 0) >= 2]
    return success_response(data={
        "النطاق": "السوق كلّه" if scope == "market" else "المحفظة",
        "الشركات": len(out),
        "لها_مساران_فأكثر": len(deep),
        "لها_قيمة_عادلة": len(have),
        "نسبة_التغطية": f"{len(have) / len(out) * 100:.0f}%" if out else "—",
        "متوسط_المسارات": (round(sum(r["عدد_المسارات"] for r in have) / len(have), 1)
                            if have else 0),
        "التفصيل": out,
    })


@router.get("/source-capability/{symbol}")
async def source_capability(symbol: str):
    """ما الذي يُعيده مفتاحُ «سهمك» فعلاً — يُقاس ولا يُفترض.

    سأل المالك أن أجلب المصادر الناقصة (كفاية رأس المال والقروض المتعثّرة
    للبنوك، والنسبة المجمّعة للتأمين، وFFO للريت) وأن أتأكّد إن كان مفتاحه
    يجلبها. ولا سبيل إلى الجزم من المختبر: لا مفتاح فيه ولا إنترنت.

    فهذا المسبار يطلب الحقول الخام من المصدر ويُخرج **أسماء ما وصل** بلا
    تفسير — فيُعرف بالقياس أيّ البنود متاح وأيّها ليس، ويُبنى عليه بدل
    التخمين. (وهو المبدأ نفسه الذي صحّح مسار أخبار «أرقام»: سبعةُ مرشّحين
    أعادوا 404 وواحدٌ نجح، ولم يُعرف ذلك إلا بالتجربة على الخادم.)
    """
    from app.core.config import settings
    out: dict = {
        "الرمز": symbol,
        "المفتاح مضبوط": bool(getattr(settings, "SAHMAK_API_KEY", None)),
        "الحقول الواصلة": {},
        "البنود المطلوبة": {},
    }
    if not out["المفتاح مضبوط"]:
        out["الخلاصة"] = "لا مفتاح مضبوط — لا يمكن قياس ما يعطيه المصدر."
        return success_response(data=out)

    from app.services import sahmak_library
    raw = await sahmak_library.fundamentals(symbol)
    if not isinstance(raw, dict) or not raw:
        # السببُ يُقرأ من المصدر لا يُخمَّن (انظر `sahmak_library.LAST`).
        from app.services.usage_tracker import usage
        last = dict(sahmak_library.LAST)
        out["ما قاله المصدر"] = last
        out["الحصّة"] = usage("sahmak")
        code = next((v.get("حالة") for v in last.values() if v.get("حالة")), None)
        out["الخلاصة"] = (
            "الخطّة لا تشمل القوائم المالية (‏403) — البنود الرقابية خارج "
            "نطاق القياس حتى تُرقّى الخطّة." if code == 403 else
            "الرمز غير مغطّى في هذه النقطة (‏404)." if code == 404 else
            "نفدت الحصّة اليومية — أعد المحاولة غداً."
            if any("الحصّة" in str(v.get("سبب", "")) for v in last.values()) else
            "لم يصل شيء — راجع «ما قاله المصدر» أعلاه.")
        return success_response(data=out)

    out["الحقول الواصلة"] = {k: (len(v) if isinstance(v, list) else type(v).__name__)
                             for k, v in raw.items()}
    # عيّنةٌ من أسماء البنود داخل كل قائمة — بها يُعرف ما يُشتقّ منها
    for k, v in raw.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out["البنود المطلوبة"][k] = sorted(v[0].keys())

    # البنود الرقابية التي نبحث عنها، ومرادفاتها المحتملة
    WANTED = {
        "كفاية رأس المال (CAR)": ("capital_adequacy", "car", "tier1", "capital_ratio"),
        "القروض المتعثّرة (NPL)": ("npl", "non_performing", "impaired_loans"),
        "هامش صافي الفائدة (NIM)": ("net_interest_margin", "nim", "interest_income"),
        "النسبة المجمّعة (Combined)": ("combined_ratio", "loss_ratio", "claims"),
        "الأموال من العمليات (FFO)": ("ffo", "funds_from_operations"),
    }
    flat = " ".join(sorted({k for v in raw.values() if isinstance(v, list)
                            for row in v if isinstance(row, dict) for k in row})).lower()
    out["البنود الرقابية"] = {
        label: ("متاح" if any(n in flat for n in names) else "غير متاح")
        for label, names in WANTED.items()
    }
    out["الخلاصة"] = ("وصلت القوائم. راجع «البنود الرقابية»: ما كان «متاح» "
                      "يُبنى عليه، وما سواه يبقى خارج نطاق القياس ويُعلَن.")
    return success_response(data=out)


@router.get("/ipo-sectors")
async def get_ipo_sectors():
    """قطاعاتُ السوق ومضاعفاتُها الوسيطة — مادّةُ حاسبة الاكتتاب (D231).

    من المخزن الدائم بلا نداءِ شبكةٍ واحد. وقطاعٌ نظائرُه دون الحدّ يُعاد
    مع سببِ امتناعه لا محجوباً: المستخدمُ يرى لماذا لا رقمَ لقطاعه.
    """
    from app.services.relative_value import MIN_PEERS, SectorTable
    from app.services.content_engine import fund_store_load
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR

    store = fund_store_load() or {}
    table = SectorTable(
        {"sector": SYMBOL_TO_SECTOR_AR.get(s), "pe": (v or {}).get("pe_ratio"),
         "pb": (v or {}).get("price_to_book")}
        for s, v in store.items())
    out = []
    for sec in sorted(set(table.pe) | set(table.pb)):
        t = table.for_sector(sec)
        pe, pb = t["pe"], t["pb"]
        out.append({
            "sector": sec,
            "pe_median": round(pe["median"], 2) if pe else None,
            "pe_q1": round(pe["q1"], 2) if pe else None,
            "pe_q3": round(pe["q3"], 2) if pe else None,
            "pe_peers": pe["n"] if pe else len(table.pe.get(sec, [])),
            "pb_median": round(pb["median"], 2) if pb else None,
            "pb_q1": round(pb["q1"], 2) if pb else None,
            "pb_q3": round(pb["q3"], 2) if pb else None,
            "pb_peers": pb["n"] if pb else len(table.pb.get(sec, [])),
            "why": None if (pe or pb) else f"نظائرُ القطاع دون {MIN_PEERS}",
        })
    return success_response(data=out)


@router.get("/ipo-value")
async def get_ipo_value(sector: str, net_profit: float, equity: float,
                        shares: float, offer_price: float | None = None):
    """تقييمٌ نسبيٌّ لشركةٍ تُطرح للاكتتاب — بالمحرّك نفسِه لا بمحرّكٍ ثانٍ.

    المدخلاتُ من نشرة الإصدار: صافي الربح · حقوقُ الملكية · عددُ الأسهم
    **بعد الطرح** — ومنها يُشتقّ مقياسا الشركة (ربحيةُ السهم ودفتريّتُه)،
    فتنزل إلى `value_from_metrics` كما تنزل الشركةُ المدرَجة.

    والشركةُ غيرُ المدرَجة ليست في عيّنة قطاعها، فلا يُنزَع لها مضاعف.
    وموضعُ سعر الطرح من النطاق يُعاد رقماً ولا يُترجَم حكمَ شراء.
    """
    from app.services.relative_value import SectorTable, value_from_metrics
    from app.services.content_engine import fund_store_load
    from app.data.company_sectors import SYMBOL_TO_SECTOR_AR

    if not shares or shares <= 0:
        raise HTTPException(400, "عددُ الأسهم بعد الطرح مطلوبٌ وموجب")
    store = fund_store_load() or {}
    table = SectorTable(
        {"sector": SYMBOL_TO_SECTOR_AR.get(s), "pe": (v or {}).get("pe_ratio"),
         "pb": (v or {}).get("price_to_book")}
        for s, v in store.items())
    eps = net_profit / shares
    bvps = equity / shares
    r = value_from_metrics(sector=sector, eps=eps, bvps=bvps, table=table)
    px = offer_price if isinstance(offer_price, (int, float)) and offer_price > 0 else None
    return success_response(data={
        "sector": sector, "eps": round(eps, 4), "bvps": round(bvps, 4),
        "value": round(r["value"], 2) if r["value"] is not None else None,
        "low": round(r["low"], 2) if r["low"] is not None else None,
        "high": round(r["high"], 2) if r["high"] is not None else None,
        "confidence": r["confidence"], "confidence_why": r.get("confidence_why") or [],
        "basis": r["basis"], "why": r["why"],
        "paths": {k: {"value": round(v["value"], 2), "low": round(v["low"], 2),
                      "high": round(v["high"], 2), "peers": v["peers"],
                      "spread": round(v["spread"], 3)}
                  for k, v in (r.get("paths") or {}).items()},
        "offer_price": px,
        # الفرقُ عن الوسيط، وموضعُ السعر من النطاق — رقمان لا حكم.
        "offer_gap_pct": (round((r["value"] - px) / px * 100, 1)
                          if px and r["value"] else None),
        "offer_in_range": (None if not (px and r["low"] is not None)
                           else r["low"] <= px <= r["high"]),
    })


@router.get("/relative-coverage")
async def get_relative_coverage():
    """تغطيةُ مُدخَل التقييم النسبيّ — كم شركةً لها مضاعفٌ مخزَّنٌ صالح (D233).

    المحرّكُ صار قراءةً دائمةً في التطبيق، فتغطيةُ مُدخَله رقمٌ يُراقَب لا
    يُفترَض. قياسٌ من المخزن بلا نداءٍ واحد، ويُعاد عددُ الناقصين لا
    قائمتُهم كاملةً حتى لا يصير المخرَجُ سجلّاً.
    """
    from app.services.content_engine import relative_inputs_coverage
    c = relative_inputs_coverage()
    return success_response(data={
        "universe": c["universe"], "covered": c["covered"],
        "missing": len(c["missing"]), "missing_sample": c["missing"][:20],
        "pct": round(c["covered"] / c["universe"] * 100, 1) if c["universe"] else None,
    })


@router.post("/relative-coverage/top-up", dependencies=[Depends(require_owner)])
async def top_up_relative_coverage():
    """يملأ مضاعفاتِ الناقصين فوراً (للمالك) — بدل انتظار مسحة الثالثة فجراً.

    يحترم احتياطيَ حصّةِ نهار العمل ويتوقّف عنده بهدوء، فلا يُجهض عرضاً
    جارياً لأجل تغذيةٍ يمكن أن تُكمل ليلاً.
    """
    from app.services.content_engine import (relative_inputs_coverage,
                                             top_up_relative_inputs)
    before = relative_inputs_coverage()
    filled = await top_up_relative_inputs()
    after = relative_inputs_coverage()
    return success_response(data={
        "filled": filled, "before": before["covered"],
        "after": after["covered"], "universe": after["universe"],
        "still_missing": len(after["missing"]),
    })


@router.get("/depth/{symbol}")
async def get_market_depth(symbol: str):
    """عمقُ السوق لشركةٍ — مستوًى واحدٌ من «تداول»، بزمنه (D272).

    ══ جُمع ولم يُعرَض ══
    طلب المالك عمقَ السوق لكلّ شركة، فقُرئ أفضلُ طلبٍ وعرضٍ بكمّيتيهما في
    لقطة مراقبة السوق (‏D262) — ثمّ **بقي في اللقطة بلا باب**: لا مسارَ
    يقرؤه ولا شاشةَ تعرضه. وقلتُ للمالك «المستوى الأوّل سُلّم»، وهذا خطأٌ
    مني: يُجمَع شيءٌ فيُحسَب مسلَّماً. والتسليمُ أن يصل العين.

    وثلاثةُ قيود:
      · **الزمنُ جزءٌ من الرقم**: لقطةٌ شائخةٌ لا تُعرَض عمقاً حاضراً —
        `snapshot()` يرفضها أصلاً، فيعود «غير متوفّر».
      · **مستوًى واحدٌ يُسمّى واحداً**: `levels: 1`. والعشرون تغذيةٌ
        مرخَّصةٌ لا تُوعَد قبل أن تُملَك.
      · **ولا يُملأ ناقصٌ**: طرفٌ بلا سعرٍ أو كمّيةٍ يغيب ولا يُصفَّر.
    """
    from app.services.tadawul_market import ensure_fresh, row_for, usable_rows

    ensure_fresh()                      # لحظيةٌ عند الطلب، بلا انتظار (D289)
    _rows, _live, _at = usable_rows()
    row = row_for(symbol)
    if not row:
        return success_response(
            data={"symbol": str(symbol), "levels": 0, "bids": [], "asks": [],
                  "available": False},
            message="عمقُ السوق غير متوفّر — لا لقطةَ حاضرةٌ لهذا الرمز.")

    def side(p, q) -> list[dict]:
        return ([{"price": row[p], "quantity": row[q]}]
                if row.get(p) is not None and row.get(q) is not None else [])

    bids, asks = side("bid", "bid_qty"), side("ask", "ask_qty")
    spread = (round(asks[0]["price"] - bids[0]["price"], 2)
              if bids and asks else None)
    return success_response(
        data={
            "symbol": str(symbol), "levels": 1 if (bids or asks) else 0,
            "bids": bids, "asks": asks, "spread": spread,
            "last": row.get("price"), "prev_close": row.get("prev_close"),
            "day_high": row.get("day_high"), "day_low": row.get("day_low"),
            "trades": row.get("trades"), "volume": row.get("volume"),
            "as_of": _at,
            "live": _live,
            "source": "تداول — مراقبة السوق",
            "available": bool(bids or asks),
            # وسعرُ الإغلاق لا يُقرأ لحظياً: الفرقُ يُقال في الشاشة (D285).
            "note": ("مستوًى واحد — وهو ما تنشره «تداول» مجّاناً" if _live
                     else "آخرُ إغلاقٍ مسجَّل — السوق مغلق"),
        },
        message="عمقُ السوق." if (bids or asks)
                else "عمقُ السوق غير متوفّر لهذا الرمز الآن.")


@router.get("/special-deals")
async def get_special_deals(symbol: str | None = None):
    """الصفقاتُ الخاصة — كلُّ السوق، أو لشركةٍ إن مُرِّر رمزُها (D273).

    ولا تُجلب في مسار الطلب: تُقرأ اللقطةُ المحفوظةُ فقط. الجلبُ في
    الجدولة — فلا ينتظر المالكُ شبكةً خارجيةً عند فتح شاشة.
    """
    from app.services.special_deals import for_symbol, reading

    rec = reading()
    if not rec:
        return success_response(
            data={"deals": [], "as_of": None, "available": False,
                  "source": "تداول — الصفقات الخاصة"},
            message="الصفقاتُ الخاصة غير متوفّرة الآن.")
    deals = for_symbol(symbol) if symbol else (rec.get("deals") or [])
    return success_response(
        data={"deals": deals, "as_of": rec.get("at"), "available": True,
              "count": len(deals), "source": "تداول — الصفقات الخاصة"},
        message="الصفقاتُ الخاصة.")

# ══ بثُّ الأسعار المباشر — دفعٌ لا سؤال ══ (D290)
@public_router.get("/stream")
async def market_stream():
    """مجرى أحداثٍ (SSE) يدفع كلَّ سعرٍ يتغيّر لحظةَ وصوله.

    **عامٌّ بلا مصادقة** وهذا مقصود: `EventSource` في المتصفّح لا يُرسل
    رؤوساً، وأسعارُ السوق ليست بيانات المالك — ولا يُبثّ منها حرفٌ يخصّ
    المحفظة. ولو رُبط بمصادقةٍ لوجب تمريرُ الرمز في العنوان، وذاك تسريبٌ
    للرمز في السجلّات لا حراسةٌ له.
    """
    from fastapi.responses import StreamingResponse

    from app.services.live_stream import stream
    return StreamingResponse(
        stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform",
                 "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"})     # لا تخزينَ وسيطاً في nginx
