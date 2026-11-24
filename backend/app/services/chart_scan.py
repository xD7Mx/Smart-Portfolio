"""مسحُ الرسم للسوق كلِّه — فرصُ صقر من قراءة الرسم (‏D784 · بأمر المالك 2026-11-22).

قال المالك: «خلِّ صقر يفهم تحليلَ الرسم ويبدأ يختار بناءً عليه — الأمريكيُّ والسعوديّ… فائدتُه أنه يُظهر الفرص وأنا أختار… يحلّل الرسمَ لكامل
السوق الأمريكي ولكامل السوق السعودي فيُظهر الفرص، ويعرف جودةَ الفرصة لمدّة كم: بعد شهر، بعد شهرين، حتى الربع القادم… بشكلٍ يوميّ يصيد المتغيّرات
ويُطلع لي قائمة… وفي السوق السعودي بدلَ الإشارات الفرص؛ والأمريكيُّ عقودُ الخيارات».

ثلاثُ مراحل كلَّ يوم لكلّ سوق (قِيس على الخادم 2026-11-22: المُصفّي يعيد السوقَ السعوديَّ كلَّه 389 من 389 بنداءٍ واحد، وكلُّ الحقول الفنية حاضرة):
  ١ السوقُ كلُّه بنداءٍ واحدٍ إلى مُصفّي TradingView: المسارُ (المتوسّطات · ‏±DI) والسيولةُ (‏CMF · ‏MFI · الحجمُ النسبيّ) والتوقيتُ (‏Stoch RSI
     يوميّاً وأسبوعيّاً) ⇐ درجةٌ أوّلية لكلّ شركة — في المجال وحده: السعوديُّ الرئيسيُّ غيرُ الموقوف، والأمريكيُّ ما له عقودُ خياراتٍ واجتاز الأساس.
  ٢ رسومُ السوق السعوديّ الرئيسيّ كلِّه، وأعلى الأمريكيّ درجةً (حصّةُ ياهو اليومية)، تُقرأ بشموعها اليومية بحساب الرسم نفسِه (‏chart_tech):
     المناطقُ الثلاث، ولوحتا الاتجاه والسيولة، وStoch RSI ⇐ الفرصةُ وجودتُها ومدّتُها ودخولُها وهدفُها ووقفُها.
  ٣ مجلسُ صقر (‏saqr_council — ‏D786: «التحليلُ الفنيّ خطوةٌ من بين الخطوات»): كلُّ فرصةٍ تُعرض على المسار والنتائج والأخبار والأحداث
     والحيتان والمحلّلين مع الرسم — ما رفضه عضوٌ يُستبعد بسببه، والباقي يُرتَّب بحكم المجلس، و«الرابط» يقرأ أفضلَها قراءةَ المحلّل.
ولا ينفّذ المسحُ شيئاً: القائمةُ للمالك يختار منها (وصقرٌ السعوديُّ يشتري ما يشتريه بعدها بقواعده، والأمريكيُّ دفترُ «عقود الخيارات» يبدأ بها)."""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone

from loguru import logger

MIN_Q = 50            # أدنى جودةٍ تُعرض فيها فرصة (من 100)
KEEP = 40             # ما يُحفظ من الفرص لكلّ سوق
DEEP = {"sa": 300, "us": 150}  # ما تُقرأ رسومُه بشموعه بعد الدرجة الأوّلية: السعوديُّ الرئيسيُّ كلُّه، والأمريكيُّ أعلاه درجةً (حصّةُ ياهو)
AI_TOP = 6            # ما يقرؤه الذكاءُ من أفضلها
CONC = 10             # ‏D814 (المالك: «المسحُ يأخذ وقتاً»): قراءةُ الرسوم عشرةً معاً لا ستّاً — قِيس المسحُ السعوديُّ 163ث والأمريكيُّ 377ث
TECH = ["name", "description", "close", "change", "Value.Traded", "SMA50", "SMA200", "EMA20", "ADX", "ADX+DI", "ADX-DI", "RSI", "Stoch.RSI.K",
        "Stoch.RSI.D", "Stoch.RSI.K|1W", "RSI|1W", "ChaikinMoneyFlow", "MoneyFlow", "relative_volume_10d_calc", "Perf.1M", "Perf.3M",
        "price_52_week_high", "price_52_week_low", "sector"]   # ‏D788: قطاعُ الشركة — لمحاور العالم في المجلس
