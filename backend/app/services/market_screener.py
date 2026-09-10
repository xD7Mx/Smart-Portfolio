"""
Whole-market technical screener dataset (فرز الأسهم — نمط TradingView).

For every company in our own Tadawul directory we precompute a compact
technical row from 1y of Yahoo daily closes: last price, SMA50, SMA200,
RSI(14), 52-week high/low, and the derived flags a screener filters on
(above/below each MA, golden/death cross, oversold/overbought). Sector,
today's change% and traded value come from the SAME already-computed
market-movers snapshot — no extra price pass for those.

Computed once daily after the close by the scheduler (this is ~one Yahoo
history call per symbol, so it is deliberately NOT on-demand), cached, and
persisted as last-known-good so the screener survives restarts and serves a
real snapshot instead of an empty screen. The frontend does the actual
filtering/sorting client-side over this one dataset — fast and flexible.
"""
import asyncio
import logging

from app.services import cache

logger = logging.getLogger(__name__)

SCREENER_CACHE_KEY = "market:screener"
SCREENER_TTL = 36 * 60 * 60  # comfortably covers a day+ between daily runs
SCREENER_AT_KEY = "market:screener:at"


def screener_age_hours() -> float | None:
    """عمرُ بيانات الفرز بالساعات، أو None إن كان مجهولاً. يُبنى عليه قرارُ
    وصف السعر: «الآن» لا تُقال إلا لبياناتٍ من جلسة اليوم."""
    import time as _t
    at = cache.get(SCREENER_AT_KEY)
    if at is None:
        try:
            from app.services import lastgood as _lg
            rec = _lg.load(SCREENER_AT_KEY) or {}
            at = rec.get("at")
        except Exception:
            at = None
    if not at:
        return None
    return max(0.0, (_t.time() - float(at)) / 3600.0)
_CONCURRENCY = 8  # bounded parallel history fetches — kind to the unofficial Yahoo endpoint


def _sma(closes: list[float], n: int) -> float | None:
    if len(closes) < n:
        return None
    return round(sum(closes[-n:]) / n, 3)


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    # Seed over the first `period` deltas (Wilder), then smooth over the rest.
    deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    seed = deltas[:period]
    avg_gain = sum(d for d in seed if d > 0) / period
    avg_loss = sum(-d for d in seed if d < 0) / period
    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _ema_series(values: list[float], n: int) -> list[float] | None:
    """سلسلة المتوسط الأسّي — تهيئة بمتوسط بسيط لأول n قيمة ثم التمهيد المعتاد."""
    if len(values) < n:
        return None
    k = 2 / (n + 1)
    ema = sum(values[:n]) / n
    out = [ema]
    for v in values[n:]:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def _macd(closes: list[float], fast: int = 12, slow: int = 26, sig: int = 9) -> dict:
    """MACD القياسي (12/26/9): الخط = EMA12 − EMA26، وخط الإشارة = EMA9 للخط.
    نُرجع الحالة (فوق/تحت الإشارة) و**التقاطع الطازج** إن حدث في آخر شمعة —
    وهو الإشارة القابلة للتنفيذ التي يبحث عنها المستخدم في الفرز.
    القيم None عند قصر التاريخ (لا نُصدر حكماً بلا بيانات)."""
    empty = {"macd": None, "macd_signal": None, "macd_hist": None,
             "macd_bullish": None, "macd_cross": None}
    if len(closes) < slow + sig:
        return empty
    ef, es = _ema_series(closes, fast), _ema_series(closes, slow)
    if not ef or not es:
        return empty
    # محاذاة السلسلتين على نفس الطول (الأبطأ يبدأ متأخراً).
    ef = ef[len(ef) - len(es):]
    macd_line = [f - s for f, s in zip(ef, es)]
    sig_line = _ema_series(macd_line, sig)
    if not sig_line or len(sig_line) < 2:
        return empty
    macd_al = macd_line[len(macd_line) - len(sig_line):]
    hist = [m - s for m, s in zip(macd_al, sig_line)]
    cross = None
    if len(hist) >= 2:
        if hist[-2] <= 0 < hist[-1]:
            cross = "up"        # تقاطع صاعد طازج
        elif hist[-2] >= 0 > hist[-1]:
            cross = "down"      # تقاطع هابط طازج
    return {
        "macd": round(macd_al[-1], 3),
        "macd_signal": round(sig_line[-1], 3),
        "macd_hist": round(hist[-1], 3),
        "macd_bullish": hist[-1] > 0,
        "macd_cross": cross,
    }


def _pct(a: float, b: float | None) -> float | None:
    if not b:
        return None
    return round((a - b) / b * 100, 2)


