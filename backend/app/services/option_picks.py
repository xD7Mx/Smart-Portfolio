"""مُنتقي عقود الخيارات طويلة الأجل (‏D759 · بأمر المالك 2026-11-17).

قال المالك: «في مختبر الأبحاث خانةٌ أضع فيها قيمةَ العقد — 150 أو 100 أو 50 دولاراً — فيُخرج أفضلَ خيارٍ في السوق الأمريكيّ،
اختيارُه على التحليل الفنيّ البسيط: المسارُ صاعدٌ أو هابطٌ أو عرضيّ، ويعرف الأخبار — مثلاً استقال رئيسُ إنفيديا فالسهمُ هابط —
ويختار عقوداً طويلةَ المدى لا قصيرة حتى لا تتآكل… صفقاتٌ أختار منها ما يناسبني مع المبرّر».

ثلاثُ مراحل، وكلُّ رقمٍ من مصدره في التطبيق (لا اختلاق):
  ١ **المسار** — لكلّ سهمٍ أو صندوقٍ سائلٍ في القائمة: الإغلاقُ ومتوسّطا 50 و200 وميلُ متوسّط 50 وتغيّرُ ثلاثة أشهر من شموعه اليومية:
     صاعدٌ (متوسّطُ 50 فوق 200 بفرقٍ فوق 1٪ صاعداً بميلٍ فوق 0.3٪، والإغلاقُ فوق 200) · هابطٌ (عكسُه) · وإلا عرضيّ لا يُشترى له عقد.
  ٢ **الأخبار** — عناوينُ السهم في عشرة أيامٍ من محرّك ياهو، يقرؤها النموذجُ قراءةَ محلّل: أثرُها (إيجابيّ · سلبيّ · محايد) وقوّتُه (0–3)
     والحدثُ نفسُه بجملة — من العناوين وحدها. والخبرُ القويُّ المعاكسُ للمسار يُسقط السهم، والقويُّ جداً يعطي العرضيَّ اتجاهَه.
  ٣ **العقد** — آجالٌ بين 120 و430 يوماً (التآكلُ الزمنيُّ بطيءٌ فيها)، وكلفتُه (سعرُ الطلب × 100) ضمن الميزانية، وسيولتُه (اهتمامٌ مفتوح
     وفارقٌ معقول)؛ ويُقاس **احتمالُ الربح عند الانتهاء** من التذبذب الضمنيّ (احتمالُ تجاوز نقطة التعادل في توزيعٍ لوغاريتميّ)،
     والدلتا، والحركةُ المطلوبةُ إلى التعادل بوحدة التذبذب المتوقّع — ويُختار لكلّ سهمٍ أفضلُ عقدٍ ثمّ تُرتَّب الصفقات.
     والسوقُ مغلقٌ يُصفِّر المصدرُ الطلبَ والعرضَ والتذبذب (مقيسٌ 2026-11-17 قبل الافتتاح: صفرٌ في أغلب العقود) — فيُؤخذ سعرُ آخر صفقةٍ
     إن كانت في خمسة أيام، ويُستخرج التذبذبُ الضمنيُّ منه بمعادلة بلاك-شولز، ويُوسَم العقدُ «آخر صفقة».
والاحتمالُ تقديرٌ من سعر السوق نفسِه لا وعد؛ وأقصى الخسارة كلفةُ العقد."""
from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime, timezone

from loguru import logger