_JOB: dict[str, dict] = {m: {"on": False, "msg": "", "at": None} for m in ("us", "sa")}


def _n(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


# ── ١ الدرجةُ الأوّلية من حقول المُصفّي (بلا شموع) ─────────────────────────────────────────────────────
def pre_score(row: dict, side: str = "long") -> float | None:
    """درجةٌ أوّليةٌ للفرصة من حقول المُصفّي: المسارُ (أربعةُ شواهد × 6) والسيولةُ (ثلاثة × 6) وتوقيتُ Stoch RSI (‏+12 · −10) والأسبوعيّ (‏+10) —
    للشراء أو للبيع؛ و‏None إن غابت الحقول."""
    c, s50, s200, e20, pdi, mdi = (_n(row.get(k)) for k in ("close", "SMA50", "SMA200", "EMA20", "ADX+DI", "ADX-DI"))
    if None in (c, s50, s200, e20, pdi, mdi):
        return None
    lng = side == "long"
    t = sum([c > s50, s50 > s200, e20 > s50, pdi > mdi]) if lng else sum([c < s50, s50 < s200, e20 < s50, mdi > pdi])
    cmf, mfi, rv = _n(row.get("ChaikinMoneyFlow")), _n(row.get("MoneyFlow")), _n(row.get("relative_volume_10d_calc"))
    liq = sum([cmf is not None and (cmf > 0 if lng else cmf < 0), mfi is not None and ((40 <= mfi <= 80) if lng else (20 <= mfi <= 60)),
               rv is not None and rv >= 1])
    k, d, kw, rw = (_n(row.get(x)) for x in ("Stoch.RSI.K", "Stoch.RSI.D", "Stoch.RSI.K|1W", "RSI|1W"))
    timing = 0
    if k is not None and d is not None:
        if (lng and (k < 30 or (k > d and k < 50))) or (not lng and (k > 70 or (k < d and k > 50))):
            timing = 12
        elif (lng and k > 85) or (not lng and k < 15):
            timing = -10
    wk = (5 if kw is not None and ((kw < 80) if lng else (kw > 20)) else 0) + (5 if rw is not None and ((rw > 50) if lng else (rw < 50)) else 0)
    return t * 6 + liq * 6 + timing + wk


def _tv_blocking(market: str) -> list[dict]:
    from curl_cffi import requests as cr
    if market == "sa":
        flt = [{"left": "type", "operation": "in_range", "right": ["stock"]}]
    else:
        flt = [{"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}, {"left": "close", "operation": "greater", "right": 5},
               {"left": "average_volume_10d_calc", "operation": "greater", "right": 300_000}, {"left": "type", "operation": "in_range", "right": ["stock", "fund"]}]
    # ‏D788: وإن رُدّ عمودُ القطاع (‏sector) يومًا فالأعمدةُ السابقةُ نفسُها — لا يتعطّل المسحُ لأجل محاور العالم
    for cols in (TECH, [c for c in TECH if c != "sector"]):
        body = {"filter": flt, "columns": cols, "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"}, "range": [0, 6000]}
        with cr.Session(impersonate="chrome") as s:
            r = s.post(f"https://scanner.tradingview.com/{'ksa' if market == 'sa' else 'america'}/scan", data=json.dumps(body), timeout=25,
                       headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
        if r.status_code == 200:
            return [{**dict(zip(cols, row.get("d") or [])), "_s": row.get("s")} for row in (json.loads(r.text or "{}").get("data") or [])]
    return []


async def market_rows(market: str) -> list[dict]:
    try:
        return await asyncio.to_thread(_tv_blocking, market)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("مسحُ الرسم/المُصفّي {}: {}", market, type(e).__name__)
        return []


async def universe(market: str, rows: list[dict]) -> dict[str, dict]:
    """{رمز: صفّ} في مجال صقر: السعوديُّ الرئيسيُّ غيرُ الموقوف ولا الصندوق، والأمريكيُّ ما له عقودٌ واجتاز الأساس (‏saqr_universe) — وإن
    تعذّر مجالُ الأمريكيّ فالسوقُ السائلُ كلُّه."""
    out: dict[str, dict] = {}
    if market == "sa":
        from app.data.saudi_directory import SUSPENDED
        from app.services.saqr_sa import main_company
        for r in rows:
            s = str(r.get("name") or "").strip()
            if not (s.isdigit() and len(s) == 4):                 # الرمزُ من «TADAWUL:2222» إن لم يأتِ الاسمُ رمزاً
                s = str(r.get("_s") or "").split(":")[-1].strip()
            if s.isdigit() and len(s) == 4 and main_company(s) and s not in SUSPENDED:
                out[s] = r
        return out
    from app.services.saqr_universe import canon, universe as U
    try:
        u = await U()
        ok = set(u.get("tr") or {})
    except Exception:                                             # noqa: BLE001
        ok = set()
    for r in rows:
        s = canon(r.get("name"))
        if s and (not ok or s in ok):
            out[s] = r
    return out


# ── ٢ القراءةُ العميقة بالشموع ────────────────────────────────────────────────────────────────────
def sa_session() -> tuple[dict, datetime, bool] | None:
    """لقطةُ «تداول» الرسمية مرّةً للمسح كلِّه — منها شمعةُ اليوم السعوديّ كما في الرسم (‏get_bars: ‏live_daily)."""
    try:
        from app.services import tadawul_market as TM
        rows, live, at = TM.usable_rows()
        if not rows or not at:
            return None
        return rows, datetime.fromisoformat(str(at).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=3))), bool(live)
    except Exception:                                             # noqa: BLE001
        return None