def _resample(points: list, unit: str) -> list[float]:
    """يُجمّع الشموع اليومية إلى أسبوعية/شهرية محليًّا — إغلاق آخر يوم في كل
    أسبوع/شهر. هكذا نخدم الفواصل الثلاثة بنداءٍ واحد لكل شركة (لا نداء إضافي
    ولا استهلاك حصّة)."""
    buckets: dict[str, float] = {}   # dict يحفظ ترتيب الإدراج (Python 3.7+)
    for p in points:
        c = p.get("close")
        d = p.get("date")
        if c is None or not d:
            continue
        if unit == "W":
            y, w, _ = _date_parts(d)
            key = f"{y}-W{w:02d}"
        else:                        # "M"
            key = d[:7]
        buckets[key] = c             # آخر إغلاق في الحاوية يغلبها
    return list(buckets.values())


def _date_parts(iso: str):
    from datetime import date
    y, m, d = (int(x) for x in iso.split("-")[:3])
    return date(y, m, d).isocalendar()


def _frame_metrics(closes: list[float]) -> dict:
    """مقاييس فاصلٍ واحد. كل علَم ثلاثي الحالة: True/False حكمٌ حقيقي، و None
    «غير متاح» (لا يكفي التاريخ لحساب المتوسط). قبلاً كانت تسقط إلى False
    فتُصنَّف الشركة الحديثة كذباً «تحت م200» و«تقاطع هابط» بلا متوسط أصلاً —
    مخالفٌ لمبدأ لا اختلاق."""
    if not closes:
        return {}
    price = closes[-1]
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    return {
        "sma50": sma50,
        "sma200": sma200,
        "rsi": _rsi(closes),
        "dist_sma50": _pct(price, sma50),
        "dist_sma200": _pct(price, sma200),
        "above_sma50": (price >= sma50) if sma50 is not None else None,
        "above_sma200": (price >= sma200) if sma200 is not None else None,
        "golden_cross": (sma50 >= sma200) if (sma50 is not None and sma200 is not None) else None,
        **_macd(closes),
    }


async def _row_for(symbol: str, name: str, sector: str | None, sem: asyncio.Semaphore) -> dict | None:
    from app.services.market_data import market_service

    async with sem:
        try:
            # تاريخ عشر سنوات بنداءٍ واحد → يكفي لاشتقاق الفواصل الثلاثة:
            # يومي (م50/م200)، أسبوعي (م50=سنة، م200≈٤ سنوات)، شهري (م50≈٤ سنوات).
            # ملاحظة: `_fetch_chart_points` معرّفة على **مُحوّل ياهو** لا على
            # الواجهة MarketDataService — استدعاؤها من الواجهة كان يرمي
            # AttributeError يبتلعه الـexcept، فيعود كل صفّ None ويبقى الفرز
            # فارغاً أبداً. نمرّ عبر `_yahoo()` كما تفعل بقية الدوال.
            points = await market_service._yahoo()._fetch_chart_points(f"{symbol}.SR", "10y", "1d")
        except Exception as e:
            logger.debug(f"Screener: history fetch failed for {symbol}: {e}")
            points = []
    points = points or []
    closes = [p["close"] for p in points if p.get("close") is not None]
    if len(closes) < 60:
        return None  # too little history to say anything technical honestly

    price = closes[-1]
    # قمة/قاع ٥٢ أسبوعاً = آخر ٢٥٢ جلسة تقريباً (لا كامل العشر سنوات).
    last_year = closes[-252:]
    daily = _frame_metrics(closes)

    return {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "price": price,
        "high_52w": round(max(last_year), 3),
        "low_52w": round(min(last_year), 3),
        # الفاصل اليومي مبسوط في الجذر (توافقاً مع أي مستهلك سابق)…
        **daily,
        # …والفواصل الثلاثة مُهيكلة ليختار المستخدم بينها.
        "frames": {
            "D": daily,
            "W": _frame_metrics(_resample(points, "W")),
            "M": _frame_metrics(_resample(points, "M")),
        },
    }


async def _governance_score(ysym: str, sector_ar: str | None) -> float | None:
    """**درجة الحوكمة** من مصدر الحقيقة الواحد — `governance_engine.evaluate_company`
    نفسه الذي تقرأه صفحة الحوكمة وتقييم الأداء ورأي الذكاء.

    كان الفرز يحسبها بدالة أخرى (`finance_score_from_periods`) فيظهر رقمٌ
    يعارض الرقم المعروض في صفحة الحوكمة لنفس الشركة — تعارضٌ يفقد الثقة.

    حماية الحصّة: لا نستدعي المحرّك إلا إذا كانت القوائم المالية **مخزَّنة
    سلفاً** (ذاكرة أو قرص)، فلا يتسبّب الفرز بأي نداء جديد. وإن كانت البيانات
    غير كافية يُعيد المحرّك evaluable=False فنُعيد None (لا درجة مُختلَقة)."""
    try:
        from app.services import cache, lastgood
        ck = f"stmt:{ysym}"
        if cache.get(ck) is None and lastgood.load(ck, max_age_seconds=cache.FUNDAMENTALS_TTL) is None:
            return None                      # لا قوائم مخزَّنة → لا نُشغّل المحرّك
        from app.services.governance_engine import evaluate_company
        gov = await evaluate_company(ysym, sector=sector_ar)
        if not gov or not gov.get("evaluable"):
            return None
        return gov.get("overall")
    except Exception:
        return None