# الأسهمُ والصناديقُ الأمريكيةُ الأسيلُ خياراتٍ — حيث تكون للعقود الطويلة أسعارٌ حقيقيةٌ واهتمامٌ مفتوح
UNIVERSE = (
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "SMH", "GLD", "SLV", "TLT", "XBI", "KRE", "ARKK",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "NFLX", "CRM", "ORCL", "INTC", "MU", "QCOM",
    "ADBE", "PLTR", "UBER", "SHOP", "PYPL", "BAC", "JPM", "WFC", "C", "GS", "XOM", "CVX", "OXY", "PFE", "MRK", "JNJ",
    "LLY", "ABBV", "UNH", "KO", "PEP", "WMT", "COST", "HD", "NKE", "DIS", "BA", "CAT", "F", "GM", "T", "VZ", "SOFI",
    "RIVN", "NIO", "BABA", "COIN", "MARA", "HOOD", "SNAP", "AAL", "CCL", "DAL", "UAL", "SBUX", "CVS", "WBD",
    "EEM", "FXI", "EWZ", "GDX", "KWEB", "XLU", "XLV", "XLI", "XLP", "CSCO", "CMCSA", "KMI", "HPE", "VALE", "NOK", "PLUG", "RIOT",
    "CLF", "LUV", "KHC", "GRAB",
)
MIN_DTE, MAX_DTE = 120, 430
RATE = 0.04
MIN_OI = 50
MAX_SPREAD = 0.35
MIN_POP = 0.12
MIN_PRICE = 2.0          # رمزٌ دون دولارين في المصدر منتهٍ أو غيرُ صالحٍ لعقدٍ طويل
STALE_DAYS = 5           # آخرُ صفقةٍ أقدمُ من خمسة أيامٍ لا يُبنى عليها سعر
CANDIDATES = 40
SCAN_TTL, NEWS_TTL, RES_TTL = 6 * 3600, 2 * 3600, 30 * 60
_JOB = {"on": False, "budget": None, "msg": "", "at": None}


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_delta(S: float, K: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / (iv * math.sqrt(T))
    return _ncdf(d1) if call else _ncdf(d1) - 1


def bs_price(S: float, K: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    sq = iv * math.sqrt(T)
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / sq
    d2 = d1 - sq
    disc = K * math.exp(-r * T)
    return S * _ncdf(d1) - disc * _ncdf(d2) if call else disc * _ncdf(-d2) - S * _ncdf(-d1)


def implied_vol(px: float, S: float, K: float, T: float, call: bool, r: float = RATE) -> float | None:
    """التذبذبُ الضمنيُّ من سعر العقد (تنصيفٌ بين 1٪ و500٪) — وسعرٌ خارجَ حدود النموذج لا تذبذبَ له."""
    lo, hi = 0.01, 5.0
    if not (px > 0 and S > 0 and K > 0 and T > 0) or not (bs_price(S, K, T, lo, call, r) < px < bs_price(S, K, T, hi, call, r)):
        return None
    for _ in range(70):
        mid = (lo + hi) / 2
        if bs_price(S, K, T, mid, call, r) < px:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def quote(o: dict, S: float, T: float, call: bool, now: float | None = None) -> dict | None:
    """سعرُ الشراء وتذبذبُه: الطلبُ والعرضُ إن كانا (والسوقُ مفتوح)، وإلا آخرُ صفقةٍ في خمسة أيام. والتذبذبُ من المصدر إن صلح وإلا من السعر."""
    ask, bid, last, K = o.get("ask") or 0, o.get("bid") or 0, o.get("last") or 0, o.get("strike")
    if not K:
        return None
    if ask > 0 and bid > 0:
        px, src, spread, ref = ask, "ask", (ask - bid) / ask, (ask + bid) / 2
    elif last > 0 and o.get("last_trade"):
        try:
            age = ((now or time.time()) - datetime.fromisoformat(o["last_trade"]).timestamp()) / 86400
        except (TypeError, ValueError):
            return None
        if age > STALE_DAYS:
            return None
        px, src, spread, ref = last, "last", None, last
    else:
        return None
    iv = (o.get("iv") or 0) / 100
    if not (0.05 <= iv <= 3):
        iv = implied_vol(ref, S, K, T, call) or 0
    if not (0.05 <= iv <= 3):
        return None
    return {"px": px, "src": src, "spread": spread, "iv": iv}


def prob_beyond(S: float, level: float, T: float, iv: float, call: bool, r: float = RATE) -> float:
    """احتمالُ أن يكون السعرُ عند الانتهاء فوق `level` (للشراء) أو دونه (للبيع) في توزيعٍ لوغاريتميّ بتذبذبٍ ضمنيّ `iv`."""
    if level <= 0:
        return 1.0 if call else 0.0
    d2 = (math.log(S / level) + (r - iv * iv / 2) * T) / (iv * math.sqrt(T))
    return _ncdf(d2) if call else _ncdf(-d2)


def trend_of(bars: list[dict]) -> dict | None:
    """المسارُ من الشموع اليومية: الإغلاقُ ومتوسّطا 50 و200 وميلُ 50 (عشرون جلسة) وتغيّرُ ثلاثة أشهر وأعلى السنة وأدناها."""
    cl = [float(b["close"]) for b in bars if isinstance(b.get("close"), (int, float)) and b["close"] > 0]
    if len(cl) < 210 or cl[-1] < MIN_PRICE:
        return None
    sma = lambda k, end=None: sum(cl[:end][-k:]) / k   # noqa: E731
    c, s50, s200 = cl[-1], sma(50), sma(200)
    s50_prev = sma(50, -20)
    slope = (s50 / s50_prev - 1) * 100
    r3m = (c / cl[-64] - 1) * 100
    hi, lo = max(cl[-252:]), min(cl[-252:])
    # المسارُ الرئيسيّ: ترتيبُ المتوسّطين بفرقٍ فوق 1٪ وميلُ متوسّط 50 فوق 0.3٪ في عشرين جلسة والإغلاقُ على جهة 200 —
    # والتذبذبُ حول متوسّطٍ واحدٍ ليس مساراً. (والارتدادُ إلى ما دون متوسّط 50 في مسارٍ قائمٍ لا يلغيه — قيس 2026-11-17: اشتراطُه
    # جعل 47 من 76 رمزاً «عرضيّاً» منها ما مسارُه بيّن)
    if s50 > s200 * 1.01 and slope > 0.3 and c > s200:
        state = "صاعد"
    elif s50 < s200 * 0.99 and slope < -0.3 and c < s200:
        state = "هابط"
    else:
        state = "عرضي"
    strength = abs(slope) + abs(r3m) / 4 + abs(c / s200 - 1) * 20
    return {"close": round(c, 2), "sma50": round(s50, 2), "sma200": round(s200, 2), "slope50": round(slope, 2), "ret3m": round(r3m, 1),
            "hi52": round(hi, 2), "lo52": round(lo, 2), "state": state, "strength": round(strength, 2)}


def direction(tr: dict, news: dict | None) -> tuple[str | None, str]:
    """اتجاهُ الصفقة: من المسار، والخبرُ القويُّ (قوّة 2 فأكثر) المعاكسُ له يُسقطها، والقويُّ جداً (3) يعطي العرضيَّ اتجاهَه."""
    base = "call" if tr["state"] == "صاعد" else "put" if tr["state"] == "هابط" else None
    imp = {"إيجابي": 1, "سلبي": -1}.get(str((news or {}).get("impact") or ""), 0)
    st = int((news or {}).get("strength") or 0)
    if base and imp and st >= 2 and (imp > 0) != (base == "call"):
        return None, f"الأخبار {'إيجابية' if imp > 0 else 'سلبية'} قويّة تعاكس المسار {tr['state']} — لا صفقة"
    if base is None and imp and st >= 3:
        return ("call" if imp > 0 else "put"), "المسارُ عرضيّ والحدثُ قويٌّ جداً — الاتجاهُ من الخبر"
    if base is None:
        return None, "المسارُ عرضيّ — لا اتجاهَ يُشترى له عقد"
    return base, ""


def candidates(rows: list[dict], S: float, dte: int, call: bool, now: float | None = None) -> list[dict]:
    """عقودُ أجلٍ واحدٍ الصالحةُ بلا قيد الميزانية: سائلةٌ (اهتمامٌ مفتوحٌ وفارقٌ معقولٌ إن عُرف) بسعرٍ حديثٍ وتذبذبٍ صالح واحتمالٍ معقول."""
    T = max(dte, 1) / 365
    out = []
    for o in rows:
        K = o.get("strike")
        if not K or (o.get("oi") or 0) < MIN_OI:
            continue
        q = quote(o, S, T, call, now)
        if not q or (q["spread"] is not None and q["spread"] > MAX_SPREAD):
            continue
        px, iv = q["px"], q["iv"]
        be = K + px if call else K - px
        pop = prob_beyond(S, be, T, iv, call)
        if pop < MIN_POP:
            continue
        sigma = iv * math.sqrt(T)
        need = (be / S - 1) if call else (1 - be / S)
        # الفارقُ المجهول (آخرُ صفقة) يُحسب في الترتيب كفارقٍ متوسّط ولا يُعرض
        score = pop * 100 + min(o.get("oi") or 0, 3000) / 300 - (q["spread"] if q["spread"] is not None else 0.15) * 15 + dte / 365 * 2
        out.append({"contract": o.get("contract"), "type": "call" if call else "put", "strike": K, "ask": px, "bid": o.get("bid"),
                    "px_src": q["src"], "last_trade": o.get("last_trade") if q["src"] == "last" else None,
                    "cost": round(px * 100, 2), "dte": dte, "breakeven": round(be, 2), "need_pct": round(need * 100, 1),
                    "need_sigma": round(need / sigma, 2) if sigma else None, "pop": round(pop * 100, 1), "delta": round(bs_delta(S, K, T, iv, call), 2),
                    "iv": round(iv * 100, 1), "oi": o.get("oi"), "volume": o.get("volume"),
                    "spread_pct": round(q["spread"] * 100, 1) if q["spread"] is not None else None, "score": round(score, 2)})
    return out


def pick_contract(rows: list[dict], S: float, dte: int, call: bool, budget: float, now: float | None = None) -> dict | None:
    """أفضلُ عقدٍ في أجلٍ واحد ضمن الميزانية (سعرُه × 100): أعلى درجةٍ في الصالحين — والاحتمالُ أثقلُ ما فيها."""
    ok = [c for c in candidates(rows, S, dte, call, now) if c["cost"] <= budget]
    return max(ok, key=lambda c: c["score"]) if ok else None


def reasons(sym: str, tr: dict, news: dict | None, k: dict, note: str) -> list[str]:
    """المبرّرُ بالعربية: المسارُ بأرقامه، والخبرُ كما قرأه المحلّل، والعقدُ بما يجعله مناسباً، وأقصى الخسارة."""
    pos = lambda v, ref: "فوق" if v > ref else "دون"   # noqa: E731
    out = [f"المسار {tr['state']}: الإغلاق {tr['close']:,.2f} {pos(tr['close'], tr['sma50'])} متوسّط 50 ({tr['sma50']:,.2f}) "
           f"و{pos(tr['close'], tr['sma200'])} متوسّط 200 ({tr['sma200']:,.2f})، وتغيّرُ ثلاثة أشهر {tr['ret3m']:+.1f}٪."]
    if news and news.get("event"):
        out.append(f"الأخبار ({news.get('impact') or 'محايد'}): {news['event']}")
    elif news is not None:
        out.append("الأخبار: لا حدثَ مؤثّراً في عناوين الأيام العشرة الأخيرة.")
    else:
        out.append("الأخبار: قراءتُها غيرُ متوفّرة الآن — الاختيارُ على المسار وحده.")
    if note:
        out.append(note + ".")
    out.append(f"العقد ينتهي بعد {k['dte']} يوماً فيبطؤ تآكلُه الزمنيّ؛ ونقطةُ التعادل {k['breakeven']:,.2f} تتطلّب حركةً "
               f"{k['need_pct']:+.1f}٪" + (f" ({k['need_sigma']:.1f} من التذبذب المتوقّع حتى الانتهاء)" if k.get("need_sigma") is not None else "") + ".")
    if k.get("px_src") == "last":
        out.append(f"السوقُ مغلقٌ الآن: الكلفةُ سعرُ آخر صفقة ({(k.get('last_trade') or '')[:10]})، والسعرُ الفعليُّ يتحدّد عند الافتتاح.")
    out.append(f"احتمالُ الربح عند الانتهاء نحو {k['pop']:.0f}٪ تقديراً من التذبذب الضمنيّ ({k['iv']:.0f}٪)، والدلتا {k['delta']:+.2f}، "
               f"والاهتمامُ المفتوح {k['oi']:,}، وأقصى الخسارة كلفةُ العقد {k['cost']:,.0f} دولار.")
    return out


# ══ المراحل ══

async def scan() -> dict:
    """المرحلةُ الأولى (تُخبَّأ ستّ ساعات): مسارُ كلّ رمزٍ في القائمة من شموعه اليومية."""
    from app.services import cache
    from app.services.market_data import market_service as M
    hit = cache.get("optpicks:scan:v2")
    if hit:
        return hit
    sem = asyncio.Semaphore(6)

    async def one(s):
        async with sem:
            try:
                bars = await asyncio.wait_for(M.get_bars(s, "1d"), 25) or []
            except Exception:                                     # noqa: BLE001
                return s, None
        return s, trend_of(bars)
    out = {s: t for s, t in await asyncio.gather(*(one(s) for s in UNIVERSE)) if t}
    if len(out) >= 10:
        cache.set("optpicks:scan:v2", out, SCAN_TTL)
    return out


async def headlines(sym: str, days: int = 10) -> list[dict]:
    """عناوينُ السهم في الأيام العشرة الأخيرة من محرّك ياهو — العنوانُ والناشرُ والوقت."""
    from app.services.options_chain import _get
    d = await _get("/v1/finance/search", {"q": sym, "newsCount": 10, "quotesCount": 0, "enableFuzzyQuery": "false"})
    floor = time.time() - days * 86400
    out = []
    for n in (d or {}).get("news") or []:
        t = n.get("providerPublishTime")
        if n.get("title") and isinstance(t, (int, float)) and t >= floor:
            out.append({"title": n["title"], "publisher": n.get("publisher"), "at": datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                        "link": n.get("link")})
    return out[:8]


READ_NEWS = """أنت محلّلُ أسهمٍ أمريكيّ. لكلّ رمزٍ أدناه مسارُه الفنّيّ وعناوينُ أخباره في الأيام العشرة الأخيرة.
اقرأ العناوين وحدها — لا تُضف معلومةً من خارجها — وقدّر أثرَها على السهم في الأشهر القادمة:
- impact: "إيجابي" أو "سلبي" أو "محايد"
- strength: 0 (لا حدث) · 1 (أثرٌ طفيف) · 2 (حدثٌ مهمّ: نتائجُ مفاجئة، ترقيةٌ أو تخفيضٌ مؤثّر، صفقةٌ كبيرة) · 3 (حدثٌ جوهريّ: استقالةُ رئيسٍ تنفيذيّ، تحقيقٌ أو دعوى كبرى، خسارةُ عميلٍ رئيسيّ، استحواذ)
- event: جملةٌ عربيةٌ قصيرةٌ تذكر الحدثَ كما في العنوان وتاريخَه (أو "" إن لا حدث)
JSON فقط بهذا الشكل: {"SYM": {"impact": "...", "strength": 0, "event": "..."}} — واذكر الرموزَ ذاتَ الحدث وحدها؛ ومن لم تذكره فلا حدثَ له.

"""


async def read_news(items: dict[str, dict]) -> dict:
    """المرحلةُ الثانية: عناوينُ كلّ الرموز (فالعرضيُّ قد يأخذ اتجاهَه من حدثٍ جوهريّ) يقرؤها النموذجُ دفعاتٍ من ثلاثين، وتُخبَّأ ساعتين لكلّ رمز.
    وإن تعذّر النموذجُ لدفعةٍ فقراءةُ رموزها «غير متوفّرة» (None)."""
    from app.services import cache
    from app.services import research_desk as RD
    out, todo = {}, {}
    for s, tr in items.items():
        hit = cache.get(f"optpicks:news:{s}")
        if hit is not None:
            out[s] = hit
        else:
            todo[s] = tr
    if not todo:
        return out
    sem = asyncio.Semaphore(8)

    async def head(s):
        async with sem:
            try:
                return await asyncio.wait_for(headlines(s), 20)
            except Exception:                                     # noqa: BLE001
                return []
    heads = dict(zip(todo, await asyncio.gather(*(head(s) for s in todo))))

    async def ask(chunk):
        lines = []
        for s in chunk:
            tr, h = todo[s], heads.get(s) or []
            lines.append(f"{s} — المسار {tr['state']} (تغيّر 3 أشهر {tr['ret3m']:+.1f}٪):\n"
                         + ("\n".join(f"  [{x['at']}] {x['title']} ({x.get('publisher') or ''})" for x in h) or "  لا عناوين"))
        try:
            return await RD._gemini([{"text": READ_NEWS + "\n\n".join(lines)}], max_tokens=4000, temperature=0.1)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("مُنتقي الخيارات: قراءة الأخبار {}", type(e).__name__)
            return None
    keys = list(todo)
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)]
    read = {}          # الرمزُ ← قراءتُه، لمن قُرئت دفعتُه وحدَه؛ ودفعةٌ تعذّرت فرموزُها «غير متوفّرة» ولا تُخبَّأ
    for chunk, got in zip(chunks, await asyncio.gather(*(ask(c) for c in chunks))):
        if isinstance(got, dict):
            read.update({s: got.get(s) for s in chunk})
    for s in todo:
        h = heads.get(s) or []
        if s not in read:
            out[s] = None
            continue
        r = read[s]
        r = r if isinstance(r, dict) else {}
        rec = {"impact": r.get("impact") if r.get("impact") in ("إيجابي", "سلبي", "محايد") else "محايد",
               "strength": max(0, min(3, int(r.get("strength") or 0))) if str(r.get("strength") or "0").isdigit() else 0,
               "event": str(r.get("event") or "")[:220] if h else "", "headlines": h[:3]}
        out[s] = rec
        cache.set(f"optpicks:news:{s}", rec, NEWS_TTL)
    return out


