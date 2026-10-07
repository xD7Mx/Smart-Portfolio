"""‏D614: كاشفُ التجزئة — بأمر المالك بعد تجزئة «سلوشنز» (٢:١): هبط السعرُ إلى النصف وبقيت
كميتُه على العدد القديم، فظهرت خسارةٌ لا وجود لها. والتجزئةُ معلنةٌ معروفة.

لا يُعدَّل شيءٌ من أرقام المالك هنا (الخطّ الأحمر الأوّل): الكاشفُ **يقترح** والمالكُ يطبّق بزرّ.
والمصادرُ، كلٌّ منها كافٍ وحده، ولا تُختلق نسبة:
  ١. إعلانُ «تجزئة» في مفكرة السوق ونسبتُه مقروءةٌ من نصّه
  ٢. هبوطُ السعر عن آخر إغلاقٍ حفظه التطبيقُ بنسبةٍ صحيحة (½ · ⅓ · ¼ …)
  ٣. الإغلاقُ السابق كما يرسله المزوّد، إن لم يكن معدَّلاً
وتسقط الإشارةُ متى سُجّلت تجزئةٌ للشركة بعدها، أو تجاهلها المالك.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from loguru import logger

CLOSES = "split:closes"          # {sym: {"d": "YYYY-MM-DD", "p": price}}
DISMISSED = "split:dismissed"    # ["sym:YYYY-MM-DD"]
NOTIFIED = "split:notified"
SEEN = "split:seen"              # {sym: {"f": factor, "d": date, "src": …}} — الإشارةُ تبقى حتى تُطبَّق أو تُتجاهل
FACTORS = (2, 3, 4, 5, 10, 1.5, 2.5)
TOL = 0.04
WINDOW_DAYS = 10

_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
_WORDS = {"سهمين": 2, "سهمان": 2, "ثلاثة": 3, "ثلاث": 3, "أربعة": 4, "اربعة": 4, "خمسة": 5, "عشرة": 10}


def factor_from_text(text: str | None) -> float | None:
    """نسبةُ التجزئة من نصّ الإعلان — أو لا شيء. لا تخمين."""
    t = (text or "").translate(_AR)
    m = re.search(r"من\s*(\d+(?:\.\d+)?)\s*(?:ريال|ريالات)?\s*إلى\s*(\d+(?:\.\d+)?)", t)
    if m and float(m.group(2)) > 0:                     # القيمةُ الاسمية من ١٠ إلى ٥
        f = float(m.group(1)) / float(m.group(2))
        return f if f > 1 else None
    m = re.search(r"(\d+(?:\.\d+)?)\s*[:：/]\s*(\d+(?:\.\d+)?)", t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        f = max(a, b) / min(a, b) if min(a, b) > 0 else None
        return f if f and 1 < f <= 20 else None
    for w, n in _WORDS.items():
        if re.search(rf"{w}\s*(?:أسهم|اسهم)?\s*(?:مقابل|لكل)", t):
            return float(n)
    return None


def factor_from_prices(prev: float | None, now: float | None) -> float | None:
    """نسبةُ الهبوط إن طابقت تجزئةً معروفة — وإلّا فهو هبوطُ سوقٍ لا تجزئة."""
    if not (isinstance(prev, (int, float)) and isinstance(now, (int, float)) and prev > 0 and now > 0):
        return None
    r = prev / now
    if r < 1.4:
        return None
    for f in FACTORS:
        if abs(r / f - 1) <= TOL:
            return float(f)
    return None


def remember_closes(prices: dict[str, float], today: str | None = None) -> None:
    """آخرُ سعرٍ لكلّ سهمٍ يومَه — مرجعُ المقارنة غداً."""
    from app.services import lastgood
    d = today or date.today().isoformat()
    store = lastgood.load(CLOSES) or {}
    for s, p in prices.items():
        if isinstance(p, (int, float)) and p > 0:
            old = store.get(s) or {}
            # سجلُّ الأمس يبقى بجانب اليوم: من يقرأ بعد حفظ اليوم يقارن بما قبله
            prev = old if old.get("d") and old.get("d") != d else {"d": old.get("pd"), "p": old.get("pp")}
            store[s] = {"d": d, "p": float(p), "pd": prev.get("d"), "pp": prev.get("p")}
    lastgood.save(CLOSES, store)


def _sym(s: str) -> str:
    return str(s or "").replace(".SR", "")


async def pending(db, scoped: bool = True) -> list[dict]:
    """تجزئاتٌ لم تُطبَّق على شركاتٍ مملوكة."""
    from sqlalchemy import select
    from app.models.portfolio import Company, Holding
    from app.models.market import MarketEvent, MarketEventType
    from app.models.transaction import Transaction
    from app.services import lastgood
    from app.services.market_data import market_service

    q = (select(Company.id, Company.symbol, Company.company_name, Holding.quantity, Holding.portfolio_id)
         .join(Holding, Holding.company_id == Company.id).where(Holding.quantity > 0))
    if not scoped:
        q = q.execution_options(skip_portfolio_scope=True)
    rows = (await db.execute(q)).all()
    if not rows:
        return []
    today = date.today()
    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    syms = {_sym(r[1]) for r in rows}
    evs = (await db.execute(select(MarketEvent).where(
        MarketEvent.event_type == MarketEventType.SPLIT, MarketEvent.event_date >= since,
        MarketEvent.event_date <= datetime.now(timezone.utc) + timedelta(days=1)))).scalars().all()
    ev_by = {}
    # ‏المصدرُ الرابع (قيس حيّاً: مفكرةُ السوق خلت من تجزئة سلوشنز، والإغلاقُ السابقُ معدَّلٌ من المزوّد):
    # عناوينُ أخبار الشركة نفسِها في نافذة الأيام — «تجزئة» ونسبتُها من النصّ
    from types import SimpleNamespace
    from app.models.market import MarketNews
    news = (await db.execute(select(MarketNews).where(
        MarketNews.published_at >= since - timedelta(days=20),
        MarketNews.headline.like("%تجزئة%")))).scalars().all()
    for n in news:
        s = _sym(n.company_symbol)
        txt = f"{n.headline} {n.summary or ''}"
        if s in syms and "سلع" not in txt and factor_from_text(txt):
            ev_by.setdefault(s, SimpleNamespace(description=txt, value=None,
                                                event_date=n.published_at))
    for e in evs:
        s = _sym(e.company_symbol)
        if s in syms:
            ev_by[s] = e
    closes = lastgood.load(CLOSES) or {}
    seen_store = dict(lastgood.load(SEEN) or {})
    seen_dirty = False
    dismissed = set(lastgood.load(DISMISSED) or [])
    from app.data.market_universe import MARKET_UNIVERSE

    out, seen = [], set()
    for cid, sym, name, qty, pid in rows:
        s = _sym(sym)
        if (s, pid) in seen:
            continue
        seen.add((s, pid))
        f, when, src = None, None, None
        e = ev_by.get(s)
        if e is not None:
            f = factor_from_text(e.description) or (float(e.value) if e.value and float(e.value) > 1 else None)
            when, src = e.event_date.date(), "إعلان"
        try:
            px = await market_service.get_price(s + ".SR")
        except Exception:                                     # noqa: BLE001
            px = None
        now = getattr(px, "price", None) if px is not None and not isinstance(px, dict) else (px or {}).get("price")
        c = closes.get(s)
        if c and c.get("d") == today.isoformat():
            c = {"d": c.get("pd"), "p": c.get("pp")} if c.get("pd") else None
        if c:
            pf = factor_from_prices(c.get("p"), now)
            if pf:
                f, src = (f or pf), (src or "السعر")
                when = when or today
        if not f:
            prev = getattr(px, "prev_close", None) if px is not None and not isinstance(px, dict) else (px or {}).get("prev_close")
            pf = factor_from_prices(prev, now)
            if pf and (e is not None or c is None):
                f, src, when = (f or pf), (src or "السعر"), (when or today)
        old = seen_store.get(s)
        if not f and old and (today - date.fromisoformat(old["d"])).days <= WINDOW_DAYS:
            f, when, src = float(old["f"]), date.fromisoformat(old["d"]), old.get("src")
        if not f or not when:
            continue
        if not old or old.get("d") != when.isoformat():
            seen_store[s] = {"f": f, "d": when.isoformat(), "src": src}
            seen_dirty = True
        key = f"{s}:{when.isoformat()}"
        if key in dismissed:
            continue
        done = (await db.execute(select(Transaction.id).where(
            Transaction.company_id == cid, Transaction.transaction_type == "SPLIT",
            Transaction.executed_at >= datetime.combine(when - timedelta(days=WINDOW_DAYS), datetime.min.time())))).first()
        if done:
            continue
        if not old or old.get("d") != when.isoformat():
            try:
                invalidate_valuations(s)
            except Exception as e:                            # noqa: BLE001
                logger.warning("التجزئة: الإبطال {}", e)
        out.append({"key": key, "company_id": cid, "symbol": s, "portfolio_id": pid,
                    "name": (MARKET_UNIVERSE.get(s) or {}).get("name_ar") or name or s,
                    "factor": f, "date": when.isoformat(), "source": src,
                    "shares": float(qty or 0), "shares_after": round(float(qty or 0) * f, 4)})
    if seen_dirty:
        lastgood.save(SEEN, seen_store)
    return out


def dismiss(key: str) -> None:
    from app.services import lastgood
    d = list(lastgood.load(DISMISSED) or [])
    if key not in d:
        d.append(key)
        lastgood.save(DISMISSED, d[-200:])


def _fmt(f: float) -> str:
    return str(int(f)) if float(f).is_integer() else f"{f:g}"


async def job() -> dict:
    """بعد الإغلاق: يُنبَّه المالكُ مرّةً لكلّ تجزئة، ثمّ تُحفظ أسعارُ اليوم مرجعاً للغد."""
    from app.core.database import AsyncSessionLocal
    from app.services import lastgood
    async with AsyncSessionLocal() as db:
        items = await pending(db, scoped=False)
    told = set(lastgood.load(NOTIFIED) or [])
    new = [i for i in items if i["key"] not in told]
    if new:
        from app.services.advisor_memory import notify
        lines = [f"تجزئة {i['name']} {_fmt(i['factor'])}:1 — أسهمك {i['shares']:g} تصير {i['shares_after']:g}. "
                 f"طبّقها من بطاقة المحفظة" for i in new]
        try:
            await notify("", lines, raw=True)
            lastgood.save(NOTIFIED, sorted(told | {i["key"] for i in new})[-200:])
        except Exception as e:                                # noqa: BLE001
            logger.warning("كاشف التجزئة: الإشعار {}", e)
    try:
        await _remember_held()
    except Exception as e:                                    # noqa: BLE001
        logger.warning("كاشف التجزئة: حفظ الأسعار {}", e)
    return {"pending": len(items), "notified": len(new)}


async def _remember_held() -> None:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company, Holding
    from app.services.market_data import market_service
    async with AsyncSessionLocal() as db:
        syms = {(_sym(s)) for (s,) in (await db.execute(
            select(Company.symbol).join(Holding, Holding.company_id == Company.id)
            .where(Holding.quantity > 0).execution_options(skip_portfolio_scope=True))).all()}
    prices = {}
    for s in syms:
        try:
            px = await market_service.get_price(s + ".SR")
        except Exception:                                     # noqa: BLE001
            continue
        p = getattr(px, "price", None) if px is not None and not isinstance(px, dict) else (px or {}).get("price")
        if isinstance(p, (int, float)):
            prices[s] = p
    remember_closes(prices)


def invalidate_valuations(symbol: str) -> dict:
    """‏D619: بعد التجزئة تبقى القيمةُ العادلةُ المحفوظة على عدد الأسهم القديم — قِيس: «سلوشنز» 307 على سعرٍ 103.6
    (صعودٌ 197٪)، وهي قيمةُ ما قبل التجزئة (~207) تُقارن بسعر ما بعدها. فكلُّ تجزئةٍ — يسجّلها المالكُ أو يكشفها
    الكاشف — تُبطل تقييماتِ الشركة المحفوظة كلَّها، فتُحسب من جديد على العدد الجديد (حَكَمُ القيمة السوقية ÷ السعر).
    لا يمسّ شيئاً من أرقام المالك: ما يُبطَل حساباتٌ مشتقّة وحدها."""
    from app.services import cache, lastgood
    s = _sym(symbol)
    out = {"cache": cache.expire_prefix(f"analysis:{s}:") + cache.expire_prefix(f"analysis:{s}.SR:")}
    for key in ("market:fundamentals", "governance:deep"):
        store = lastgood.load(key)
        if isinstance(store, dict):
            hit = [k for k in (s, s + ".SR") if isinstance(store.get(k), dict)]
            for k in hit:
                store[k] = {kk: vv for kk, vv in store[k].items()
                            if not (kk.startswith("fair_value") or kk in ("value_to_price", "upside", "fv", "fv_conf"))}
            if hit:
                lastgood.save(key, store)
            out[key] = len(hit)
    # النسخةُ الاحتياطية للتحليل (تُعرض عند انقطاع المصادر) تبقى، بلا قيمتها العادلة القديمة
    for k in (f"analysis:{s}", f"analysis:{s}.SR"):
        old = lastgood.load(k)
        if isinstance(old, dict) and old.get("fair_value") is not None:
            lastgood.save(k, {**old, "fair_value": None, "valuation": None})
            out[k] = 1
    logger.info("التجزئة {}: أُبطلت التقييماتُ المحفوظة {}", s, out)
    # ويُعاد التقييمُ فوراً في الخلفية (مسحةٌ لرمزٍ واحد) فلا تبقى الشركةُ بلا قيمةٍ حتى المسحة الليلية
    try:
        import asyncio
        from app.services.market_valuation_sweep import sweep
        asyncio.get_running_loop().create_task(sweep([s]))
        out["resweep"] = True
    except Exception:                                             # noqa: BLE001
        out["resweep"] = False
    return out