async def daily(sym: str, market: str, ses: tuple | None = None) -> list[dict]:
    """يوميُّ سنتين للمسح من مصدر الرسم نفسِه — ياهو ‏/chart ثمّ تنظيفُ ‏D735، وشمعةُ اليوم السعوديّ من «تداول» كما يرسمها التطبيق —
    بلا خبء: مئاتُ الرموز مرّةً في اليوم لا تُحمَّل على مخزن الخادم ولا على ملفّه (يُكتب كاملاً كلَّ خمس ثوانٍ — ‏D592) وذاكرتُه ‏~1 ج.ب.
    (‏D784 قيس على الخادم: كان يُنادى ‏market_service.daily_base — وهي في مُهايئ ياهو لا في الخدمة — فلم يُقرأ رسمٌ واحد: 0 من 269)."""
    from app.services import bars as B
    from app.services.market_data import market_service as M
    from app.services.usage_tracker import can_call, record
    if not can_call("yahoo"):
        return []
    record("yahoo")
    rows = B.clean_daily(await M._yahoo()._fetch_chart_points(f"{sym}.SR" if market == "sa" else sym, "2y", "1d"))
    if market == "sa" and ses:
        rows = B.live_daily(rows, ses[0].get(sym), ses[1], ses[2])
    return rows


async def deep(sym: str, market: str, ses: tuple | None = None) -> tuple[dict | None, list[dict]]:
    from app.services import chart_tech as T
    try:
        bars = T.clean(await asyncio.wait_for(daily(sym, market, ses), 30))
    except Exception as e:                                        # noqa: BLE001
        logger.debug("مسحُ الرسم/الشموع {}: {}", sym, type(e).__name__)
        return None, []
    if len(bars) < 60:
        return None, bars
    return T.read(bars, saudi=market == "sa", longs_only=market == "sa"), bars