async def contracts_for(sym: str, call: bool, budget: float) -> tuple[dict | None, float | None]:
    """المرحلةُ الثالثة لرمزٍ واحد: آجالُه بين 120 و430 يوماً (الأقربُ والأوسطُ والأبعد)، وأفضلُ عقدٍ ضمن الميزانية فيها —
    ومعه كلفةُ أرخصِ عقدٍ صالحٍ فيها كلِّها ليُقال للمالك بكم يُفتح هذا السهم إن لم يكن ضمن ميزانيته."""
    from app.services.options_chain import chain
    base = await chain(sym)
    if not base or not base.get("price"):
        return None, None
    exps = [e for e in base.get("expirations") or [] if MIN_DTE <= e["dte"] <= MAX_DTE]
    pick = list({e["t"]: e for e in (exps[:1] + exps[len(exps) // 2:len(exps) // 2 + 1] + exps[-1:])}.values())
    best, cheapest = None, None
    for e in pick:
        ch = await chain(sym, e["t"])
        if not ch:
            continue
        for k in candidates(ch["calls"] if call else ch["puts"], float(ch["price"] or base["price"]), e["dte"], call):
            cheapest = k["cost"] if cheapest is None else min(cheapest, k["cost"])
            if k["cost"] <= budget and (best is None or k["score"] > best["score"]):
                best = {**k, "expiry": e["date"]}
    if best:
        best.update(symbol=sym, name=base.get("name"), price=base.get("price"))
    return best, cheapest


async def run(budget: float) -> dict:
    """الصفقاتُ لميزانيةٍ بعينها: المسارُ ثمّ الأخبارُ ثمّ العقود — وتُخبَّأ نصفَ ساعة."""
    from app.services import cache
    _JOB.update(on=True, budget=budget, msg="قراءةُ المسارات", at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    try:
        sc = await scan()
        top = dict(sorted(sc.items(), key=lambda kv: -kv[1]["strength"]))
        _JOB["msg"] = "قراءةُ الأخبار"
        news = await read_news(top)
        plan, skipped = [], []
        for s, tr in top.items():
            side, note = direction(tr, news.get(s))
            if side:
                plan.append((s, tr, side, note))
            elif note:
                skipped.append({"symbol": s, "why": note})
        plan = plan[:CANDIDATES]
        _JOB["msg"] = "البحثُ في العقود"
        sem = asyncio.Semaphore(4)

        async def one(p):
            s, tr, side, note = p
            async with sem:
                try:
                    k, low = await asyncio.wait_for(contracts_for(s, side == "call", budget), 60)
                except Exception:                                 # noqa: BLE001
                    k, low = None, None
            if not k:
                kind = "شراء" if side == "call" else "بيع"
                skipped.append({"symbol": s, "min_cost": low, "why": (f"أرخصُ عقد {kind} طويلِ الأجل سائلٍ باحتمالٍ معقول كلفتُه {low:,.0f} دولار — فوق الميزانية"
                                                                      if low else f"لا عقدَ {kind} طويلَ الأجل سائلاً باحتمالٍ معقول")})
                return None
            return {**k, "trend": tr, "news": news.get(s), "reasons": reasons(s, tr, news.get(s), k, note)}
        picks = [x for x in await asyncio.gather(*(one(p) for p in plan)) if x]
        picks.sort(key=lambda x: -x["score"])
        skipped.sort(key=lambda x: (x.get("min_cost") is None, x.get("min_cost") or 0))
        res = {"budget": budget, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "picks": picks[:8],
               "closed": any(p.get("px_src") == "last" for p in picks[:8]), "skipped": skipped[:30], "scanned": len(sc), "news_ok": any(v is not None for v in news.values()),
               "limits": {"min_dte": MIN_DTE, "max_dte": MAX_DTE, "min_oi": MIN_OI, "max_spread": int(MAX_SPREAD * 100)}}
        cache.set(f"optpicks:res:{int(budget)}", res, RES_TTL)
        return res
    finally:
        _JOB.update(on=False, msg="")


def cached(budget: float) -> dict | None:
    from app.services import cache
    return cache.get(f"optpicks:res:{int(budget)}")
