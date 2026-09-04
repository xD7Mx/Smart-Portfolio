"""
Market-wide movers (top gainers/losers + advancer/decliner counts across the
whole Tadawul, not just the user's own holdings).

Computed hourly during trading hours by the scheduler, never on-demand per
request — a full scan needs one Yahoo price call per company in the real
live Tadawul directory (fetched fresh each time from Sahmak, so however many
are actually listed, not a hardcoded count). Yahoo has no official daily
quota, but it's an unofficial/undocumented endpoint that can rate-limit or
block a server making requests too frequently — and since every price
lookup on the site (this scan, individual company pages, TASI/Brent
tickers) shares that same one source, getting blocked here would stop
prices working everywhere else too. That risk — not a request-count quota —
is why this stays hourly instead of a tight 15-min interval. The computed
snapshot is cached and served instantly by the read endpoint; if the job
hasn't run yet (e.g. a fresh install before market open), the endpoint
reports that plainly instead of blocking to compute it.
"""

from loguru import logger
from app.services import cache

MOVERS_CACHE_KEY = "market:movers"
MOVERS_TTL = 6 * 60 * 60  # comfortably covers the gap between hourly scheduled runs

OPPORTUNITIES_CACHE_KEY = "market:opportunities"
OPPORTUNITIES_TTL = 6 * 60 * 60
OPPORTUNITY_CANDIDATE_POOL = 30  # how many top-momentum names get the full (expensive) analysis
OPPORTUNITY_RESULT_COUNT = 10


def _sector_breakdown(rows: list) -> list:
    """Average daily change per sector across the whole market, from the same
    scanned rows. Sector comes from the app's own static Tadawul directory
    (app/data/market_universe) — never invented; symbols with no known
    sector are grouped under 'غير مصنّف' and dropped if that's all there is."""
    from app.data.market_universe import MARKET_UNIVERSE
    agg: dict[str, list] = {}
    for r in rows:
        sym = str(r["symbol"]).replace(".SR", "")
        meta = MARKET_UNIVERSE.get(sym) or {}
        sector = meta.get("sector")
        if not sector:
            continue
        agg.setdefault(sector, []).append(r["change_pct"])
    out = [
        {"sector": s, "avg_change_pct": round(sum(v) / len(v), 2), "count": len(v)}
        for s, v in agg.items()
    ]
    out.sort(key=lambda x: x["avg_change_pct"], reverse=True)
    return out


def _return_distribution(rows: list) -> list:
    """Histogram of today's per-company returns into fixed buckets — shows the
    'shape' of the day at a glance (how many names up/down and by how much)."""
    buckets = [
        {"label": "≤ −5%", "lo": None, "hi": -5, "count": 0, "tone": "down"},
        {"label": "−5% إلى −2%", "lo": -5, "hi": -2, "count": 0, "tone": "down"},
        {"label": "−2% إلى 0%", "lo": -2, "hi": 0, "count": 0, "tone": "down"},
        {"label": "0% إلى +2%", "lo": 0, "hi": 2, "count": 0, "tone": "up"},
        {"label": "+2% إلى +5%", "lo": 2, "hi": 5, "count": 0, "tone": "up"},
        {"label": "≥ +5%", "lo": 5, "hi": None, "count": 0, "tone": "up"},
    ]
    for r in rows:
        c = r["change_pct"]
        for b in buckets:
            lo_ok = b["lo"] is None or c >= b["lo"]
            hi_ok = b["hi"] is None or c < b["hi"]
            if lo_ok and hi_ok:
                b["count"] += 1
                break
    return [{"label": b["label"], "count": b["count"], "tone": b["tone"]} for b in buckets]


def _market_sentiment(advancers: int, decliners: int) -> dict:
    """A transparent breadth-derived market mood (NOT a fabricated index): the
    share of advancing companies among those that moved. Stated plainly so it
    can never be mistaken for an official sentiment gauge."""
    moved = advancers + decliners
    score = round(advancers / moved * 100) if moved else 50
    if score >= 70:
        label = "تفاؤل قوي"
    elif score >= 56:
        label = "تفاؤل"
    elif score >= 45:
        label = "حياد"
    elif score >= 30:
        label = "حذر"
    else:
        label = "ضغط بيعي"
    return {"score": score, "label": label, "advancers": advancers, "decliners": decliners}


