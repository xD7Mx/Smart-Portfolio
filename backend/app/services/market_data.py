"""
Market Data Integration Layer — Smart Portfolio
==================================================
Adapter pattern: isolates external providers from the rest of the system.
Provider can be swapped from Settings without touching any other code.

Supported providers:
- Yahoo Finance (primary)
- Sahmak (secondary / Saudi market)
"""

from typing import Optional, List
import yfinance as yf
import httpx
from loguru import logger
from app.core.config import settings


# ─── Unified Price Model ──────────────────────────────────────

class PriceData:
    def __init__(self, symbol: str, price: float, change: float, change_pct: float, volume: float = 0,
                 day_low: float | None = None, day_high: float | None = None,
                 prev_close: float | None = None):
        self.symbol = symbol
        self.price = price
        self.change = change
        self.change_pct = change_pct
        self.volume = volume
        self.day_low = day_low
        self.day_high = day_high
        # الإغلاق السابق: `None` تعني أن المزوّد لم يُرسله — لا أنه صفر.
        # وعليه يتوقّف معنى `change_pct`: بلا إغلاقٍ سابق لا تغيّرَ يُقاس.
        self.prev_close = prev_close

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "day_low": self.day_low,
            "day_high": self.day_high,
            "prev_close": self.prev_close,
        }


def _set_book_value(p: dict) -> None:
    """القيمة الدفترية للسهم = حقوق الملكية ÷ عدد الأسهم.

    وهي **للسهم** لا للشركة عن قصد: حقوق الملكية معروضةٌ أصلاً في الجدول،
    فتكرارها باسمٍ آخر لا يضيف شيئاً. والقيمة الدفترية للسهم هي التي تُقارَن
    بالسعر مباشرةً — وهي المعنى المتداول للمصطلح في تداول.

    ولا تُحسب إلا من سطرين حقيقيين في القائمة نفسها. غياب أحدهما يترك الخانة
    فارغة تُقرأ «—»؛ ولا يُستعاض عنه بعدد الأسهم الحاليّ لأن ذلك يقيس سنةً
    قديمة بمقامٍ من اليوم فيُنتج رقماً لا يخصّ أيّ سنة.
    """
    if p.get("book_value") is not None:
        return  # سطرٌ مُبلَّغ من المصدر — لا يُداس باشتقاق
    eq, sh = p.get("equity"), p.get("shares_outstanding")
    p["book_value"] = round(eq / sh, 2) if eq is not None and sh else None


def _needs_supplement(periods: list[dict]) -> bool:
    """Should we spend a scarce Sahmak call on this symbol? With the new
    Tadawul panel (Buffett quality / Lynch PEG / analyst consensus / ROE /
    payout) every input comes from Yahoo — so Yahoo is the primary source and
    Sahmak is a fallback ONLY for depth: fewer than 3 years (the CAGR / PEG /
    consistency frameworks need history). The old working-capital trigger is
    gone: Altman's Z-Score / liquidity ratios are no longer decision inputs,
    so a missing current-assets line no longer justifies burning quota. This
    sharply cuts Sahmak usage against the 100/day cap."""
    return not periods or len(periods) < 3


def _merge_supplement(target: list[dict], extra: list[dict]) -> None:
    """Field-level merge of a supplement source (Sahmak) into `target`
    (Yahoo) IN PLACE — Phase B. Two effects:
      1. a year the target lacks entirely is appended (as before), and
      2. a field the target has as None in a year the source DOES report is
         filled from the source — so a company Yahoo left with blank gross
         profit / operating income / working-capital lines still gets a full
         multi-year picture, and Altman / Piotroski-trend stop abstaining.
    Never overwrites a real Yahoo value; only fills genuine gaps. Fields
    filled from the supplement are tracked per period under `_supplemented`."""
    by_year = {p["year"]: p for p in target if p.get("year")}
    for e in extra or []:
        yr = e.get("year")
        if not yr:
            continue
        if yr not in by_year:
            e.setdefault("source", "sahmak")
            target.append(e)
            by_year[yr] = e
            continue
        row = by_year[yr]
        for k, v in e.items():
            if k in ("year", "source") or v is None:
                continue
            if row.get(k) is None:
                row[k] = v
                row.setdefault("_supplemented", []).append(k)


# ─── Yahoo Finance Adapter ────────────────────────────────────

def _persist_valuation(symbol: str, data: dict) -> None:
    """حفظ حقول التقييم في مخزن الأساسيات الدائم (`market:fundamentals`).

    الرمز يُخزَّن مجرّداً من اللاحقة (`2222` لا `2222.SR`) — بنفس مفتاح مخزن
    التوزيعات، وإلا ظهر للشركة الواحدة سجلّان لا يجد الفرز أحدهما."""
    from datetime import datetime, timezone
    keep = {k: data.get(k) for k in
            ("target_mean_price", "pe_ratio", "price_to_book", "roe", "book_value")
            if data.get(k) is not None}
    if not keep:
        return
    from app.services.content_engine import _fund_store_put
    keep["val_asof"] = datetime.now(timezone.utc).date().isoformat()
    _fund_store_put(symbol.split(".")[0], keep)