async def _enrich_fundamentals(rows: list[dict]) -> None:
    """يُطعّم صفوف الفرز ببيانات **أساسية وشرعية وحوكمية** — من الكاش وقاعدة
    البيانات فقط، **بلا أي نداء إضافي** لأي مزوّد (فلا تُمسّ حصّة ياهو/سهمك).
    ما لا يتوفّر يبقى None صراحةً («غير متاح») ولا يُختلَق ولا يُفلتَر عليه.

    هذا ما يميّز الفرز عن أي أداة تقنية عامة: يُجيب أسئلة المستثمر الحقيقية
    (متوافق شرعاً · توزيعات > ٤٪ · درجة مالية > ٧٠) لا أسئلة المضارب فقط."""
    from app.services import cache

    # ١) الشرعي + الدرجة المالية من قاعدة البيانات (مصدر التطبيق نفسه).
    db_map: dict[str, dict] = {}
    try:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Company
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Company.symbol, Company.sharia_status, Company.finance_score))
            for sym, sharia, score in res.all():
                db_map[str(sym).replace(".SR", "")] = {
                    "sharia": getattr(sharia, "value", sharia),
                    "finance_score": float(score) if score is not None else None,
                }
    except Exception as e:
        logger.warning(f"Screener: fundamentals from DB unavailable: {e}")

    # المخزن المتراكم لعائد التوزيعات (يُبنى من نداءات تمّت أصلاً في مسحة المفكرة).
    try:
        from app.services.content_engine import fund_store_load
        fund_store = fund_store_load()
    except Exception:
        fund_store = {}

    # التوافق الشرعي: **من ملفات المقاصد/أرقام المحلّية** (تغطّي ~٩٧٪ من السوق
    # بصفر نداءات) لا من قاعدة البيانات — قاعدة البيانات لا تحوي إلا شركاتك،
    # فكان الفلتر الشرعي يُخفي السوق كلّه ويُبقي محفظتك فقط.
    try:
        from app.services import maqasid
    except Exception:
        maqasid = None

    # جدولُ مضاعفات القطاعات — يُبنى مرّةً من المخزن الدائم قبل الحلقة، لا
    # لكلّ صفّ. ويسقط إلى None بلا إسقاط الفرز: القيمةُ النسبية إضافةٌ لا
    # ركن، وغيابُها يترك الحقولَ فارغةً كما لو لم تُحسب.
    _sector_table = None
    try:
        from app.services.relative_value import SectorTable as _ST
        from app.services.relative_value import relative_value as _relative_value
        from app.data.company_sectors import SYMBOL_TO_SECTOR_AR as _SEC_AR
        _sector_table = _ST(
            {"sector": _SEC_AR.get(s), "pe": (v or {}).get("pe_ratio"),
             "pb": (v or {}).get("price_to_book")}
            for s, v in fund_store.items())
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"القيمة النسبية معطّلة في هذا المسح: {type(e).__name__}: {e}")

    for r in rows:
        sym = r["symbol"]
        ysym = f"{sym}.SR"
        d = db_map.get(sym) or {}
        sharia = None
        if maqasid is not None:
            try:
                rating = maqasid.rating(sym)
                if rating:
                    sharia = rating.get("status")
                    r["sharia_source"] = rating.get("source")
                    r["purification"] = rating.get("purification")
            except Exception:
                pass
        if not sharia:                       # احتياط: قاعدة البيانات لشركاتك
            sharia = d.get("sharia")
        r["sharia"] = sharia if sharia and sharia != "UNKNOWN" else None
        # ══ المحرّكُ أوّلاً، والمخزَّنُ احتياطٌ ══ (D198)
        # كان العمودُ المخزَّن في قاعدة البيانات يُقرأ أوّلاً، والمحرّكُ لا
        # يُستدعى إلا إن غاب. والعمودُ **نسخةٌ محفوظة** يكتبها مسحٌ دوريّ:
        # فإن تغيّرت معايرةُ المحرّك (D162) أو تجدّدت القوائمُ ولم يُعَد
        # المسحُ بعد، عُرض في الفرز وخريطة القطاعات رقمٌ قديمٌ بينما صفحةُ
        # الشركة تحسب حيّاً — وهو الاختلافُ الذي رآه المالك.
        #
        # والحيُّ هنا لا يكلّف نداءَ شبكة: `_governance_score` تمتنع ما لم
        # تكن القوائمُ مخزَّنةً سلفاً. فإن لم تكن، رجعنا إلى المخزَّن — رقمٌ
        # قديمٌ خيرٌ من فراغ، والفراغُ خيرٌ من رقمٍ مُختلَق.
        fs = await _governance_score(ysym, r.get("sector"))
        if not fs:
            fs = d.get("finance_score")
        r["finance_score"] = fs if fs else None

        # ٢) حقول التقييم: الكاش أوّلاً (٣٠ يوماً)، فإن انتهى فالمخزن الدائم.
        #    المخزن يتراكم ولا يُفرَّغ، فتكتمل تغطية السوق وتبقى — بخلاف الكاش
        #    الذي يُسقط ما لم يُجلب حديثاً فتظهر خانات فارغة بلا سبب.
        fund = cache.get(f"fund:yahoo:{ysym}") or {}
        stored = fund_store.get(sym) or {}
        pick = lambda k: fund.get(k) if fund.get(k) is not None else stored.get(k)
        r["pe_ratio"] = pick("pe_ratio")
        r["price_to_book"] = pick("price_to_book")
        r["roe"] = pick("roe")
        # ══ السعرُ العادل = متوسّطُ تقديرات بيوت الخبرة ══ (بأمر المالك)
        # نفسُ الرقم الذي تعرضه صفحةُ الشركة وتحليلُ الذكاء — مصدرٌ واحد
        # في التطبيق كلِّه، باسمٍ واحد.
        _fv = pick("target_mean_price")
        r["fair_value"] = _fv
        r["fair_value_asof"] = stored.get("val_asof")

        # ══ ما لا يغطّيه بيتُ خبرة ══ (D212)
        # ‎124 شركةً من ‎273 بلا هدفِ محلّلين، وقد قِيس أنّ ذلك نقصُ السوق لا
        # نقصُ أنبوبنا: لا مصدرَ ينشر لها هدفاً لأن أحداً لا يُصدره. فتُشتقّ
        # لها **قيمةٌ نسبيةٌ إلى القطاع** من مضاعفات نظائرها.
        #
        # وهي حقلٌ مستقلٌّ لا يمسّ `fair_value`: لا تستبدل رأيَ محلّلٍ حيث
        # وُجد، ولا تُخلط به في العرض. تُحسب فقط حيث لا هدفَ أصلاً.
        r["rel_value"] = r["rel_conf"] = r["rel_why"] = None
        if _fv is None and _sector_table is not None:
            try:
                _rv = _relative_value(
                    sector=r.get("sector"), price=r.get("price"),
                    pe=r["pe_ratio"], pb=r["price_to_book"],
                    book_value=pick("book_value"), table=_sector_table)
                if _rv["value"] is not None:
                    r["rel_value"] = round(_rv["value"], 2)
                    r["rel_low"] = round(_rv["low"], 2)
                    r["rel_high"] = round(_rv["high"], 2)
                    r["rel_conf"] = _rv["confidence"]
                    r["rel_basis"] = _rv["basis"]
                else:
                    r["rel_why"] = _rv["why"]
            except Exception as e:                                # noqa: BLE001
                logger.warning(f"القيمة النسبية {sym}: {type(e).__name__}: {e}")
        # ══ المصدرُ نفسُه الذي تقرؤه صفحةُ السهم ══ (D223)
        # كان `fund.get` — الكاشُ وحدَه — بينما بقيةُ الحقول تُقرأ بـ`pick`
        # من الكاش والمخزن الدائم معاً. فإذا انتهى الكاشُ سقط الفرزُ إلى
        # حسابنا الخاصّ وبقيت الصفحةُ على رقم المزوّد: ‎2.44٪ هنا و‎2.56٪ هناك
        # لبوبا (رآه المالك). والحسابُ الخاصُّ يبقى احتياطاً لا بديلاً.
        # ══ مُنتِجٌ واحدٌ للعائد ══ (D223)
        # لا سلسلةَ خاصّةً بالفرز وأخرى بصفحة السهم: الدالّةُ نفسُها بالترتيب
        # نفسِه، فيستحيل اختلافُهما مهما كانت حالُ الكاش. ويعود المصدرُ مع
        # الرقم فلا يُعرض تعريفان تحت اسمٍ واحدٍ بلا بيان.
        from app.services.dividend_yield import resolve as _dy_resolve
        dy, dy_src = _dy_resolve(sym, r.get("price"), fund, stored)
        r["dividend_yield_source"] = dy_src

        # (الاحتياطُ القديم — حسابُ التوزيعات ÷ السعر — انتقل إلى الدالّة
        #  الموحَّدة أعلاه، فلا يبقى تعريفٌ ثانٍ في هذا الملفّ.)
        r["dividend_yield"] = dy

    have = sum(1 for r in rows if r.get("sharia") or r.get("dividend_yield") or r.get("finance_score"))
    logger.info(f"Screener: fundamentals attached for {have}/{len(rows)} rows (cache/DB only).")
    _attach_relative_valuation(rows)