async def compute_market_movers(db=None) -> dict | None:
    from app.services.market_data import market_service

    # Directory source (owner's data-source policy): the site's OWN static
    # Tadawul directory is the SOLE source (app/data/market_universe, 395 real
    # symbols we collected) — the whole-market scan's reliability rests only on
    # our own data + Yahoo prices, with ZERO dependency on Sahmak. Sahmak's job
    # is now strictly the financial-statements backup behind Yahoo (see
    # market_data.get_financials); it's intentionally not called here so the
    # site keeps working identically if Sahmak is ever dropped entirely.
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    # السوق الرئيسي فقط (تاسي): رموز نمو الموازية (9xxx) تُستثنى من إحصاءات
    # السوق — النِّسب والتوزيع والسيولة والمزاج — كما تفعل تطبيقات البنوك
    # الحقيقية؛ إدراجها كان يحرف الأرقام عن السوق الفعلي.
    names = {s: (m.get("name_ar") or m.get("name_en") or s)
             for s, m in main_market(MARKET_UNIVERSE).items()}
    # ══ الصناديقُ تُسعَّر ولا تُحسب في إحصاء السوق ══
    # صناديقُ المؤشرات المتداولة (‏9400–9409) أوراقٌ حقيقية بأسعارٍ حقيقية
    # (أثبتها المالك بصورة `9407.SR` على ياهو: 25.50 ريالاً بإغلاقٍ متأخّر)،
    # لكنّها ليست شركاتٍ في تاسي — فلا تدخل الاتّساع ولا المزاج ولا السيولة
    # ولا ترتيبَ الرابحين، وإلّا حرفت إحصاءَ السوق عن معناه.
    # فتُجلب أسعارُها في المسحة نفسها (بلا نداءٍ إضافيّ) وتوضع في `stocks`
    # وحدها — وهي التي تقرأ منها خريطةُ القطاعات حركةَ كل رمز. فيرى المالك
    # حركةَ صندوقه، ولا يتلوّث إحصاءُ السوق.
    fund_syms = [s for s, m in MARKET_UNIVERSE.items()
                 if m.get("sector") == "صناديق المؤشرات المتداولة"]

    if not names:
        logger.warning("Market movers: no company directory available — skipping.")
        return None

    # Yahoo needs the .SR suffix — bare Tadawul digits ("2222") silently
    # return nothing, which made the whole scan yield ZERO prices and left
    # every market widget stuck on "لم تُحسب بيانات السوق بعد" forever.
    yahoo_syms = {f"{s}.SR": s for s in list(names) + fund_syms}
    prices = await market_service.get_prices(list(yahoo_syms.keys()))
    if not prices:
        logger.warning("Market movers: no prices returned for any symbol — skipping.")
        return None

    def _row(ysym, d):
        sym = yahoo_syms[ysym]
        return {"symbol": sym,
                "name": (MARKET_UNIVERSE.get(sym) or {}).get("name_ar")
                        or names.get(sym, sym),
                "price": d["price"], "change_pct": d["change_pct"],
                "volume": d.get("volume") or 0}

    priced = [(ysym, d) for ysym, d in prices.items()
              if ysym in yahoo_syms and d.get("price") is not None
              and d.get("change_pct") is not None]
    rows = [_row(y, d) for y, d in priced if yahoo_syms[y] in names]
    fund_rows = [_row(y, d) for y, d in priced if yahoo_syms[y] in fund_syms]
    if not rows:
        return None

    advancers = sum(1 for r in rows if r["change_pct"] > 0)
    decliners = sum(1 for r in rows if r["change_pct"] < 0)
    unchanged = len(rows) - advancers - decliners

    sorted_rows = sorted(rows, key=lambda r: r["change_pct"], reverse=True)
    snapshot = {
        "gainers": sorted_rows[:10],
        "losers": list(reversed(sorted_rows[-10:])),
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "total": len(rows),
        # Derived views over the SAME already-computed rows — no extra
        # provider calls. Powers the sector heatmap, distribution histogram,
        # and market-mood gauge widgets on the Market page.
        "sectors": _sector_breakdown(rows),
        "distribution": _return_distribution(rows),
        "sentiment": _market_sentiment(advancers, decliners),
        # Compact per-symbol daily change — lets the sector heatmap expand a
        # clicked sector into ALL its companies (from the directory) annotated
        # with today's move, using the SAME already-scanned rows (no extra
        # provider calls).
        "stocks": {r["symbol"]: r["change_pct"] for r in rows + fund_rows},
        # REAL market liquidity — the actual traded value = Σ(price × today's
        # volume) across every scanned company, from the SAME scan (no extra
        # calls). This is the true market turnover, not the TASI-index
        # price×volume estimate — accurate to the stocks we cover.
        "market_liquidity": round(sum((r["price"] or 0) * (r["volume"] or 0) for r in rows)),
        "liquidity_symbols": sum(1 for r in rows if (r.get("volume") or 0) > 0),
        # تغطية المسح: كم شركةً رُصدت من أصل دليل السوق الرئيسي. بدونها يبدو
        # مجموعُ التداول رقماً مطلقاً، وهو في الحقيقة مجموعُ ما وصلت أسعاره
        # وأحجامه — فإن سقط ثُلث السوق سقط ثُلث الرقم بلا أن يُقال. وهي أيضاً
        # تُفسّر اختلاف ترتيب الرابحين والخاسرين: الشركة التي لم يصل سعرها
        # لا تدخل الترتيب أصلاً.
        "scanned": len(rows),
        "universe": len(names),
    }
    # ══ سلسلةُ السيولة من مسحنا لا من حجم المؤشّر ══
    # بطاقةُ السيولة كانت تبني أعمدتها من (إغلاق تاسي × حجمه)، وياهو لا
    # يُعيد حجماً للمؤشّر غالباً — فتُصفَّى الأعمدةُ كلُّها ويظهر «لم تُحسب
    # السيولة بعد» ولو كان مجموعُ التداول محسوباً. فالسلسلةُ تُبنى من
    # مسحنا نفسه: نقطةٌ لكل يومٍ تُقيَّد وتبقى، فتصير الأعمدةُ تاريخاً
    # حقيقياً لا تقديراً من مؤشّر.
    # ══ ولا تظهر الأعمدةُ إلا بعد يومين ══ (عطبٌ رآه المالك)
    # السلسلةُ تتراكم نقطةً في اليوم، فبطاقةُ السيولة تبقى بلا أعمدةٍ
    # يوماً كاملاً بعد كل تركيبٍ جديد — والاحتياطُ (حجمُ المؤشّر) لا يعمل
    # لأن ياهو لا يُعيد حجماً للمؤشّر أصلاً. فتظهر البطاقةُ برأسٍ بلا جسم.
    # والعلاجُ ملءٌ رجعيّ **مقيس لا مخترَع**: تُجمع قيمةُ التداول اليومية
    # (‏سعرُ الإغلاق × الحجم) من تاريخ الشركات التي تحمل سيولةَ السوق —
    # أكبر أربعين بقيمة تداول اليوم، وهي تحمل جُلَّ السيولة — فتخرج سلسلةٌ
    # حقيقيةٌ لعيّنةٍ حقيقية. وتُوسم `sample` تمييزاً لها عن نقاط المسح
    # الكامل، ونقطةُ المسح تتقدّم عليها دائماً في اليوم نفسه.
    # ولا تُقيَّد نقطةٌ صفرية: يومُ عطلةٍ لا تداولَ فيه ليس قراءةَ سيولةٍ
    # منخفضة بل غيابَ قراءة، وتقييدُه يكسر مقياس البطاقة.
    try:
        from app.services import lastgood
        from datetime import date as _date
        series = lastgood.load("market:liquidity_series") or []
        if not isinstance(series, list):
            series = []
        today = _date.today().isoformat()
        by_date = {p.get("date"): p for p in series if isinstance(p, dict)}

        # الملءُ الرجعيّ يُحاوَل مرّةً حين لا تكفي النقاطُ لرسم أعمدة.
        if len(by_date) < 3:
            try:
                top = sorted(rows, key=lambda r: (r.get("price") or 0) * (r.get("volume") or 0),
                             reverse=True)[:40]
                agg: dict[str, float] = {}
                for r in top:
                    hist = await market_service.get_history(r["symbol"], "1mo") or []
                    for p in hist:
                        c, v, d = p.get("close"), p.get("volume"), p.get("date")
                        if d and isinstance(c, (int, float)) and isinstance(v, (int, float)) and v > 0:
                            agg[str(d)[:10]] = agg.get(str(d)[:10], 0.0) + c * v
                # ══ المعايرة: الشكلُ من العيّنة والمستوى من المسح ══
                # العيّنةُ أربعون شركة والمسحُ السوقُ كلُّه، فمجموعاهما في
                # مرتبتين مختلفتين. ولو خُلطا لظهر عمودُ اليوم برجاً فوق
                # أعمدةٍ قزمة — رسمٌ يكذّب نفسه. فتُضرب العيّنةُ كلُّها في
                # نسبة (مسحُ اليوم ÷ عيّنةُ اليوم)، فيبقى **الاتّجاه** وهو
                # المقيس حقّاً، ويستقيم المستوى.
                same_day = agg.get(today) or 0
                scale = (snapshot["market_liquidity"] / same_day
                         if same_day > 0 and snapshot["market_liquidity"] > 0 else 1.0)
                for d, val in agg.items():
                    if val > 0 and d not in by_date:
                        by_date[d] = {"date": d, "value": round(val * scale),
                                      "scanned": len(top), "src": "sample"}
                if agg:
                    logger.info(f"liquidity series back-filled: {len(agg)} days "
                                f"from {len(top)} names (scale {scale:.2f})")
            except Exception as e:                                # noqa: BLE001
                logger.warning(f"liquidity back-fill failed: {e}")

        if snapshot["market_liquidity"] > 0:
            by_date[today] = {"date": today, "value": snapshot["market_liquidity"],
                              "scanned": len(rows), "src": "scan"}
        series = [by_date[d] for d in sorted(by_date)][-60:]
        lastgood.save("market:liquidity_series", series)
        snapshot["liquidity_series"] = series
    except Exception:                                             # noqa: BLE001
        pass
    cache.set(MOVERS_CACHE_KEY, snapshot, MOVERS_TTL)
    # Persist to disk immediately so the "last close" survives restarts and is
    # always available to serve instead of an empty screen — the operational
    # floor: the market widgets must never show "not computed yet" once a
    # single successful scan has ever run.
    try:
        from app.services import lastgood
        lastgood.save("market:movers", snapshot)
    except Exception:
        pass
    logger.info(f"Market movers: computed from {len(rows)} companies ({advancers} up, {decliners} down).")

    # Opportunities piggyback on this same scan's already-fetched prices —
    # no extra full-market price pass. Only runs the heavier per-company
    # analysis (financials + 1y history, not just a price) on the top
    # momentum names, and only if a DB session was handed in (the scheduler
    # job does; the endpoint's lazy first-compute fallback does not, to
    # avoid a slow blocking request — it just serves movers immediately and
    # opportunities catch up on the next scheduled run).
    if db is not None:
        try:
            await compute_investment_opportunities(db, sorted_rows)
        except Exception as e:
            logger.error(f"Investment opportunities computation failed: {e}")

    return snapshot


