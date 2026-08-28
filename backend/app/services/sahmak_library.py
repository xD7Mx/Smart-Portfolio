"""
Sahmak monthly data layer — company library, financial statements, and
official company website (used for verified company logos).

These datasets change slowly, so each is fetched at most once per 30 days
(LIBRARY_TTL) and served from cache in between: the whole month costs a
handful of Sahmak calls, leaving the daily quota for prices.

Confirmed against the official SDK source (github.com/sahmk-sa/sahmk-python,
`sahmk/client.py` + `sahmk/models.py`) — base URL, auth header, endpoint
paths, and every response field name below are the real contract, not a
guess. `/financials/{symbol}/` is a Starter+ plan endpoint; on a Free plan
it returns 403 and this degrades to an empty result (never fabricated).
"""

import httpx
from loguru import logger
from app.core.config import settings
from app.services import cache


def _base() -> str:
    return getattr(settings, "SAHMAK_BASE_URL", "https://app.sahmk.sa/api/v1").rstrip("/")


def _headers() -> dict:
    return {"X-API-Key": settings.SAHMAK_API_KEY, "Accept": "application/json"}


# آخرُ ما قاله المصدر — يُحفظ ليقرأه المسبار (لا يُستعمل في أي منطق).
LAST: dict = {}


async def _get(path: str, params: dict | None = None):
    """GET one confirmed path; returns the raw JSON body (no envelope — the
    SDK confirms responses are unwrapped, no `data` key) or None."""
    # ══ السببُ يُسجَّل ولا يُبتلع ══ (بأمر المالك: قياسٌ لا تخمين)
    # كان الفشلُ يعود `None` صامتاً، فلا يُفرَّق بين ثلاثة أسباب مختلفة
    # تماماً: خطّةٌ لا تشمل النقطة (‏403)، ورمزٌ غير مغطّى (‏404)،
    # وحصّةٌ نفدت (لا نداءَ أصلاً). ومسبارٌ لا يفصل بين الأسباب لا
    # يحسم شيئاً — وقد كلّف ذلك جولةَ تشخيصٍ يدويّة كاملة.
    if not settings.SAHMAK_API_KEY:
        LAST[path] = {"سبب": "لا مفتاح مضبوط"}
        return None
    from app.services.usage_tracker import can_call, record
    if not can_call("sahmak"):
        LAST[path] = {"سبب": "نفدت الحصّة اليومية — لم يقع نداء"}
        return None
    try:
        record("sahmak")
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(f"{_base()}{path}", params=params, headers=_headers())
            LAST[path] = {"حالة": r.status_code,
                          "نوع": r.headers.get("content-type", "")[:40],
                          "مقتطف": (r.text or "")[:200]}
            if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                return r.json()
            if r.status_code == 403:
                logger.info(f"Sahmak {path}: plan does not include this endpoint (403).")
    except Exception as e:
        LAST[path] = {"سبب": f"خطأ اتصال: {str(e)[:120]}"}
        logger.debug(f"Sahmak {path} failed: {e}")
    return None


async def company_library() -> list:
    """Full Saudi market directory from GET /companies/ (Free plan) —
    paginated, cached monthly. Each item: {symbol, name, name_en, market}."""
    ck = "sahmak:library"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    if not settings.SAHMAK_API_KEY:
        return []
    from app.services.usage_tracker import can_call, record

    out: list = []
    limit, offset = 200, 0
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for _ in range(20):  # hard cap: 20 pages × 200 = 4000 rows
                if not can_call("sahmak"):
                    break
                record("sahmak")
                r = await client.get(
                    f"{_base()}/companies/",
                    params={"limit": limit, "offset": offset},
                    headers=_headers(),
                )
                if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                    break
                payload = r.json()
                rows = payload.get("results", payload if isinstance(payload, list) else [])
                if not rows:
                    break
                for c in rows:
                    sym = str(c.get("symbol") or "").strip()
                    if not sym:
                        continue
                    out.append({
                        "symbol": sym,
                        "name": c.get("name") or c.get("name_en") or sym,
                        "name_en": c.get("name_en") or c.get("name") or sym,
                        "market": c.get("market") or "TASI",
                    })
                offset += limit
                total = payload.get("total") or payload.get("count")
                if total and offset >= int(total):
                    break
    except Exception as e:
        logger.warning(f"Sahmak company_library failed: {e}")

    if out:
        cache.set(ck, out, cache.LIBRARY_TTL)
    return out


async def company_profile(symbol: str) -> dict | None:
    """GET /company/{symbol}/ — confirmed fields (from sahmk/models.py Company):
    symbol, name, name_en, current_price, sector, industry, description,
    website, country, currency (+ fundamentals/technicals/valuation/analysts
    on paid plans). Cached monthly per symbol."""
    base = symbol.replace(".SR", "")
    ck = f"sahmak:profile:{base}"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    data = await _get(f"/company/{base}/")
    if isinstance(data, dict) and data:
        cache.set(ck, data, cache.LIBRARY_TTL)
        return data
    return None


async def company_logo_url(symbol: str) -> str | None:
    """Verified company logo via the official website Sahmak reports for
    this symbol (Company.website), resolved through Clearbit's free
    domain-to-logo service. Never guesses a domain — if Sahmak doesn't
    report a website for this symbol, no logo is returned (honest empty),
    matching the no-fake-data doctrine."""
    profile = await company_profile(symbol)
    website = (profile or {}).get("website")
    if not website:
        return None
    domain = website.strip()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.split("/")[0].removeprefix("www.").strip()
    if not domain or "." not in domain:
        return None
    return f"https://logo.clearbit.com/{domain}"