# ── التقييم النسبي للقطاع + الحكم المركّب ─────────────────────────────────
# حسابٌ داخليّ بحت على صفوف الفرز نفسها: **صفر نداء شبكة**. السؤال الذي يجيب
# عنه غير سؤال درجة الحوكمة: تلك تقول «أهذه الشركة سليمة؟»، وهذا يقول «أسعرها
# اليوم رخيصٌ أم غالٍ مقارنةً بأقرانها في قطاعها؟» — وشركةٌ سليمة قد تكون
# صفقةً رديئة بسعر اليوم، ومتعثّرةٌ قد تكون مُسعّرة لتعثّرها سلفاً.
#
# الوسيط لا المتوسّط: مضاعف ربحية شاذّ واحد (٣٠٠ مثلاً لشركةٍ أرباحها تكاد
# تكون صفراً) يجرّ المتوسّط فيبدو القطاع كلّه رخيصاً. والوسيط لا يتأثّر به.
_MIN_PEERS = 3          # أقلّ من ثلاثة أقران ليس قطاعاً يُقاس عليه
_CHEAP = 20.0           # ٪ تحت وسيط القطاع ⇒ مبخّس


def _median(vals: list[float]) -> float | None:
    v = sorted(vals)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def _attach_relative_valuation(rows: list[dict]) -> None:
    by_sector: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("sector"):
            by_sector.setdefault(r["sector"], []).append(r)

    med: dict[str, dict] = {}
    for sec, group in by_sector.items():
        # مضاعف سالب = خسارة، ولا معنى لمقارنته: يُستبعد من الوسيط ومن الحكم.
        pes = [float(x["pe_ratio"]) for x in group if isinstance(x.get("pe_ratio"), (int, float)) and x["pe_ratio"] > 0]
        pbs = [float(x["price_to_book"]) for x in group if isinstance(x.get("price_to_book"), (int, float)) and x["price_to_book"] > 0]
        med[sec] = {
            "pe": _median(pes) if len(pes) >= _MIN_PEERS else None,
            "pb": _median(pbs) if len(pbs) >= _MIN_PEERS else None,
            "n": len(group),
        }

    for r in rows:
        # ── المقياس الثاني: تقدير المحللين ────────────────────────────────
        # سؤالٌ آخر غير سؤال القطاع: لا «أرخص من أقرانه؟» بل «كم يبعد سعره عن
        # القيمة التي يراها المحللون؟». يُعرض مستقلاً ولا يُخلط بالأول، فمصدره
        # آراء بشر لا مقارنة أرقام — ويُحدَّث شهرياً لا يومياً.
        # ══ متغيّرٌ من دالّةٍ أخرى ══ (D199)
        # كان السطرُ يبدأ بـ`_up if _up is not None` — و`_up` متغيّرٌ محلّيٌّ
        # في `_enrich_fundamentals` لا وجودَ له هنا، فيرفع NameError على
        # **كلّ صفّ** فتسقط الفجوةُ عن هدف المحلّلين من الفرز كلِّه. كشفه
        # مسبارٌ شغّل المسارَ على صفٍّ واحد بدل قراءة الشيفرة.
        fv, px = r.get("fair_value"), r.get("price")
        r["upside_pct"] = (round((float(fv) - float(px)) / float(px) * 100, 1)
                           if isinstance(fv, (int, float)) and fv > 0
                           and isinstance(px, (int, float)) and px > 0
                           else None)


        m = med.get(r.get("sector") or "", {})
        gap = basis = None
        pe, pb = r.get("pe_ratio"), r.get("price_to_book")
        # شركةٌ خاسرة (مضاعف سالب): لا تُقاس بمكرّر الدفترية فتُصنَّف «رخيصة» —
        # رُخصها انعكاس الخسارة نفسها، والتصنيف حينها تضليل صريح.
        losing = isinstance(pe, (int, float)) and pe <= 0
        if losing:
            pb = None
        if m.get("pe") and isinstance(pe, (int, float)) and pe > 0:
            gap, basis = (m["pe"] - pe) / m["pe"] * 100, "pe"
        elif m.get("pb") and isinstance(pb, (int, float)) and pb > 0:
            # مكرّر الدفترية بديلٌ لا مساوٍ: يُعلَن الأساس كي لا يُقرأ الرقمان
            # كأنهما مقياس واحد.
            gap, basis = (m["pb"] - pb) / m["pb"] * 100, "pb"

        r["sector_pe"] = round(m["pe"], 2) if m.get("pe") else None
        r["sector_pb"] = round(m["pb"], 2) if m.get("pb") else None
        r["value_gap_pct"] = round(gap, 1) if gap is not None else None
        r["value_basis"] = basis

        # الحكم: لا يُختلق عند نقص البيان — «لا يكفي» حكمٌ صادق، والصمت أفضل
        # من تصنيفٍ مبنيّ على فراغ.
        # ثلاث حالات لا سبع: «مبخّس وسليم» و«مبخّس · حوكمة ضعيفة» لم تكونا
        # حكمين مستقلّين بل حاصل ضرب التقييم في السلامة — وللسلامة فلترها
        # وشريطها المستقلّان، فتقاطعهما يغني عن تصنيفٍ مركّب يضاعف القائمة.
        # وتبقى «خاسرة» و«لا يكفي» حالتَي بيانٍ لا خياري بحث.
        if losing:
            v = "loss"
        elif gap is None:
            v = "insufficient"
        elif gap >= _CHEAP:
            v = "cheap"
        elif gap <= -_CHEAP:
            v = "expensive"
        else:
            v = "fair"
        r["verdict"] = v