async def compute_investment_opportunities(db, sorted_momentum_rows: list) -> list:
    """Top-momentum names (excluding anything already held) re-ranked by the
    site's real ai_score (70% financial + 30% technical, from analyze_company
    — the same deterministic scoring used on every company's own page, never
    a fabricated number). Bounded to a small candidate pool since this is the
    expensive analysis (financials + 1y history per symbol), not just a price."""
    from sqlalchemy import select
    from app.models.portfolio import Company
    from app.services.analysis import analyze_company

    held = {row[0] for row in (await db.execute(
        select(Company.symbol).where(Company.status != "ARCHIVED")
    )).all()}

    candidates = [r for r in sorted_momentum_rows if r["symbol"] not in held][:OPPORTUNITY_CANDIDATE_POOL]

    scored = []
    for c in candidates:
        result = await analyze_company(c["symbol"], c["name"], db)
        if result and result.get("ai_score") is not None:
            info = result.get("fundamentals") or {}
            val = result.get("valuation") or {}
            # درجة الحوكمة = نفس finance_score الموحّد (financial.score)، وعائد
            # التوزيع والحكم على التقييم (أرخص/أغلى من القطاع) — كلها حقيقية من
            # نفس تحليل الشركة، كي يبني الفلتر عليها بلا اختلاق.
            scored.append({
                "symbol": c["symbol"], "name": c["name"],
                "price": c["price"], "change_pct": c["change_pct"],
                "ai_score": result["ai_score"], "decision": result.get("decision"),
                "governance_score": (result.get("financial") or {}).get("score"),
                "dividend_yield": info.get("dividend_yield"),
                "valuation_verdict": val.get("verdict"),
                # مبخّس = أرخص من متوسط القطاع (حكم التقييم النسبي الحقيقي).
                "is_undervalued": (val.get("verdict") == "أرخص من متوسط القطاع"),
            })

    scored.sort(key=lambda r: r["ai_score"], reverse=True)
    top = scored[:OPPORTUNITY_RESULT_COUNT]
    cache.set(OPPORTUNITIES_CACHE_KEY, top, OPPORTUNITIES_TTL)
    logger.info(f"Investment opportunities: scored {len(scored)}/{len(candidates)} candidates, kept top {len(top)}.")
    return top


def get_cached_market_movers() -> dict | None:
    return cache.get(MOVERS_CACHE_KEY)


def get_cached_opportunities() -> list | None:
    return cache.get(OPPORTUNITIES_CACHE_KEY)