class YahooFinanceAdapter:
    """
    Wraps yfinance to provide a consistent interface.
    """
    name = "yahoo_finance"

    async def get_price(self, symbol: str) -> Optional[PriceData]:
        from app.services.usage_tracker import record, can_call
        from app.services import cache

        # Serve from cache if fetched within the last 15 min — no provider call at all.
        ck = f"price:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached

        if not can_call("yahoo"):
            logger.warning("Yahoo: daily quota reached — skipping call to stay within free tier.")
            return None
        try:
            record("yahoo")
            # Direct call to Yahoo's public chart API — far more reliable than the
            # yfinance library. Falls back to query2 when query1 rate-limits (429).
            result = None
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                for host in ("query1", "query2"):
                    try:
                        r = await client.get(
                            f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
                        )
                        if r.status_code == 200:
                            result = r.json().get("chart", {}).get("result")
                            if result:
                                break
                    except Exception:
                        continue
            if not result:
                return None
            meta = result[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            if price is None:
                return None
            price = float(price)
            # ══ صفرٌ مختلَق ══
            # كان الإغلاق السابق الغائب يُستبدل بالسعر نفسه، فيخرج التغيّر
            # صفراً — أي أن التطبيق **يؤكّد أن السهم لم يتحرّك** وهو لا يعلم.
            # والفرق ظاهرٌ للمالك: مؤشّرٌ صاعد يُعرض محايداً بلا سبب.
            # فيُحفظ الغياب كما هو (`prev_close = None`)، ويبقى `change_pct`
            # صفراً للتوافق مع ما يقرؤه بقيّة التطبيق حسابياً — ومن أراد
            # الصدق قرأ `prev_close` وعرف أن الصفر لا مرجع له.
            had_prev = prev is not None
            prev = float(prev) if prev else price
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0
            day_low = meta.get("regularMarketDayLow")
            day_high = meta.get("regularMarketDayHigh")
            volume = meta.get("regularMarketVolume")
            data = PriceData(symbol, price, change, change_pct,
                              volume=float(volume) if volume is not None else 0,
                              day_low=float(day_low) if day_low is not None else None,
                              day_high=float(day_high) if day_high is not None else None,
                              prev_close=prev if had_prev else None)
            cache.set(ck, data, cache.PRICE_TTL)
            return data
        except Exception as e:
            logger.warning(f"YahooFinance: failed for {symbol}: {e}")
            return None

    async def get_prices(self, symbols: List[str]) -> dict:
        """Concurrent batch quotes (bounded) — sequential fetching of a whole-
        market list (≈400 symbols × ~0.5-1s each) took MINUTES, longer than
        the frontend's 30s request timeout, which is why the market scan
        could never complete inline. 15 at a time finishes the full Tadawul
        in ~15-25s while staying gentle on Yahoo."""
        import asyncio
        sem = asyncio.Semaphore(15)

        async def one(symbol: str):
            async with sem:
                data = await self.get_price(symbol)
                return symbol, (data.to_dict() if data else None)

        pairs = await asyncio.gather(*(one(s) for s in symbols))
        return {s: d for s, d in pairs if d}

    async def _fetch_chart_points(self, symbol: str, range_: str, interval: str) -> list:
        """One raw chart request → deduped, sorted OHLC points. Never raises —
        returns [] on any failure so the caller can try a coarser interval."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        result = None
        try:
            async with httpx.AsyncClient(timeout=12, headers=headers) as client:
                for host in ("query1", "query2"):
                    try:
                        r = await client.get(
                            f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval={interval}"
                        )
                        if r.status_code == 200:
                            result = r.json().get("chart", {}).get("result")
                            if result:
                                break
                    except Exception:
                        continue
        except Exception:
            return []
        if not result:
            return []
        res = result[0]
        ts = res.get("timestamp") or []
        q = (res.get("indicators", {}).get("quote") or [{}])[0]
        closes = q.get("close") or []
        opens = q.get("open") or []
        highs = q.get("high") or []
        lows = q.get("low") or []
        vols = q.get("volume") or []
        from datetime import datetime, timezone
        def g(arr, i):
            v = arr[i] if i < len(arr) else None
            return round(float(v), 3) if v is not None else None
        by_date: dict = {}
        for i, t in enumerate(ts):
            c = g(closes, i)
            if c is None:
                continue
            date = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
            # Some symbols (notably indices) occasionally repeat a timestamp
            # for a given interval — keep only the first bar per date so the
            # chart library never sees duplicate/out-of-order times (which
            # collapses the whole series down to a single visible candle).
            if date in by_date:
                continue
            by_date[date] = {
                "date": date,
                "time": int(t),
                "open": g(opens, i) if g(opens, i) is not None else c,
                "high": g(highs, i) if g(highs, i) is not None else c,
                "low": g(lows, i) if g(lows, i) is not None else c,
                "close": c,
                "volume": int(vols[i]) if i < len(vols) and vols[i] is not None else 0,
            }
        return sorted(by_date.values(), key=lambda p: p["time"])

    async def get_history(self, symbol: str, range_: str = "3mo") -> Optional[list]:
        """Daily close history for charts — cached 24h (one provider call per
        symbol per day at most)."""
        from app.services.usage_tracker import record, can_call
        from app.services import cache
        ck = f"hist:yahoo:{symbol}:{range_}:v4"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None
        record("yahoo")
        # Daily bars can come back mostly null/duplicated for some tickers
        # (notably indices like ^TASI.SR) — same reason the real Yahoo
        # Finance UI itself switches to a coarser interval for long windows.
        # Try progressively coarser intervals until one actually yields a
        # usable number of real bars, instead of silently showing one
        # giant candle with an empty gap.
        default_interval = "1wk" if range_ in ("2y", "5y") else "1mo" if range_ in ("10y", "max") else "1d"
        candidates = {"1d": ["1d", "1wk", "1mo"], "1wk": ["1wk", "1mo"], "1mo": ["1mo"]}[default_interval]
        points: list = []
        for interval in candidates:
            points = await self._fetch_chart_points(symbol, range_, interval)
            if len(points) >= 5:
                break
        # Some symbols (confirmed live for ^TASI.SR) only ever have a single
        # day of history on Yahoo's free chart API across every range and
        # interval — a real data-availability limit, not something a coarser
        # interval can fix. One candle would be misleading, so treat it the
        # same as "no history" and let the UI say so honestly.
        if len(points) < 2:
            return None
        cache.set(ck, points, cache.HISTORY_TTL)
        return points

    # Yahoo quoteSummary now needs a cookie + crumb pair; we fetch it once and
    # reuse it (cached ~1h). This unlocks the full fundamentals + statements.
    async def _crumb(self):
        from app.services import cache
        c = cache.get("yahoo:crumb")
        if c is not None:
            return c
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
                await client.get("https://fc.yahoo.com")  # sets consent cookies
                r = await client.get("https://query2.finance.yahoo.com/v1/test/getcrumb")
                if r.status_code == 200 and r.text and "<" not in r.text:
                    pair = (r.text.strip(), dict(client.cookies))
                    cache.set("yahoo:crumb", pair, 60 * 60)
                    return pair
        except Exception as e:
            logger.debug(f"Yahoo crumb fetch failed: {e}")
        return None

    async def _quote_summary(self, symbol: str, modules: str):
        """Raw quoteSummary result dict for the given modules (query1→query2)."""
        crumb = await self._crumb()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        cookies = crumb[1] if crumb else {}
        params = f"modules={modules}&formatted=false"
        if crumb:
            params += f"&crumb={crumb[0]}"
        async with httpx.AsyncClient(timeout=14, headers=headers, cookies=cookies, follow_redirects=True) as client:
            for host in ("query1", "query2"):
                try:
                    r = await client.get(
                        f"https://{host}.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?{params}"
                    )
                    if r.status_code == 200:
                        result = (r.json().get("quoteSummary", {}).get("result") or [None])[0]
                        if result:
                            return result
                except Exception:
                    continue
        return None

    async def get_asset_profile(self, symbol: str) -> Optional[dict]:
        """نبذة النشاط + الإدارة التنفيذية من وحدة assetProfile.

        تحذير توثيقي مهمّ: companyOfficers هي **الإدارة التنفيذية** (رئيس
        تنفيذي · مالي · تشغيل) وليست **مجلس الإدارة** — وهما جهتان مختلفتان
        نظاماً. Yahoo لا يُوفّر تشكيل المجالس، وتداول تنشره في الإفصاحات بلا
        واجهة برمجية. فأي عرضٍ لهؤلاء يجب أن يُسمّى «الإدارة التنفيذية» بصدق،
        وأعضاء المجلس مصدرهم إدخال المالك وحده.

        النبذة إنجليزية من هذا المصدر — تُترجَم في طبقةٍ أعلى وتُوسَم بذلك.
        الحقول مخزَّنة شهرياً: بيانات لا تتغيّر إلا نادراً."""
        from app.services import cache
        from app.services.usage_tracker import record, can_call
        # تطبيع الرمز هنا لا عند المُنادي: رموز تداول أرقامٌ مجرّدة (1120) وYahoo
        # يعرفها بلاحقة السوق (1120.SR). كان المُنادي يمرّر الرمز خاماً فيردّ
        # Yahoo لا شيء، فتظهر «نبذة عن الشركة» فارغةً أبداً لكل شركة سعودية —
        # ويُقرأ ذلك كأن Yahoo لا يوفّر البيانات، وهو يوفّرها.
        s = (symbol or "").strip().upper()
        if s.isdigit():
            s = f"{s}.SR"
        symbol = s
        ck = f"profile:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None
        record("yahoo")
        try:
            result = await self._quote_summary(symbol, "assetProfile")
            ap = (result or {}).get("assetProfile") or {}
            if not ap:
                return None
            officers = []
            for o in (ap.get("companyOfficers") or []):
                name = (o.get("name") or "").strip()
                if not name:
                    continue
                officers.append({"name": name, "title": (o.get("title") or "").strip()})
            out = {
                "summary_en": (ap.get("longBusinessSummary") or "").strip() or None,
                "website": (ap.get("website") or "").strip() or None,
                "industry": (ap.get("industry") or "").strip() or None,
                "employees": ap.get("fullTimeEmployees"),
                # الإدارة التنفيذية — لا مجلس الإدارة. الاسم صريح كي لا يُخلطا.
                "executives": officers,
            }
            if any(v for v in out.values()):
                cache.set(ck, out, 30 * 24 * 60 * 60)
                return out
        except Exception as e:
            logger.warning(f"assetProfile failed for {symbol}: {e}")
        return None

    async def get_dividends(self, symbol: str) -> Optional[dict]:
        """Dividend history (up to 10y) + inferred frequency + next ex/pay date.
        Cached 24h."""
        from app.services import cache
        from app.services.usage_tracker import record, can_call
        ck = f"div:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None
        from datetime import datetime, timezone
        history = []
        try:
            record("yahoo")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
                res = None
                for host in ("query1", "query2"):
                    try:
                        r = await client.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}?range=10y&interval=1mo&events=div")
                        if r.status_code == 200:
                            res = (r.json().get("chart", {}).get("result") or [None])[0]
                            if res:
                                break
                    except Exception:
                        continue
            if res:
                divs = (res.get("events", {}) or {}).get("dividends", {}) or {}
                for _, d in divs.items():
                    ts = d.get("date"); amt = d.get("amount")
                    if ts and amt:
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        history.append({"date": dt.date().isoformat(), "year": dt.year, "amount": round(float(amt), 4)})
                history.sort(key=lambda x: x["date"])
        except Exception as e:
            logger.warning(f"Yahoo dividends failed for {symbol}: {e}")

        # frequency + next dates from quoteSummary
        ex_date = pay_date = None
        try:
            sq = await self._quote_summary(symbol, "summaryDetail,calendarEvents")
            if sq:
                sd = sq.get("summaryDetail", {})
                ce = sq.get("calendarEvents", {})
                def dt(v):
                    if isinstance(v, dict):
                        v = v.get("raw")
                    if isinstance(v, (int, float)):
                        return datetime.fromtimestamp(v, tz=timezone.utc).date().isoformat()
                    return None
                ex_date = dt(sd.get("exDividendDate"))
                pay_date = dt(ce.get("dividendDate"))
        except Exception:
            pass

        # infer frequency from per-year counts over the last 5 years
        from collections import Counter
        recent_years = [h["year"] for h in history if h["year"] >= (datetime.now().year - 5)]
        per_year = Counter(recent_years)
        counts = sorted(per_year.values())
        freq = None
        if counts:
            med = counts[len(counts) // 2]
            freq = {4: "ربع سنوي", 2: "نصف سنوي", 1: "سنوي", 3: "ثلاث مرات سنوياً"}.get(med, "غير منتظم")

        out = {"symbol": symbol, "history": history[-40:], "frequency": freq,
               "ex_date": ex_date, "pay_date": pay_date}
        if history or ex_date:
            cache.set(ck, out, 24 * 60 * 60)
        return out

    async def get_earnings_dates(self, symbol: str) -> Optional[dict]:
        """التاريخ القادم لإعلان النتائج المالية (Yahoo calendarEvents.earnings)
        — تاريخ مُهيكل مسبق التحديد، وهو تصنيف أساسي في مفكرة أرقام المدفوعة.
        مجاني، مُخزَّن ٢٤ساعة، ومحكوم بحصّة ياهو (يُعيد None عند نفادها)."""
        from app.services import cache
        from app.services.usage_tracker import record, can_call
        from datetime import datetime, timezone
        ck = f"earn:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None
        record("yahoo")
        try:
            sq = await self._quote_summary(symbol, "calendarEvents")
        except Exception as e:
            logger.warning(f"Yahoo earnings failed for {symbol}: {e}")
            return None
        if not sq:
            return None
        ce = (sq.get("calendarEvents") or {}).get("earnings") or {}
        raw_dates = ce.get("earningsDate") or []
        def dt(v):
            if isinstance(v, dict):
                v = v.get("raw")
            if isinstance(v, (int, float)):
                return datetime.fromtimestamp(v, tz=timezone.utc).date().isoformat()
            return None
        dates = sorted({d for d in (dt(x) for x in raw_dates) if d})
        if not dates:
            return None
        today = datetime.now(timezone.utc).date().isoformat()
        next_date = next((d for d in dates if d >= today), dates[-1])
        # **مؤكَّدٌ أم متوقَّع؟** المصدر يقولها صراحةً في `isEarningsDateEstimate`،
        # وكنّا نقرأ التاريخ ونرمي وصفه — فتُعرض المواعيد كلّها في المفكرة
        # بوصف «المتوقّع» ولو كانت مُعلَنةً رسميّاً. وهذا ما شكا منه المالك:
        # مفكرةٌ تقول توقّعات وهو يريد إعلانات. الوصف يُحفظ الآن ويُعرض كما هو.
        est = ce.get("isEarningsDateEstimate")
        # وموعد مكالمة النتائج — إعلانٌ رسميّ آخر يستحقّ الظهور.
        call_raw = ce.get("earningsCallDate") or []
        call_dates = sorted({d for d in (dt(x) for x in call_raw) if d})
        next_call = next((d for d in call_dates if d >= today), None)
        out = {"symbol": symbol, "next_date": next_date, "dates": dates,
               "is_estimate": bool(est) if est is not None else None,
               "next_call": next_call}
        cache.set(ck, out, 24 * 60 * 60)
        return out

    async def get_company_info(self, symbol: str) -> Optional[dict]:
        from app.services import cache
        from app.services.usage_tracker import record, can_call
        # Fundamentals barely change — cached for 30 days, so this hits the provider
        # at most once a month per company (matches how often the data actually updates).
        ck = f"fund:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None

        def _num(d, *path):
            cur = d
            for p in path:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(p)
            if isinstance(cur, dict):
                cur = cur.get("raw")
            return cur if isinstance(cur, (int, float)) else None

        try:
            record("yahoo")
            modules = ("financialData,defaultKeyStatistics,summaryDetail,price,"
                       "assetProfile,earnings")
            res = await self._quote_summary(symbol, modules)
            data = None
            if res:
                fd = res.get("financialData", {})
                ks = res.get("defaultKeyStatistics", {})
                sd = res.get("summaryDetail", {})
                pr = res.get("price", {})
                ap = res.get("assetProfile", {})
                pct = lambda v: round(v * 100, 2) if isinstance(v, (int, float)) else None
                data = {
                    "symbol": symbol,
                    "name": pr.get("longName") or pr.get("shortName"),
                    "sector": ap.get("sector"),
                    "industry": ap.get("industry"),
                    "market_cap": _num(pr, "marketCap") or _num(sd, "marketCap"),
                    "revenue": _num(fd, "totalRevenue"),
                    "net_income": _num(ks, "netIncomeToCommon"),
                    "ebitda": _num(fd, "ebitda"),
                    "eps": _num(ks, "trailingEps"),
                    "forward_eps": _num(ks, "forwardEps"),
                    "book_value": _num(ks, "bookValue"),
                    "price_to_book": _num(ks, "priceToBook"),
                    "operating_cash_flow": _num(fd, "operatingCashflow"),
                    "free_cash_flow": _num(fd, "freeCashflow"),
                    "total_cash": _num(fd, "totalCash"),
                    "total_debt": _num(fd, "totalDebt"),
                    "debt_to_equity": _num(fd, "debtToEquity"),
                    "current_ratio": _num(fd, "currentRatio"),
                    "quick_ratio": _num(fd, "quickRatio"),
                    "gross_margin": pct(_num(fd, "grossMargins")),
                    "operating_margin": pct(_num(fd, "operatingMargins")),
                    "profit_margin": pct(_num(fd, "profitMargins")),
                    "roe": pct(_num(fd, "returnOnEquity")),
                    "roa": pct(_num(fd, "returnOnAssets")),
                    "revenue_growth": pct(_num(fd, "revenueGrowth")),
                    "earnings_growth": pct(_num(fd, "earningsGrowth")),
                    "pe_ratio": _num(sd, "trailingPE"),
                    "forward_pe": _num(sd, "forwardPE"),
                    "peg_ratio": _num(ks, "pegRatio"),
                    "ev_to_ebitda": _num(ks, "enterpriseToEbitda"),
                    "dividend_yield": pct(_num(sd, "dividendYield")),
                    "dividend_per_share": _num(sd, "dividendRate"),
                    "payout_ratio": pct(_num(sd, "payoutRatio")),
                    "beta": _num(sd, "beta"),
                    "week52_low": _num(sd, "fiftyTwoWeekLow"),
                    "week52_high": _num(sd, "fiftyTwoWeekHigh"),
                    "avg_volume": _num(sd, "averageVolume") or _num(sd, "averageDailyVolume3Month"),
                    "target_mean_price": _num(fd, "targetMeanPrice"),
                    "recommendation": fd.get("recommendationKey"),
                    "current_price": _num(fd, "currentPrice"),
                }

            # Fallback to yfinance if quoteSummary was blocked.
            if not data or not data.get("name"):
                def _fetch():
                    info = yf.Ticker(symbol).info
                    pctm = lambda k: round(info.get(k, 0) * 100, 2) if info.get(k) else None
                    return {
                        "symbol": symbol, "name": info.get("longName") or info.get("shortName"),
                        "sector": info.get("sector"), "industry": info.get("industry"),
                        "market_cap": info.get("marketCap"), "revenue": info.get("totalRevenue"),
                        "net_income": info.get("netIncomeToCommon"), "ebitda": info.get("ebitda"),
                        "eps": info.get("trailingEps"), "forward_eps": info.get("forwardEps"),
                        "book_value": info.get("bookValue"), "price_to_book": info.get("priceToBook"),
                        "operating_cash_flow": info.get("operatingCashflow"),
                        "free_cash_flow": info.get("freeCashflow"),
                        "total_cash": info.get("totalCash"), "total_debt": info.get("totalDebt"),
                        "debt_to_equity": info.get("debtToEquity"),
                        "current_ratio": info.get("currentRatio"), "quick_ratio": info.get("quickRatio"),
                        "gross_margin": pctm("grossMargins"), "operating_margin": pctm("operatingMargins"),
                        "profit_margin": pctm("profitMargins"), "roe": pctm("returnOnEquity"),
                        "roa": pctm("returnOnAssets"), "revenue_growth": pctm("revenueGrowth"),
                        "earnings_growth": pctm("earningsGrowth"), "pe_ratio": info.get("trailingPE"),
                        "forward_pe": info.get("forwardPE"),
                        "peg_ratio": info.get("pegRatio"), "ev_to_ebitda": info.get("enterpriseToEbitda"),
                        "dividend_yield": pctm("dividendYield"),
                        "dividend_per_share": info.get("dividendRate"), "payout_ratio": pctm("payoutRatio"),
                        "beta": info.get("beta"), "week52_low": info.get("fiftyTwoWeekLow"),
                        "week52_high": info.get("fiftyTwoWeekHigh"),
                        "avg_volume": info.get("averageVolume"),
                        "target_mean_price": info.get("targetMeanPrice"),
                        "recommendation": info.get("recommendationKey"),
                        "current_price": info.get("currentPrice"),
                    }
                import asyncio
                data = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=12)

            if data and data.get("name"):
                cache.set(ck, data, cache.FUNDAMENTALS_TTL)
                # تثبيت حقول التقييم في المخزن الدائم — بلا أي نداء إضافي:
                # هذه الجلبة وقعت لسببٍ آخر أصلاً (صفحة شركة، حوكمة، مسحة
                # ليلية)، ونحن نلتقط ثمرتها في الطريق. وبدون التثبيت تضيع بعد
                # ٣٠ يوماً فلا تكتمل تغطية «فرز الأسهم» أبداً — وهي العلّة
                # نفسها التي عولجت سابقاً في توزيعات السهم.
                try:
                    _persist_valuation(symbol, data)
                except Exception:
                    pass
                return data
        except Exception as e:
            logger.warning(f"YahooFinance company info failed for {symbol}: {e}")
        return None

    # Real endpoint (used internally by Yahoo's own site and by yfinance for
    # multi-year statements) that carries much deeper annual history than the
    # quoteSummary "incomeStatementHistory" module, which Yahoo has trimmed to
    # 1-2 periods for most Tadawul tickers. Each "type" comes back as its own
    # item in the result list; merged here by asOfDate (year).
    async def _fundamentals_timeseries(self, symbol: str, years: int = 4,
                                       freq: str = "annual") -> list:
        """قوائمُ مالية من مصدر ياهو الزمنيّ — سنويةً أو ربعية.

        ‏`freq`: «annual» أو «quarterly». والمصدر نفسه يقدّم الاثنين بأسماء
        حقولٍ تختلف في البادئة وحدها (‏annualTotalRevenue ↔
        quarterlyTotalRevenue)، فبُدِّلت البادئة ولم يُكتب مسارٌ ثانٍ —
        مساران لمصدرٍ واحد يفترقان يوماً ما.
        والفرق الجوهريّ في المفتاح: السنويّ يُفهرَس بالسنة، والربعيّ لا
        يصحّ فهرسته بها (أربعةُ صفوفٍ تدهس بعضها). فالمفتاح هو تاريخ
        القياس كاملاً، ويُسمّى الصفُّ باسمه الربعيّ (‏2026 ر٢).
        """
        import time
        quarterly = freq == "quarterly"
        pfx = "quarterly" if quarterly else "annual"
        types = [
            f"{pfx}TotalRevenue", f"{pfx}NetIncomeCommonStockholders", f"{pfx}NetIncome",
            f"{pfx}DilutedEPS", f"{pfx}BasicEPS",
            f"{pfx}StockholdersEquity", f"{pfx}TotalLiabilitiesNetMinorityInterest", f"{pfx}TotalAssets",
            f"{pfx}OperatingCashFlow", f"{pfx}CashAndCashEquivalents", f"{pfx}EndCashPosition",
            f"{pfx}CapitalExpenditure", f"{pfx}FreeCashFlow",
            f"{pfx}EBIT", f"{pfx}InterestExpense",
            # Added for the Financial Feature Engine (governance redesign) — margins,
            # liquidity ratios, dilution and dividend-growth all need these raw lines.
            f"{pfx}GrossProfit", f"{pfx}OperatingIncome", f"{pfx}CostOfRevenue",
            f"{pfx}CurrentAssets", f"{pfx}CurrentLiabilities", f"{pfx}Inventory",
            f"{pfx}TotalDebt", f"{pfx}CashDividendsPaid",
            f"{pfx}DilutedAverageShares", f"{pfx}BasicAverageShares",
            # ══ بنودُ الأطر القطاعية ══ (بأمر المالك: جودةٌ استثمارية)
            # ليست عامّةً كسابقتها، بل يطلبها إطارُ نشاطٍ بعينه:
            #   • البنوك (‏CAMELS): صافي دخل العمولات ومخصّص خسائر الائتمان
            #     — منهما هامشُ العمولة وتكلفةُ المخاطر.
            #   • الصناديق العقارية (‏NAREIT): الإهلاك والإطفاء ومكاسب بيع
            #     العقار — منها الأموالُ من العمليات (‏FFO).
            # وهي بنودٌ عاديّة في القوائم لا بنودٌ رقابية، فتصل من المصدر
            # نفسه بلا مصدرٍ جديد. وما لم يصل منها يبقى «خارج النطاق».
            f"{pfx}NetInterestIncome", f"{pfx}InterestIncome",
            f"{pfx}CreditLossesProvision",
            f"{pfx}DepreciationAndAmortization",
            f"{pfx}DepreciationAmortizationDepletion",
            f"{pfx}GainLossOnSaleOfPPE",
        ]
        crumb = await self._crumb()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        cookies = crumb[1] if crumb else {}
        period2 = int(time.time())
        period1 = period2 - years * 366 * 24 * 60 * 60
        params = {
            "symbol": symbol,
            "type": ",".join(types),
            "period1": period1,
            "period2": period2,
        }
        if crumb:
            params["crumb"] = crumb[0]
        by_year: dict[int, dict] = {}
        async with httpx.AsyncClient(timeout=14, headers=headers, cookies=cookies, follow_redirects=True) as client:
            for host in ("query2", "query1"):
                try:
                    r = await client.get(
                        f"https://{host}.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}",
                        params=params,
                    )
                    if r.status_code != 200:
                        continue
                    results = ((r.json().get("timeseries") or {}).get("result")) or []
                    if not results:
                        continue
                    for item in results:
                        for key, rows in item.items():
                            if key in ("meta",) or not isinstance(rows, list):
                                continue
                            for row in rows:
                                if not isinstance(row, dict):
                                    continue
                                date = row.get("asOfDate")
                                val = row.get("reportedValue")
                                val = val.get("raw") if isinstance(val, dict) else val
                                if not date or not isinstance(val, (int, float)):
                                    continue
                                # السنويّ يُفهرَس بالسنة، والربعيّ بتاريخ
                                # القياس كاملاً — وإلا دهست أرباعُ السنة
                                # الواحدة بعضها وبقي ربعٌ واحد منها.
                                bucket = str(date) if quarterly else int(str(date)[:4])
                                by_year.setdefault(bucket, {})[key] = val
                                # تاريخ الإقفال يُحفظ للسنويّ أيضاً: السنة
                                # المالية تُقفل في ديسمبر عند أكثر شركات
                                # تداول، ولا تُقفل كذلك عند كلّها. فيُقرأ
                                # الشهر من المصدر ولا يُفترض.
                                by_year[bucket]["_as_of"] = str(date)
                    if by_year:
                        break
                except Exception as e:
                    logger.debug(f"fundamentals-timeseries failed for {symbol} via {host}: {e}")
                    continue

        out = []
        for bucket, d in by_year.items():
            # اسمُ الفترة: السنة للسنويّ، و«2026 ر٢» للربعيّ — الربع يُشتقّ
            # من شهر تاريخ القياس لا يُفترض، فالسنة المالية قد لا تبدأ في
            # يناير وتُنسب الأرباع إلى شهورها الفعلية.
            if quarterly:
                y, mth = int(str(bucket)[:4]), int(str(bucket)[5:7])
                year = f"{y} ر{(mth - 1) // 3 + 1}"
            else:
                year = bucket
            revenue = d.get(f"{pfx}TotalRevenue")
            net_income = d.get(f"{pfx}NetIncomeCommonStockholders") or d.get(f"{pfx}NetIncome")
            equity = d.get(f"{pfx}StockholdersEquity")
            total_liab = d.get(f"{pfx}TotalLiabilitiesNetMinorityInterest")
            total_assets = d.get(f"{pfx}TotalAssets")
            op_cf = d.get(f"{pfx}OperatingCashFlow")
            capex = d.get(f"{pfx}CapitalExpenditure")
            # FCF: prefer Yahoo's own reported figure; else derive from cash
            # generated by operations minus what was reinvested in capex
            # (capex is reported as a negative outflow, hence the addition).
            fcf = d.get(f"{pfx}FreeCashFlow")
            if fcf is None and op_cf is not None and capex is not None:
                fcf = op_cf + capex
            ebit = d.get(f"{pfx}EBIT")
            interest_expense = d.get(f"{pfx}InterestExpense")
            out.append({
                "year": year,
                "as_of": str(bucket) if quarterly else d.get("_as_of"),
                "revenue": revenue,
                "net_income": net_income,
                "eps": d.get(f"{pfx}DilutedEPS") or d.get(f"{pfx}BasicEPS"),
                "equity": equity,
                "debt_ratio": round(total_liab / total_assets, 2) if total_liab and total_assets else None,
                "operating_cash_flow": op_cf,
                "ending_cash": d.get(f"{pfx}CashAndCashEquivalents") or d.get(f"{pfx}EndCashPosition"),
                "capex": capex,
                "free_cash_flow": fcf,
                "interest_coverage": round(ebit / interest_expense, 2) if ebit and interest_expense else None,
                # Raw lines for the Financial Feature Engine — kept alongside the
                # already-derived ratios above rather than replacing them.
                "total_assets": total_assets,
                "total_liabilities": total_liab,
                "gross_profit": d.get(f"{pfx}GrossProfit"),
                "operating_income": d.get(f"{pfx}OperatingIncome"),
                "cost_of_revenue": d.get(f"{pfx}CostOfRevenue"),
                "current_assets": d.get(f"{pfx}CurrentAssets"),
                "current_liabilities": d.get(f"{pfx}CurrentLiabilities"),
                "inventory": d.get(f"{pfx}Inventory"),
                "total_debt": d.get(f"{pfx}TotalDebt"),
                "dividends_paid": d.get(f"{pfx}CashDividendsPaid"),
                "shares_outstanding": d.get(f"{pfx}DilutedAverageShares") or d.get(f"{pfx}BasicAverageShares"),
                # بنودُ الأطر القطاعية — تبقى None لمن لا يُبلّغها، ويقرأها
                # `sector_metrics` فيمتنع عن الاشتقاق بدل أن يخمّنه.
                "net_interest_income": d.get(f"{pfx}NetInterestIncome"),
                "interest_income": d.get(f"{pfx}InterestIncome"),
                "credit_loss_provision": d.get(f"{pfx}CreditLossesProvision"),
                "depreciation": (d.get(f"{pfx}DepreciationAndAmortization")
                                 or d.get(f"{pfx}DepreciationAmortizationDepletion")),
                "gain_on_asset_sale": d.get(f"{pfx}GainLossOnSaleOfPPE"),
            })
        for p in out:
            _set_book_value(p)
        out.sort(key=lambda p: p["year"])
        return out

    async def _quarterly_from_summary(self, symbol: str) -> list[dict]:
        """الأرباعُ من ملخّص الاقتباس — الموضع الثاني الذي يحملها.

        الوحداتُ الربعية موجودةٌ في الملخّص نفسه الذي نقرأ منه السنويَّ
        احتياطاً، فلا مصدرَ جديد ولا نداءَ إضافيّ في مسارٍ آخر.
        """
        res = await self._quote_summary(
            symbol,
            "incomeStatementHistoryQuarterly,balanceSheetHistoryQuarterly,"
            "cashflowStatementHistoryQuarterly")
        if not res:
            return []
        inc = (res.get("incomeStatementHistoryQuarterly") or {}).get("incomeStatementHistory") or []
        bal = (res.get("balanceSheetHistoryQuarterly") or {}).get("balanceSheetStatements") or []
        cf = (res.get("cashflowStatementHistoryQuarterly") or {}).get("cashflowStatements") or []
        if not (inc or bal or cf):
            return []

        def _asof(stmt) -> str | None:
            d = stmt.get("endDate", {})
            raw = d.get("raw") if isinstance(d, dict) else None
            if not raw:
                return None
            from datetime import datetime, timezone
            return datetime.fromtimestamp(raw, tz=timezone.utc).strftime("%Y-%m-%d")

        out: list[dict] = []
        for i in range(min(8, max(len(inc), len(bal), len(cf)))):
            inc_i = inc[i] if i < len(inc) else {}
            bal_i = bal[i] if i < len(bal) else {}
            cf_i = cf[i] if i < len(cf) else {}
            asof = _asof(inc_i) or _asof(bal_i) or _asof(cf_i)
            if not asof:
                continue
            y, mth = int(asof[:4]), int(asof[5:7])
            op_cf = _raw(cf_i, "totalCashFromOperatingActivities")
            capex = _raw(cf_i, "capitalExpenditures")
            total_liab = _raw(bal_i, "totalLiab")
            total_assets = _raw(bal_i, "totalAssets")
            out.append({
                "year": f"{y} ر{(mth - 1) // 3 + 1}",
                "as_of": asof,
                "revenue": _raw(inc_i, "totalRevenue"),
                "net_income": _raw(inc_i, "netIncome"),
                "equity": _raw(bal_i, "totalStockholderEquity"),
                "debt_ratio": (round(total_liab / total_assets, 2)
                               if total_liab and total_assets else None),
                "operating_cash_flow": op_cf,
                "capex": capex,
                "free_cash_flow": (op_cf + capex) if (op_cf is not None and capex is not None) else None,
                "total_assets": total_assets,
                "total_liabilities": total_liab,
                "gross_profit": _raw(inc_i, "grossProfit"),
                "operating_income": _raw(inc_i, "operatingIncome"),
                "cost_of_revenue": _raw(inc_i, "costOfRevenue"),
                "source": "yahoo-summary",
            })
        for p in out:
            _set_book_value(p)
        return out

    async def get_quarterly_financials(self, symbol: str) -> Optional[dict]:
        """القوائم الربعية — مسارٌ مستقلّ عن السنويّ عمداً.

        السنويُّ يُغذّي محرّك الحوكمة والدرجات، وله مسارُ تكميلٍ ومخزنٌ
        وحصصُ نداءات مضبوطة. فإقحامُ الربعيّ فيه كان سيُعرّض ما تُبنى عليه
        الأحكام لتغييرٍ لا يخصّه. والربعيّ هنا للعرض وحده: يُقرأ من المصدر
        الزمنيّ نفسه، ويُخزَّن أسبوعاً — أقصرَ من السنويّ لأن الربع يتبدّل
        أربع مرّاتٍ في السنة لا مرّة.
        """
        from app.services import cache, lastgood
        ck = f"stmtq:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        disk = lastgood.load(ck, max_age_seconds=7 * 24 * 60 * 60)
        if disk is not None:
            cache.set(ck, disk, 7 * 24 * 60 * 60)
            return disk
        try:
            periods = await self._fundamentals_timeseries(symbol, years=3,
                                                          freq="quarterly")
        except Exception as e:                                    # noqa: BLE001
            logger.warning(f"Quarterly financials failed for {symbol}: {e}")
            return None
        if not periods:
            # ══ مسارُ احتياطٍ للربعيّ ══ (بأمر المالك)
            # وجد المالك شركاتٍ لها قوائمُ سنوية ولا ربعية. والسنويُّ له
            # مساران عند المصدر: السلسلةُ الزمنية، ثم ملخّصُ الاقتباس عند
            # فشلها. أمّا الربعيُّ فكان على مسارٍ واحد — فإن لم يُبلّغه
            # المصدرُ في السلسلة سقط كلُّه، لا لأنه غير موجود بل لأننا لم
            # نسأل عنه في الموضع الثاني.
            # والوحدات هنا هي الوحدات الربعية من الملخّص نفسه
            # (‏incomeStatementHistoryQuarterly وأخواتها)، لا مصدرٌ جديد.
            periods = await self._quarterly_from_summary(symbol)
        if not periods:
            return None
        periods = sorted(periods, key=lambda p: p.get("as_of") or "")[-8:]
        out = {"periods": periods, "years": [p["year"] for p in periods],
               "frequency": "quarterly"}
        cache.set(ck, out, 7 * 24 * 60 * 60)
        lastgood.save(ck, out)
        return out

    async def get_financials(self, symbol: str, allow_supplement: bool = True) -> Optional[dict]:
        """Multi-year income/balance/cashflow rows for the governance report —
        this IS the basis the AI score is derived from, so real multi-year
        depth matters here, not just the latest snapshot.

        Tries the deeper fundamentals-timeseries endpoint first (the same one
        Yahoo's own site and yfinance use for 3+ years of history); falls
        back to the shallower quoteSummary statement modules only if that
        returns nothing.

        Sahmak (the scarce 100/day source) is spent SURGICALLY: only when
        `allow_supplement` is True (never during the ~395-company market-wide
        scan) AND Yahoo actually left a gap the experts need (working-capital
        lines, or fewer than 3 years) — see _needs_supplement. Result is
        cached 30 days in memory AND persisted to disk (lastgood), so a
        restart reuses it instead of re-burning Yahoo/Sahmak quota."""
        from app.services import cache, lastgood
        from app.services.usage_tracker import record, can_call
        ck = f"stmt:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        # Disk cache (survives restarts) — statements change only quarterly,
        # so a 30-day-old persisted copy is authoritative and costs no calls.
        disk = lastgood.load(ck, max_age_seconds=cache.FUNDAMENTALS_TTL)
        if disk is not None:
            cache.set(ck, disk, cache.FUNDAMENTALS_TTL)
            return disk
        if not can_call("yahoo"):
            return None

        def _raw(d, *path):
            cur = d
            for p in path:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(p)
            if isinstance(cur, dict):
                cur = cur.get("raw")
            return cur if isinstance(cur, (int, float)) else None

        try:
            record("yahoo")
            deep_periods = await self._fundamentals_timeseries(symbol)
            if len(deep_periods) >= 2:
                for p in deep_periods:
                    p.setdefault("source", "yahoo")
                if allow_supplement and _needs_supplement(deep_periods):
                    try:
                        from app.services import sahmak_library
                        extra = await sahmak_library.financial_periods(symbol)
                        _merge_supplement(deep_periods, extra)
                    except Exception as e:
                        logger.debug(f"Sahmak financials supplement skipped for {symbol}: {e}")
                deep_periods.sort(key=lambda p: p["year"])
                for p in deep_periods:
                    _set_book_value(p)   # يشمل ما جاء من المُكمِّل
                out = {"symbol": symbol, "periods": deep_periods}
                cache.set(ck, out, cache.FUNDAMENTALS_TTL)
                lastgood.save(ck, out)
                return out

            res = await self._quote_summary(
                symbol,
                "incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory,defaultKeyStatistics",
            )
            if not res:
                return None
            inc = res.get("incomeStatementHistory", {}).get("incomeStatementHistory", []) or []
            bal = res.get("balanceSheetHistory", {}).get("balanceSheetStatements", []) or []
            cf = res.get("cashflowStatementHistory", {}).get("cashflowStatements", []) or []

            def year(stmt):
                d = stmt.get("endDate", {})
                raw = d.get("raw") if isinstance(d, dict) else None
                if raw:
                    from datetime import datetime, timezone
                    return datetime.fromtimestamp(raw, tz=timezone.utc).year
                return None

            periods = []
            n = min(3, max(len(inc), len(bal), len(cf)))
            for i in range(n):
                inc_i = inc[i] if i < len(inc) else {}
                bal_i = bal[i] if i < len(bal) else {}
                cf_i = cf[i] if i < len(cf) else {}
                revenue = _raw(inc_i, "totalRevenue")
                net_income = _raw(inc_i, "netIncome")
                equity = _raw(bal_i, "totalStockholderEquity")
                total_liab = _raw(bal_i, "totalLiab")
                total_assets = _raw(bal_i, "totalAssets")
                op_cf = _raw(cf_i, "totalCashFromOperatingActivities")
                # EPS per statement period — present on some Tadawul symbols'
                # incomeStatementHistory, absent on others; left honestly None
                # rather than approximated from current shares outstanding.
                eps = _raw(inc_i, "dilutedEPS") or _raw(inc_i, "basicEPS")
                # Cash & equivalents at period end — a real balance-sheet line
                # (not derived), confirmed present as "cash" on Yahoo's
                # balanceSheetHistory statements.
                ending_cash = _raw(bal_i, "cash")
                capex = _raw(cf_i, "capitalExpenditures")
                fcf = (op_cf + capex) if (op_cf is not None and capex is not None) else None
                ebit = _raw(inc_i, "ebit")
                interest_expense = _raw(inc_i, "interestExpense")
                periods.append({
                    "year": year(inc_i) or year(bal_i) or year(cf_i),
                    "revenue": revenue,
                    "net_income": net_income,
                    "eps": eps,
                    "equity": equity,
                    "debt_ratio": round(total_liab / total_assets, 2) if total_liab and total_assets else None,
                    "operating_cash_flow": op_cf,
                    "ending_cash": ending_cash,
                    "capex": capex,
                    "free_cash_flow": fcf,
                    "interest_coverage": round(ebit / interest_expense, 2) if ebit and interest_expense else None,
                    # لا عدد أسهمٍ في هذا المسار، فتبقى فارغةً حتى تُملأ من
                    # defaultKeyStatistics أدناه للسنة الأخيرة وحدها.
                    "book_value": None,
                })
            periods = [p for p in periods if p["year"]]
            periods.sort(key=lambda p: p["year"])

            # Supplement the latest period when balance/cashflow modules were
            # empty (common for Tadawul symbols): derive from financialData +
            # defaultKeyStatistics so cells aren't blank.
            if periods and any(periods[-1].get(k) is None for k in ("equity", "debt_ratio", "operating_cash_flow", "eps", "ending_cash")):
                try:
                    sup = await self._quote_summary(symbol, "financialData,defaultKeyStatistics,price")
                    if sup:
                        fd = sup.get("financialData", {})
                        ks = sup.get("defaultKeyStatistics", {})
                        pr = sup.get("price", {})
                        last = periods[-1]
                        book = _raw(ks, "bookValue")
                        shares = _raw(ks, "sharesOutstanding") or _raw(pr, "sharesOutstanding")
                        total_debt = _raw(fd, "totalDebt")
                        if last.get("equity") is None and book and shares:
                            last["equity"] = round(book * shares)
                        if last.get("operating_cash_flow") is None:
                            last["operating_cash_flow"] = _raw(fd, "operatingCashflow")
                        if last.get("debt_ratio") is None and total_debt and last.get("equity"):
                            eq = last["equity"]
                            last["debt_ratio"] = round(total_debt / (total_debt + eq), 2) if (total_debt + eq) else None
                        if last.get("eps") is None:
                            last["eps"] = _raw(ks, "trailingEps")
                        if last.get("ending_cash") is None:
                            last["ending_cash"] = _raw(fd, "totalCash")
                        # هذا المسار الأضعف لا يحمل عدد أسهمٍ لكل سنة، فلا
                        # تُحسب القيمة الدفترية إلا للسنة الأخيرة — وهي هنا
                        # سطرٌ **مُبلَّغ** من Yahoo (bookValue) لا مُشتقّ.
                        if last.get("book_value") is None and book:
                            last["book_value"] = round(book, 2)
                except Exception:
                    pass

            for p in periods:
                p.setdefault("source", "yahoo")

            # Supplement from Sahmak (Phase B) — only when allowed and Yahoo
            # left a gap worth a scarce call (see _needs_supplement).
            if allow_supplement and _needs_supplement(periods):
                try:
                    from app.services import sahmak_library
                    extra = await sahmak_library.financial_periods(symbol)
                    _merge_supplement(periods, extra)
                except Exception as e:
                    logger.debug(f"Sahmak financials supplement skipped for {symbol}: {e}")

            periods.sort(key=lambda p: p["year"])
            for p in periods:
                _set_book_value(p)

            if periods:
                out = {"symbol": symbol, "periods": periods}
                cache.set(ck, out, cache.FUNDAMENTALS_TTL)
                lastgood.save(ck, out)
                return out
        except Exception as e:
            logger.warning(f"YahooFinance financials failed for {symbol}: {e}")
        return None

    async def get_ownership(self, symbol: str) -> Optional[dict]:
        """Major-holders breakdown (insiders / institutions / public float)."""
        from app.services import cache
        from app.services.usage_tracker import record, can_call
        ck = f"own:yahoo:{symbol}"
        cached = cache.get(ck)
        if cached is not None:
            return cached
        if not can_call("yahoo"):
            return None
        try:
            record("yahoo")
            res = await self._quote_summary(symbol, "majorHoldersBreakdown")
            mh = (res or {}).get("majorHoldersBreakdown", {})
            def pct(k):
                v = mh.get(k)
                if isinstance(v, dict):
                    v = v.get("raw")
                return round(v * 100, 1) if isinstance(v, (int, float)) else None
            insiders = pct("insidersPercentHeld")
            institutions = pct("institutionsPercentHeld")
            if insiders is None and institutions is None:
                return None
            public = None
            if insiders is not None and institutions is not None:
                public = round(max(0.0, 100 - insiders - institutions), 1)
            out = {"insiders": insiders, "institutions": institutions, "public": public}
            cache.set(ck, out, cache.FUNDAMENTALS_TTL)
            return out
        except Exception as e:
            logger.warning(f"YahooFinance ownership failed for {symbol}: {e}")
        return None


# ─── Sahmak Adapter ───────────────────────────────────────────

class SahmakAdapter:
    """
    Adapter for the Sahmak Saudi market data provider.
    """
    name = "sahmak"

    def __init__(self):
        self.api_key = settings.SAHMAK_API_KEY
        self.BASE_URL = getattr(settings, "SAHMAK_BASE_URL", "https://sahmk.sa").rstrip("/")

    async def get_price(self, symbol: str) -> Optional[PriceData]:
        if not self.api_key:
            logger.warning("Sahmak: No API key configured.")
            return None
        from app.services.usage_tracker import record, can_call
        if not can_call("sahmak"):
            logger.warning("Sahmak: daily quota reached — skipping call to stay within free tier.")
            return None
        try:
            record("sahmak")
            base = symbol.replace(".SR", "")
            # Official Sahmk API: GET /quote/{symbol}/ (Free plan), X-API-Key auth.
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/quote/{base}/",
                    headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                )
                if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                    d = resp.json()
                    d = d.get("data", d)
                    price = d.get("price") or d.get("close") or d.get("last")
                    if price:
                        return PriceData(
                            symbol=symbol,
                            price=float(price),
                            change=float(d.get("change", 0) or 0),
                            change_pct=float(d.get("change_percent", d.get("change_pct", 0)) or 0),
                        )
        except Exception as e:
            logger.warning(f"Sahmak: failed for {symbol}: {e}")
        return None

    async def get_prices(self, symbols: List[str]) -> dict:
        results = {}
        for symbol in symbols:
            data = await self.get_price(symbol)
            if data:
                results[symbol] = data.to_dict()
        return results

    async def get_sharia_status(self, symbol: str) -> Optional[str]:
        """Best-effort Sharia lookup via GET /company/{symbol}/. Sahmk's public
        docs don't list a sharia field, so this reads it only if present in the
        (plan-dependent) company payload; otherwise returns None. The AI lookup
        is the primary source — this is a fallback only."""
        if not self.api_key:
            return None
        from app.services.usage_tracker import record, can_call
        if not can_call("sahmak"):
            logger.warning("Sahmak: daily quota reached — skipping Sharia lookup.")
            return None
        try:
            record("sahmak")
            base = symbol.replace(".SR", "")
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/company/{base}/",
                    headers={"X-API-Key": self.api_key, "Accept": "application/json"},
                )
                if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                    d = resp.json()
                    d = d.get("data", d) if isinstance(d, dict) else d
                    for key in ("sharia_compliant", "is_sharia_compliant", "shariah_compliant", "compliance_status", "sharia_status"):
                        if isinstance(d, dict) and key in d:
                            val = d[key]
                            if isinstance(val, bool):
                                return "COMPLIANT" if val else "NON_COMPLIANT"
                            if isinstance(val, str):
                                v = val.strip().lower()
                                if v in ("compliant", "yes", "true", "متوافق", "متوافقة"):
                                    return "COMPLIANT"
                                if v in ("non_compliant", "no", "false", "غير متوافق", "غير متوافقة"):
                                    return "NON_COMPLIANT"
        except Exception as e:
            logger.warning(f"Sahmak: sharia lookup failed for {symbol}: {e}")
        return None


# ─── Market Data Service (Router) ────────────────────────────

class MarketDataService:
    """
    Central market data service.
    Routes requests to the configured primary provider
    and falls back to secondary if needed.
    """

    def __init__(self):
        self.primary = self._create_adapter(settings.PRIMARY_MARKET_PROVIDER)
        self.secondary = self._create_adapter(settings.SECONDARY_MARKET_PROVIDER)

    def _create_adapter(self, name: str):
        if name == "yahoo_finance":
            return YahooFinanceAdapter()
        elif name == "sahmak":
            return SahmakAdapter()
        return YahooFinanceAdapter()

    async def get_price(self, symbol: str) -> Optional[dict]:
        from app.services.usage_tracker import remaining_fraction
        base = symbol.replace(".SR", "")
        saudi = base.isdigit()

        # Quota synergy: for Saudi tickers both providers can answer, so route
        # to whichever has more of its daily budget left. A provider under a
        # 15% reserve is only used when the other is fully spent — no single
        # key ever dies while the others sit idle.
        providers = [self.primary, self.secondary]
        if saudi:
            def budget(p):
                frac = remaining_fraction("sahmak" if isinstance(p, SahmakAdapter) else "yahoo")
                return (frac >= 0.15, frac)  # reserve floor first, then remaining share
            providers = sorted(providers, key=budget, reverse=True)
        else:
            # Sahmak only knows Saudi tickers; never burn its quota on
            # commodities/indices (BZ=F, GC=F, ^TASI...) it can't answer.
            providers = [p for p in providers if not isinstance(p, SahmakAdapter)]

        for p in providers:
            arg = base if (saudi and isinstance(p, SahmakAdapter)) else symbol
            data = await p.get_price(arg)
            if data:
                return data.to_dict()
        return None

    async def get_prices(self, symbols: List[str]) -> dict:
        return await self.primary.get_prices(symbols)

    def _yahoo(self):
        return self.primary if isinstance(self.primary, YahooFinanceAdapter) else YahooFinanceAdapter()

    async def get_company_info(self, symbol: str) -> Optional[dict]:
        if hasattr(self.primary, "get_company_info"):
            return await self.primary.get_company_info(symbol)
        return None

    async def get_history(self, symbol: str, range_: str = "3mo") -> Optional[list]:
        return await self._yahoo().get_history(symbol, range_)

    async def get_financials(self, symbol: str, allow_supplement: bool = True) -> Optional[dict]:
        return await self._yahoo().get_financials(symbol, allow_supplement=allow_supplement)

    async def get_ownership(self, symbol: str) -> Optional[dict]:
        return await self._yahoo().get_ownership(symbol)

    async def get_dividends(self, symbol: str) -> Optional[dict]:
        return await self._yahoo().get_dividends(symbol)

    async def get_earnings_dates(self, symbol: str) -> Optional[dict]:
        return await self._yahoo().get_earnings_dates(symbol)

    async def get_asset_profile(self, symbol: str) -> Optional[dict]:
        """نبذة النشاط (إنجليزية) والإدارة التنفيذية — لا مجلس الإدارة."""
        return await self._yahoo().get_asset_profile(symbol)


market_service = MarketDataService()