async def resolve_logo_wikipedia(name_en: str) -> str | None:
    """Second, independent free logo source when Sahmak/Clearbit has no
    website on file for this company: Wikipedia's own REST summary API
    (no key, no quota) returns the infobox thumbnail for a company's
    article when one exists — reliable for any large/mid-cap Tadawul name
    that has an English Wikipedia page (most do). Upgraded from the
    (often small) served thumbnail to a larger rendition via Wikipedia's
    own thumb-width URL convention. Cached a month like any other logo
    lookup; returns None (never a guess) if no matching article/image."""
    if not name_en:
        return None
    ck = f"wiki:logo:{name_en}"
    cached = cache.get(ck)
    if cached is not None:
        return cached or None
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{name_en.replace(' ', '_')}",
                headers={"User-Agent": "SmartPortfolio/1.0 (logo lookup)"},
            )
            if r.status_code != 200:
                cache.set(ck, "", cache.LIBRARY_TTL)
                return None
            data = r.json()
            thumb = (data.get("thumbnail") or {}).get("source") or (data.get("originalimage") or {}).get("source")
            if not thumb:
                cache.set(ck, "", cache.LIBRARY_TTL)
                return None
            # Wikipedia thumb URLs embed the requested width as a path
            # segment (".../thumb/.../200px-Foo.png") — bump it up for a
            # crisper icon than the ~160px default summary thumbnail.
            import re
            thumb = re.sub(r"/\d+px-", "/300px-", thumb)
            cache.set(ck, thumb, cache.LIBRARY_TTL)
            return thumb
    except Exception:
        return None


def _num(v):
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, dict):
        return v.get("raw") if isinstance(v.get("raw"), (int, float)) else None
    return None


async def fundamentals(symbol: str):
    """Financial statement data for one symbol — monthly per symbol.
    GET /financials/{symbol}/ (Starter+ plan) — returns None gracefully on
    a Free plan (403) rather than raising."""
    base = symbol.replace(".SR", "")
    ck = f"sahmak:fund:{base}"
    cached = cache.get(ck)
    if cached is not None:
        return cached
    # history=3y explicitly requests the deepest annual depth the plan
    # allows (confirmed SDK param), so older years are supplied whenever
    # the plan supports it rather than only whatever the default returns.
    data = await _get(f"/financials/{base}/", params={"history": "3y", "period": "annual"})
    if isinstance(data, dict) and data:
        cache.set(ck, data, cache.LIBRARY_TTL)
        return data
    return None


def _year_of(report_date: str | None) -> int | None:
    if not report_date:
        return None
    try:
        return int(str(report_date)[:4])
    except (TypeError, ValueError):
        return None


async def financial_periods(symbol: str) -> list:
    """Annual statement rows in our internal shape (year/revenue/net_income/
    equity/debt_ratio/operating_cash_flow), used to fill in years Yahoo's
    quoteSummary doesn't cover for this symbol.

    Parses the CONFIRMED FinancialsResponse shape from the official SDK:
      income_statements[]:  {report_date, total_revenue, gross_profit, operating_income, net_income}
      balance_sheets[]:     {report_date, total_assets, total_liabilities, stockholders_equity, total_debt}
      cash_flows[]:         {report_date, operating_cash_flow, investing_cash_flow, financing_cash_flow, free_cash_flow}
    Merged by year (report_date's year) into one row per year."""
    raw = await fundamentals(symbol)
    if not isinstance(raw, dict):
        return []

    by_year: dict[int, dict] = {}

    for stmt in raw.get("income_statements", []) or []:
        year = _year_of(stmt.get("report_date"))
        if not year:
            continue
        row = by_year.setdefault(year, {"year": year})
        row["revenue"] = _num(stmt.get("total_revenue"))
        row["net_income"] = _num(stmt.get("net_income"))
        # Fuller income-statement lines — enable Piotroski's gross-margin
        # trend and Altman/Greenblatt EBIT across ALL years, not just Yahoo's.
        row["gross_profit"] = _num(stmt.get("gross_profit"))
        row["operating_income"] = _num(stmt.get("operating_income"))
        row["cost_of_revenue"] = _num(stmt.get("cost_of_revenue"))

    for stmt in raw.get("balance_sheets", []) or []:
        year = _year_of(stmt.get("report_date"))
        if not year:
            continue
        row = by_year.setdefault(year, {"year": year})
        equity = _num(stmt.get("stockholders_equity"))
        total_liab = _num(stmt.get("total_liabilities"))
        total_assets = _num(stmt.get("total_assets"))
        row["equity"] = equity
        row["total_assets"] = total_assets
        row["total_liabilities"] = total_liab
        row["total_debt"] = _num(stmt.get("total_debt"))
        row["debt_ratio"] = round(total_liab / total_assets, 2) if total_liab and total_assets else None
        # Working-capital lines — the missing piece for Altman Z (tried under
        # a few common key names; None-safe when the source omits them).
        row["current_assets"] = _num(stmt.get("total_current_assets") or stmt.get("current_assets"))
        row["current_liabilities"] = _num(stmt.get("total_current_liabilities") or stmt.get("current_liabilities"))
        row["inventory"] = _num(stmt.get("inventory"))

    for stmt in raw.get("cash_flows", []) or []:
        year = _year_of(stmt.get("report_date"))
        if not year:
            continue
        row = by_year.setdefault(year, {"year": year})
        row["operating_cash_flow"] = _num(stmt.get("operating_cash_flow"))
        row["free_cash_flow"] = _num(stmt.get("free_cash_flow"))
        row["capex"] = _num(stmt.get("capital_expenditures") or stmt.get("capex"))

    out = list(by_year.values())
    out.sort(key=lambda r: r["year"])
    return out