async def compute_screener() -> list | None:
    """Full-market technical scan → cached screener dataset. Enriches each row
    with today's change% / traded value / sector from the movers snapshot when
    available (no extra call)."""
    from app.data.market_universe import MARKET_UNIVERSE
    from app.services.market_movers import get_cached_market_movers

    # السوق الرئيسي فقط (تاسي) — نستثني نمو (9xxx) كما في مسح المحركين.
    from app.data.universe import main_market
    universe = main_market(MARKET_UNIVERSE)
    if not universe:
        logger.warning("Screener: empty market directory — skipping.")
        return None

    sem = asyncio.Semaphore(_CONCURRENCY)
    tasks = [
        _row_for(s, (m.get("name_ar") or m.get("name_en") or s), m.get("sector"), sem)
        for s, m in universe.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    rows = [r for r in results if isinstance(r, dict)]
    if not rows:
        logger.warning("Screener: no technical rows computed — skipping.")
        return None

    # طُعم اليوم (التغير% والقيمة المتداولة) من مسح المحركين نفسه.
    movers = get_cached_market_movers() or {}
    day_change = movers.get("stocks") or {}
    for r in rows:
        r["change_pct"] = day_change.get(r["symbol"])

    await _enrich_fundamentals(rows)

    # ══ الجودةُ في قائمة السوق — ليُرتَّب السوقُ ويُصفّى ══ (بأمر المالك)
    # «جاهزٌ لكل شركات السوق» يعني أن يجد المستثمرُ المرشّحين لا أن يحكم
    # على واحدةٍ اختارها هو. فتُطعَّم صفوفُ الفرز بما حُفظ في المخزن
    # العميق عند فتح كل شركة — بلا نداءٍ إضافيّ ولا إعادة حساب — فتُرتَّب
    # القائمة بالدرجة وتُصفّى بالخطّ الأحمر وبنسبة القيمة إلى السعر.
    try:
        from app.services import lastgood as _lg2
        deep = _lg2.load("governance:deep") or {}
        if isinstance(deep, dict):
            for r in rows:
                d = deep.get(str(r["symbol"]).replace(".SR", ""))
                if not isinstance(d, dict):
                    continue
                r["quality"] = d.get("quality")
                r["quality_coverage"] = d.get("coverage")
                r["quality_basis"] = d.get("basis")
                r["archetype"] = d.get("archetype")
                r["red_lines"] = d.get("red_lines") or 0
                r["governance"] = d.get("governance")
                r["decision"] = (d.get("decision") or {}).get("label") \
                    if isinstance(d.get("decision"), dict) else d.get("decision")
                r["value_to_price"] = d.get("value_to_price")
    except Exception:                                             # noqa: BLE001
        pass

    rows.sort(key=lambda r: r["symbol"])
    cache.set(SCREENER_CACHE_KEY, rows, SCREENER_TTL)
    # ختمُ الزمن: بدونه لا يعرف أحدٌ كم عمر هذه الأسعار. المخزّن يعيش ٣٦ ساعة
    # ويسقط بعدها إلى «آخر لقطةٍ سليمة» بلا حدٍّ لعمرها — فقد تُقدَّم أسعارُ
    # أسبوعٍ مضى على أنها سعر اليوم. الختم يجعل ذلك قابلاً للقول لا للإخفاء.
    import time as _t
    cache.set(SCREENER_AT_KEY, _t.time(), SCREENER_TTL)
    try:
        from app.services import lastgood as _lg
        _lg.save(SCREENER_AT_KEY, {"at": _t.time()})
    except Exception:
        pass
    try:
        from app.services import lastgood
        lastgood.save("market:screener", rows)
    except Exception:
        pass
    logger.info(f"Screener: computed technical rows for {len(rows)}/{len(universe)} companies.")
    return rows


async def refresh_derived(rows: list) -> list:
    """يُنعش الحقولَ المشتقّةَ في صفوف اللقطة عند التقديم — لا عند بنائها.

    ══ لقطةٌ مجمَّدةٌ تخالف صفحةً حيّة ══ (D226)
    رأى المالكُ عائدَ التوزيعات ودرجةَ الجودة في الجدول يخالفان صفحةَ السهم
    «كأنهما تطبيقان». والسببُ ليس حساباً مختلفاً بل **زمناً مختلفاً**: صفوفُ
    الفرز تُبنى مرّةً في اليوم وتُخزَّن، وصفحةُ السهم تحسب لحظتَها. فما
    دام الحقلُ المشتقُّ محفوظاً في اللقطة، سيظلّ يخالفها بين مسحةٍ وأخرى —
    ولو وحّدنا المُنتِج.

    والفصلُ الصحيح: **ما يكلّف شبكةً يُخزَّن، وما يُقرأ من مخزنٍ يُحسب عند
    الطلب.** فالسعرُ والمتوسّطاتُ وRSI تبقى لقطةً يومية (نداءُ تاريخٍ لكلّ
    شركة)، وعائدُ التوزيعات ودرجةُ الجودة تُقرآن من المخزن بلا نداءٍ واحد —
    فلا عذرَ لتجميدهما.
    """
    if not rows:
        return rows
    try:
        from app.services.dividend_yield import resolve as _dy_resolve
        from app.services.content_engine import fund_store_load
        store = fund_store_load() or {}
    except Exception:                                             # noqa: BLE001
        return rows

    # ══ والقيمةُ النسبيةُ من جنس المشتقّات ══ (D230)
    # هي حسابٌ من المخزن الدائم بلا نداءٍ واحد، فتجميدُها في اللقطة يورث
    # العطبَ نفسَه من وجهٍ أشدّ: كلُّ صفٍّ بُني قبل وجود المحرّك يبقى بلا
    # قيمةٍ إلى الأبد، فيرى المالكُ «—» على شركةٍ تقييمُها في يدنا. تُعاد
    # هنا عند التقديم — وحيث لا هدفَ محلّلين فقط، فلا تزحف على رأيِ أحد.
    # ══ المائدةُ من المُنتِج الواحد ══ (D240)
    # كانت تُبنى هنا من المخزن **كلِّه**، وفي صفحة السهم من المخزن مصفَّى
    # على السوق الرئيسيّ — فاختلف وسيطُ القطاع بين الشاشتين: ‎28 خلافاً
    # في أربعين شركة (قِيس على الخادم). فصار البناءُ في موضعٍ واحد.
    _tbl = None
    _fields_for = None
    try:
        from app.services.relative_value import fields_for as _fields_for
        from app.services.relative_value import market_table as _mkt
        _tbl = _mkt(store)
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"إنعاشُ السعر العادل معطّل: {type(e).__name__}: {e}")

    for r in rows:
        sym = str(r.get("symbol") or "")
        if not sym:
            continue
        # ══ سعرُ الصفّ هو سعرُ صفحة السهم ══ (بأمر المالك · D236)
        # قال: «بياناتها في كوكبٍ آخر لا تطابق صفحة السهم، سواءَ آخر سعرٍ
        # وغير ذلك». والسببُ مقيس: سعرُ الصفّ **آخرُ إغلاقٍ في تاريخٍ**
        # جُلب وقت المسح (‏`closes[-1]`)، وصفحةُ السهم تقرأ السعرَ اللحظيّ.
        # فيختلفان طولَ اليوم كلَّه — وليس هذا نقصَ بيانٍ بل زمنَين.
        #
        # والعلاجُ بلا نداءٍ واحد: كاشُ الأسعار (‏15 دقيقة) هو نفسُه الذي
        # تملؤه صفحةُ السهم، فيُقرأ منه. وكلُّ ما اشتُقّ من السعر يُعاد
        # حسابُه معه — وإلا صار الصفُّ يخالف **نفسَه**: سعرٌ جديدٌ وفجوةٌ
        # محسوبةٌ على قديم.
        try:
            pd = cache.get(f"price:yahoo:{sym}.SR")
            px_new = getattr(pd, "price", None) if pd is not None else None
            if isinstance(px_new, (int, float)) and px_new > 0:
                r["price"] = px_new
                _chg = getattr(pd, "change_pct", None)
                if isinstance(_chg, (int, float)):
                    r["change_pct"] = round(_chg, 2)
                for _k, _sma in (("dist_sma50", r.get("sma50")),
                                 ("dist_sma200", r.get("sma200"))):
                    if isinstance(_sma, (int, float)):
                        r[_k] = _pct(px_new, _sma)
                if isinstance(r.get("sma50"), (int, float)):
                    r["above_sma50"] = px_new >= r["sma50"]
                if isinstance(r.get("sma200"), (int, float)):
                    r["above_sma200"] = px_new >= r["sma200"]
                # قمّةُ العام وقاعُه: سعرُ اليوم داخلُ العام بالضرورة، فإن
                # تجاوز المحفوظَ فالحدُّ هو السعر — لا رقمٌ أقلُّ من الواقع.
                if isinstance(r.get("high_52w"), (int, float)):
                    r["high_52w"] = round(max(r["high_52w"], px_new), 3)
                if isinstance(r.get("low_52w"), (int, float)):
                    r["low_52w"] = round(min(r["low_52w"], px_new), 3)
                _fv = r.get("fair_value")
                if isinstance(_fv, (int, float)) and _fv > 0:
                    r["upside_pct"] = round((_fv - px_new) / px_new * 100, 1)
        except Exception:                                         # noqa: BLE001
            pass
        try:
            fund = cache.get(f"fund:yahoo:{sym}.SR") or {}
            dy, src = _dy_resolve(sym, r.get("price"), fund, store.get(sym) or {})
            if dy is not None:
                r["dividend_yield"] = dy
                r["dividend_yield_source"] = src
        except Exception:                                         # noqa: BLE001
            pass
        # ══ حقولُ التقييم من سلسلة الصفحة نفسِها ══ (D239)
        # قِيس على أربعين شركةً: المكرّرُ خالف في ‎32، ومضاعفُ الدفترية في
        # ‎33، وهدفُ المحلّلين في ‎8، وحدّا العام في ‎39 و‎38. والسببُ واحد:
        # الصفُّ يحمل **نسخةً** مأخوذةً وقتَ المسح، وصفحةُ السهم تقرأ
        # الكاشَ الحيَّ — مصدران لا مصدرٌ واحد.
        #
        # وما هو دالّةُ سعرٍ يُعاد حسابُه بالسعر الحاضر: المكرّرُ = السعر ÷
        # ربحيةِ السهم، والمضاعفُ = السعر ÷ الدفترية. فلا يبقى مكرّرُ أمسِ
        # بجانب سعرِ اليوم في صفٍّ واحد.
        try:
            _row = store.get(sym) or {}
            _fnd = cache.get(f"fund:yahoo:{sym}.SR") or {}

            def _pick(key: str):
                x = _fnd.get(key)
                return x if x is not None else _row.get(key)

            _px = r.get("price")
            _eps, _bv = _pick("eps"), _pick("book_value")
            # وما خرج عن مدى المعقول لا يُنشَر — الحدُّ نفسُه الذي يستعمله
            # المحرّك، فلا يُعرض مضاعفٌ ‎63 في جدولٍ ويُخفى في صفحة (‏1213).
            from app.services.relative_value import PB_RANGE as _PBR
            from app.services.relative_value import PE_RANGE as _PER
            from app.services.relative_value import _ok as _rng
            if isinstance(_px, (int, float)) and _px > 0:
                if isinstance(_eps, (int, float)) and _eps > 0:
                    _v3 = _rng(round(_px / _eps, 6), *_PER)
                    if _v3 is not None:
                        r["pe_ratio"] = _v3
                if isinstance(_bv, (int, float)) and _bv > 0:
                    _v4 = _rng(round(_px / _bv, 6), *_PBR)
                    r["price_to_book"] = _v4
            for _k, _src in (("fair_value", "target_mean_price"),
                             ("high_52w", "week52_high"),
                             ("low_52w", "week52_low")):
                _v2 = _pick(_src)
                if isinstance(_v2, (int, float)) and _v2 > 0:
                    r[_k] = _v2
            # وحدّا العام يشملان سعرَ اليوم بالضرورة.
            if isinstance(_px, (int, float)) and _px > 0:
                if isinstance(r.get("high_52w"), (int, float)):
                    r["high_52w"] = round(max(r["high_52w"], _px), 3)
                if isinstance(r.get("low_52w"), (int, float)):
                    r["low_52w"] = round(min(r["low_52w"], _px), 3)
                _fv2 = r.get("fair_value")
                if isinstance(_fv2, (int, float)) and _fv2 > 0:
                    r["upside_pct"] = round((_fv2 - _px) / _px * 100, 1)
        except Exception:                                         # noqa: BLE001
            pass
        # درجةُ الجودة: المحرّكُ أوّلاً كما في البناء (D198) — ويمتنع بلا
        # قوائمَ مخزَّنةٍ فيبقى المخزَّنُ في الصفّ، فلا يُفرَّغ عمودٌ كان مملوءاً.
        try:
            fs = await _governance_score(f"{sym}.SR", r.get("sector"))
            if fs:
                r["finance_score"] = fs
        except Exception:                                         # noqa: BLE001
            pass
        # ══ ودائمٌ كما في صفحة السهم ══ (D239)
        # كان يُحسب حيث لا هدفَ محلّلين وحدَه، وصفحةُ السهم تحسبه دائماً
        # (‏D232). فخلا الصفُّ منه في ‎28 شركةً من ‎40 والصفحةُ تعرضه —
        # وشرطُ العرض (الهدفُ أوّلاً) باقٍ في الواجهة لا في الحساب.
        if _tbl is not None and _fields_for is not None:
            try:
                r.update(_fields_for(sym, r.get("price"), store=store,
                                     fund=cache.get(f"fund:yahoo:{sym}.SR") or {},
                                     table=_tbl))
            except Exception:                                     # noqa: BLE001
                pass
    return rows


def get_cached_screener() -> list | None:
    data = cache.get(SCREENER_CACHE_KEY)
    if data is not None:
        return data
    try:
        from app.services import lastgood
        return lastgood.load("market:screener")
    except Exception:
        return None