def item(sym: str, name: str | None, r: dict, bars: list[dict], market: str) -> dict:
    """سطرُ الفرصة كما يُعرض ويُحفظ — بلا شواهدَ مفصّلة (أسبابُها جملٌ قصيرة)."""
    from app.services import option_picks as OP
    T_, L_ = r["trend"], r["liq"] or {}
    out = {"symbol": sym, "name": name, "setup": r["setup"], "side": r["side"], "quality": r["quality"], "horizon": r["horizon"], "horizon_n": r["horizon_n"],
           "entry": r["entry"], "target": r["target"], "stop": r["stop"], "rr": r["rr"], "zone": r["zone"], "where": r["where"], "close": round(r["close"], 4),
           "trend": {"word": T_["word"], "level": T_["level"], "strength": T_["strength"]},
           "liq": {"side": L_.get("side"), "word": L_.get("word"), "level": L_.get("level"), "strength": L_.get("strength"), "tag": L_.get("tag")},
           "k": None if r.get("k") is None else round(r["k"], 1), "rsi": None if r.get("rsi") is None else round(r["rsi"], 1),
           "weekly": (r.get("weekly") or {}).get("word"), "reasons": r.get("reasons") or [],
           "zones": [{"name": z["name"], "lo": round(z["lo"], 4), "hi": round(z["hi"], 4)} for z in r["zones"]]}
    tr = OP.trend_of(bars)                                        # مسارُ صقر نفسُه (‏trend_of) — للمجلس، ولدفتر «عقود الخيارات» بلا جلبٍ ثانٍ
    if tr:
        out["tr"] = tr
    return out


# ── الحفظُ والقراءة ──────────────────────────────────────────────────────────────────────────────
def _path(market: str) -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "saqr")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"opps_{market}.json")


def load(market: str) -> dict | None:
    try:
        with open(_path(market), encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                             # noqa: BLE001
        return None


def save(market: str, data: dict) -> None:
    p = _path(market)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)


def fresh(market: str, days: int = 4) -> dict | None:
    """مسحُ السوق إن كان حديثاً (أربعةُ أيامٍ تغطّي العطلةَ الأسبوعية) — وإلّا None."""
    d = load(market)
    if not d or not d.get("at"):
        return None
    try:
        at = datetime.fromisoformat(d["at"])
    except ValueError:
        return None
    return d if datetime.now(timezone.utc) - at <= timedelta(days=days) else None


def lookup(market: str, sym: str) -> dict | None:
    d = fresh(market)
    return next((x for x in (d or {}).get("items") or [] if x["symbol"] == sym), None)


def chart_of(market: str, sym: str) -> tuple[str, dict | None]:
    """حكمُ الرسم على سهمٍ لصقر: ‏("none", None) لا مسحَ حديث (فقواعدُه السابقة وحدها) · ‏("opp", فرصة) · ‏("weak", قراءة) فرصةٌ دون الجودة ·
    ‏("flat", قراءة) لا فرصةَ في الرسم · ‏("unread", None) لم يُقرأ رسمُه في المسح (درجتُه الأوّليةُ دون غيره)."""
    d = fresh(market)
    if not d or not d.get("read"):
        return "none", None
    x = next((x for x in d.get("items") or [] if x["symbol"] == sym), None)
    if x:
        return "opp", x
    r = (d.get("reads") or {}).get(sym)
    if not r:
        return "unread", None
    return ("weak" if r.get("setup") else "flat"), r


def summary(market: str) -> dict | None:
    """خلاصةُ آخر مسحٍ للوحة صقر: وقتُه وأعدادُه — بلا القائمة."""
    d = load(market)
    return {k: d.get(k) for k in ("at", "universe", "screened", "read", "found")} if d and d.get("at") else None


# ── ٣ مجلسُ صقر — الرسمُ خطوةٌ من بين الخطوات (‏D786) ────────────────────────────────────────────────────────
async def review(market: str, items: list[dict], kept_bars: dict[str, list[dict]], ai: bool = True) -> tuple[list[dict], list[dict]]:
    """كلُّ فرصةٍ من الرسم تُعرض على مجلس صقر (‏saqr_council): المسارُ والرسمُ والنتائجُ والأخبارُ والأحداثُ والحيتانُ والمحلّلون —
    ما رفضه عضوٌ يُستبعد بسببه (ويُعرض في «استبعدها المجلس»)، والباقي يُرتَّب بحكم المجلس ثمّ درجته ثمّ جودة الرسم، و«الرابط» لأفضلها."""
    from app.services import chart_tech as T
    from app.services import saqr_council as CN
    ctx = await CN.context(market)
    reg = ctx.get("reg") or {}
    today = datetime.now(timezone(timedelta(hours=3))).date()
    cands = []
    for x in items:
        s, tr = x["symbol"], x.get("tr")
        cr_any = x
        stt = stxt = None
        if market == "sa":
            from app.services.saqr_sa import results_of
            bars = kept_bars.get(s) or []
            cr_any = T.read(bars, saudi=True, longs_only=False) if len(bars) >= 60 else x
            try:
                stt, stxt, _ = results_of(s, today)
            except Exception:                                     # noqa: BLE001
                stt = stxt = None
        cands.append({"symbol": s, "name": x.get("name"), "side": x["side"], "price": x["close"], "tr": tr, "cr_side": x, "cr_any": cr_any,
                      "liq": x.get("liq"), "stt": stt, "stxt": stxt, "sector": x.get("sector"),
                      "rs3": (tr["ret3m"] - reg["ret3m"]) if market == "sa" and tr and isinstance(reg.get("ret3m"), (int, float)) else None,
                      "earn_days": CN.earn_days(s) if market == "us" else None})
    evs = await CN.collect(market, cands, ctx, conc=8)              # ‏D814: شواهدُ المرشّحين ثمانيةً معاً لا أربعاً
    boards = {}
    approved, rejected = [], []
    for x in items:
        bd = CN.judge(evs[x["symbol"]])
        boards[x["symbol"]] = bd
        x["council"] = CN.compact(bd)
        x["heads"] = evs[x["symbol"]].get("heads") or []
        (rejected if bd["veto"] else approved).append(x)
    rank = {"يوافق": 0, "يوافق بتحفّظ": 1}
    approved.sort(key=lambda x: (rank.get(x["council"]["verdict"], 2), -x["council"]["score"], -x["quality"]))
    if ai:
        # ‏D814: قراءاتُ الذكاء لأفضل الفرص معاً (ثلاثٌ في آن) لا واحدةً بعد واحدة — كلٌّ منها حتى 75 ثانية فكانت ستُّها تتتابع دقائق
        sem = asyncio.Semaphore(3)

        async def link_one(x):
            async with sem:
                x["link"] = await CN.link(x["symbol"], x.get("name"), market, x["side"], boards[x["symbol"]], chart=x, price=x["close"])
        await asyncio.gather(*(link_one(x) for x in approved[:AI_TOP]))
    rej = [{"symbol": x["symbol"], "name": x.get("name"), "setup": x["setup"], "side": x["side"], "quality": x["quality"],
            "why": x["council"]["veto_why"]} for x in rejected]
    return approved, rej


# ── المسح ─────────────────────────────────────────────────────────────────────────────────────────
async def scan(market: str, ai: bool = True) -> dict:
    """مسحُ السوق كلِّه (‏us · sa) ⇐ ‏{market, at, universe, read, found, items, dist} محفوظاً — ولا ينفّذ شيئاً."""
    from app.data.saudi_directory import name_of
    from app.services.usage_tracker import background
    market = "sa" if market == "sa" else "us"
    job = _JOB[market]
    if job["on"]:
        return load(market) or {}
    job.update(on=True, msg="قراءةُ السوق كلِّه من المُصفّي", at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    t0 = time.monotonic()
    try:
        with background():
            rows = await market_rows(market)
            uni = await universe(market, rows)
            sides = ("long",) if market == "sa" else ("long", "short")
            ranked: dict[str, float] = {}
            for s, r in uni.items():
                sc = max((x for x in (pre_score(r, sd) for sd in sides) if x is not None), default=None)
                if sc is not None:
                    ranked[s] = sc
            pool = sorted(ranked, key=lambda s: -ranked[s])[:DEEP[market]]
            job["msg"] = f"قراءةُ رسوم {len(pool)} شركةً بشموعها"
            sem = asyncio.Semaphore(CONC)
            ses = sa_session() if market == "sa" else None
            items, kept_bars, reads = [], {}, {}

            async def one(s):
                async with sem:
                    r, bars = await deep(s, market, ses)
                if r is not None:                                 # قراءةُ كلّ رسمٍ قُرئ — ليقول صقرٌ لماذا لم يختر سهماً
                    reads[s] = {"setup": r.get("setup"), "quality": r.get("quality"), "side": r.get("side"), "where": r.get("where")}
                if not r or not r.get("setup") or r["quality"] < MIN_Q:
                    return                                        # شموعُ ما لا فرصةَ فيه تُترك فوراً — لا تُحبس مئاتُ السلاسل في الذاكرة
                row = uni.get(s) or {}
                it = item(s, (name_of(s) if market == "sa" else None) or row.get("description") or row.get("name"), r, bars, market)
                if market == "us" and isinstance(row.get("sector"), str):
                    it["sector"] = row["sector"]
                items.append(it)
                kept_bars[s] = bars
            await asyncio.gather(*(one(s) for s in pool))
            t_read = time.monotonic()
            items.sort(key=lambda x: (-x["quality"], -x["horizon_n"]))
            items = items[:KEEP]
            rejected: list[dict] = []
            if items:
                job["msg"] = "صقر يقرأ النتائجَ والأخبارَ والأحداثَ والحيتانَ والمحلّلين"
                items, rejected = await review(market, items, kept_bars, ai)
            t_rev = time.monotonic()
            dist: dict[str, int] = {}
            for x in items:
                dist[x["setup"]] = dist.get(x["setup"], 0) + 1
            data = {"market": market, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "universe": len(uni), "screened": len(ranked),
                    "read": len(reads), "found": len(items), "items": items, "dist": dist, "min_q": MIN_Q, "reads": reads, "rejected": rejected,
                    "secs": round(time.monotonic() - t0, 1),
                    # ‏D814: أين ذهب الوقت — القراءةُ (المُصفّي والرسوم) ثمّ المراجعة (الشواهد والذكاء)
                    "phases": {"read": round(t_read - t0, 1), "review": round(t_rev - t_read, 1)}}
            # مسحٌ بلا مجالٍ (تعذّرُ المُصفّي) أو بلا رسمٍ مقروء (تعذّرُ الشموع) لا يمحو مسحاً سابقاً ولا يُعدّ مسحاً — وإلّا رفض صقرٌ
            # كلَّ شركةٍ «لم يُقرأ رسمُها» (قيس على الخادم 2026-11-22: مسحُ الإقلاع 0 رسوم حُفظ حديثاً)
            if uni and reads:
                save(market, data)
            else:
                logger.warning("مسحُ الرسم {}: المجال {} · رسومٌ قُرئت {} — لا يُحفظ", market, len(uni), len(reads))
            return data
    finally:
        job.update(on=False, msg="")


def view(market: str) -> dict:
    """القائمةُ للواجهة — بلا قراءات ما لم يُختر (تبقى في الخادم لأسباب صقر)."""
    m = "sa" if market == "sa" else "us"
    d = load(m) or {}
    return {**{k: v for k, v in d.items() if k != "reads"}, "job": dict(_JOB[m])}
