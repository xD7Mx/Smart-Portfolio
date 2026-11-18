"""صقر — وكيلُ التداول الآليّ لعقود الخيارات الأمريكية (‏D763 · بأمر المالك 2026-11-18).

«أضف تبويباً اسمه صقر… وكيلُ تداولٍ آليّ… يبدأ من ميزانية 100 دولار ويحاول أن يوصلها إلى 10,000… السوقُ الأمريكيّ كاملٌ قدّام عينه،
عقودُ الخيارات كاملة والسترايكات كاملة… يختار بحسب الميزانية الموجودة في المحفظة… لازم يفهم أنّ الموضوع جدّ، ما هو محاكاة ولا لعب».

فصقرٌ يدير **محفظةَ خياراتٍ مستقلّة** (لا تمسّ محفظةَ المالك السعودية ولا أرقامَها): نقدٌ ومراكزُ وصفقاتٌ مغلقة ومنحنى رأس مال.
والتنفيذُ بأسعار السوق الحقيقية لحظتَها — الشراءُ بسعر العرض والبيعُ بسعر الطلب وعمولةُ الوسيط على كلّ عقد — حتى يُربط وسيطٌ (‏IBKR)؛
فالنتيجةُ ما كان سيحدث فعلاً لا ما يُتمنّى. وكلُّ قرارٍ (دخولٌ أو رفضٌ أو خروج) مكتوبٌ بسببه في السجلّ، ويصل تلغرام.

الدخولُ (كلّ عشرين دقيقة في الجلسة الرسمية، ومقعدٌ شاغرٌ ونقدٌ يكفي):
  ١ السوقُ كلُّه: قائمةُ الأسيل خياراتٍ + الأنشطُ تداولاً اليومَ في السوق الأمريكيّ (‏TradingView) — مسارُ كلٍّ من شموعه اليومية.
  ٢ الاتجاهُ من المسار، والخبرُ القويُّ المعاكس يُسقطه (قراءةُ النموذج لعناوين عشرة أيام).
  ٣ لا يعاكس حركةَ اليوم، ولا يدخل قبل أرباح الشركة بثلاثة أيام (ينهار التذبذبُ بعدها).
  ٤ العقد: أجلُ 21–200 يوماً، عرضٌ وطلبٌ حيّان بفارقٍ ≤ 8٪، اهتمامٌ مفتوح ≥ 100، دلتا 0.35–0.80، تعادلٌ دون الهدف الفنيّ وعائدٌ عنده،
     تآكلٌ يوميّ ≤ 3٪ — ثمّ حكمُ المستشار بيونانياته كلِّها «مناسب» لا «بحذر».
  ٥ الحجم بالطبقة: دون 500 دولار نصفُ رأس المال لمركزين، ودون 2,000 ثلثُه لثلاثة، ودون 10,000 خُمسُه لخمسة، وما فوقها عُشرُه لثمانية.
بوّاباتٌ تمنع الدخول: أوّلُ ربع ساعةٍ وآخرُ عشرين دقيقةً من الجلسة، وحدثٌ اقتصاديٌّ عالي الأثر قريب (الفيدراليُّ يوماً كاملاً)،
وخسارةُ اليوم 15٪ (قاطع)، وثلاثُ صفقاتٍ في اليوم، ولا عودةَ إلى سهمٍ خرج بوقفٍ قبل خمسة أيام.
الخروجُ (كلّ خمس دقائق): وقفٌ عند 60٪ من سعر الشراء، ومن +50٪ يرتفع الوقفُ إلى الدخول ومن +80٪ إلى 75٪ من القمّة، وجنيٌ عند التضاعف
أو بلوغِ السهم الهدفَ، وخروجٌ قبل 14 يوماً من الانتهاء، وعند انكسار الأطروحة."""
import asyncio
import hashlib
import html
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone

from loguru import logger

from app.services import option_picks as OP

START, GOAL = 100.0, 10_000.0
FEE = 0.65                                    # عمولةُ الوسيط لكلّ عقدٍ في كلّ اتّجاه (‏IBKR)
RULES = {"min_oi": 100, "max_spread": 0.08, "min_delta": 0.35, "max_delta": 0.80, "min_rr": 0.6, "min_pop": 0.25}
MIN_DTE, MAX_DTE = 21, 200
EXP_TARGETS = (30, 60, 120)
MAX_BURN = 0.03                               # التآكلُ اليوميّ ≤ 3٪ من قيمة العقد
STOP = 0.60                                   # الوقف: سعرُ الطلب 60٪ من سعر الشراء
TRAIL_BE, TRAIL_ON, TRAIL_KEEP = 1.5, 1.8, 0.75
TAKE = 2.0
EXIT_DTE = 14
OPEN_WAIT, CLOSE_WAIT = 15, 20                # دقائق
EVENT_BEFORE_H, FED_BEFORE_H, EVENT_AFTER_M = 2, 24, 30
FED_RX = ("FOMC", "Federal Funds", "Fed Chair", "Powell")
DAY_LOSS = 0.15
MAX_NEW_DAY = 3
COOL_DAYS = 5
EARN_DAYS = 3
FIGHT_PCT = 1.0                               # لا شراءَ والسهمُ يهبط اليومَ أكثر من 1٪ (ولا بيعَ وهو يصعد)
SCAN_EVERY = 20 * 60
SHORTLIST, DEEP = 24, 8
TIERS = ((500, 0.50, 2), (2000, 0.30, 3), (10_000, 0.20, 5), (math.inf, 0.10, 8))
# ‏D764: سوقان ودفتران — الأمريكيّ (عقودٌ وأسهم) والسعوديّ (أسهمٌ وحدها)، والهدفُ مئةُ ضعفٍ لكلٍّ منهما
MARKETS = {"us": {"file": "ledger.json", "ccy": "USD", "start": START, "broker": "IBKR"},
           "sa": {"file": "ledger_sa.json", "ccy": "SAR", "start": 1_000.0, "broker": "الوسيط السعوديّ"}}
GOAL_X = 100
FEE_SA = 0.00155                              # عمولةُ الوسيط السعوديّ مع ضريبتها لكلّ جهة
STOCK_STOP = 0.93                             # وقفُ السهم: −7٪
STOCK_TRAIL = (1.08, 1.12, 0.94)              # من +8٪ إلى الدخول، ومن +12٪ إلى 94٪ من القمّة
STOCK_TIME_DAYS, STOCK_TIME_GAIN = 42, 1.03   # سهمٌ لم يتقدّم 3٪ في ستّة أسابيع يُحرّر مالُه
REASON_AR = {"stop": "بلغ الوقف", "trail": "وقفٌ متحرّكٌ يحمي الربح", "take": "تضاعف العقد — جنيُ الربح", "target": "بلغ السهمُ الهدف",
             "time": "اقترب الأجل", "broken": "انكسرت الأطروحة", "manual": "إغلاقٌ يدويّ من المالك", "stale": "لم يتقدّم — يُحرَّر المال",
             "regime": "انقلب السوقُ العامّ", "geo": "خطرٌ جيوسياسيّ", "results": "نتائجُ ربعيةٌ مخيّبة"}
_LOCK = asyncio.Lock()
_JOB = {"on": False, "msg": "", "at": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime | None = None) -> str:
    return (t or _now()).isoformat(timespec="seconds")


# ══ الدفتر ══

def _mk(market: str) -> str:
    return market if market in MARKETS else "us"


def _path(market: str = "us") -> str:
    d = os.path.join(os.environ.get("SP_STATE_DIR", "/app/storage"), "saqr")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, MARKETS[_mk(market)]["file"])


def fresh(capital: float | None = None, on: bool = True, market: str = "us") -> dict:
    m = MARKETS[_mk(market)]
    cap = round(float(capital if capital is not None else m["start"]), 2)
    return {"market": _mk(market), "ccy": m["ccy"], "capital": cap, "goal": round(cap * GOAL_X, 2), "cash": cap, "started": _iso(), "on": on,
            "positions": [], "closed": [], "equity": [[_iso(), cap]], "log": [], "signals": [],
            "day": {"date": None, "start_eq": cap, "new": 0}, "last_cycle": None, "last_scan": None, "cycles": 0,
            "health": {}, "runs": [], "broker": {"linked": False, "name": m["broker"]}}


def load(market: str = "us") -> dict:
    try:
        st = json.load(open(_path(market), encoding="utf-8"))
        base = fresh(st.get("capital"), st.get("on", True), market)
        return {**base, **st, "market": _mk(market), "ccy": MARKETS[_mk(market)]["ccy"]}
    except Exception:                                             # noqa: BLE001
        return fresh(market=market)


def save(st: dict) -> None:
    path = _path(st.get("market", "us"))
    tmp = path + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, path)


def log(st: dict, kind: str, text: str, sym: str | None = None) -> None:
    st["log"] = ([{"at": _iso(), "kind": kind, "text": text, "sym": sym}] + st.get("log", []))[:400]


def kind_of(p: dict) -> str:
    return p.get("kind") or "option"


def mult(p: dict) -> int:
    """العقدُ مئةُ سهم، والسهمُ سهم."""
    return 100 if kind_of(p) == "option" else 1


def fee_of(market: str, kind: str, qty: float, px: float) -> float:
    """عمولةُ جهةٍ واحدة: العقدُ الأمريكيّ 0.65 لكلّ عقد، والسهمُ الأمريكيّ عمولةُ IBKR المتدرّجة (0.0035 للسهم، لا تقلّ عن 0.35
    ولا تزيد على 1٪ من القيمة)، والسهمُ السعوديّ 0.155٪ من القيمة مع ضريبتها."""
    if _mk(market) == "sa":
        return round(qty * px * FEE_SA, 2)
    if kind == "stock":
        return round(min(max(0.35, 0.0035 * qty), 0.01 * qty * px), 2)
    return round(FEE * qty, 2)


def mark_of(p: dict) -> float:
    """قيمةُ المركز الآن: سعرُ الطلب (ما يُباع به فعلاً) × المضاعف × الكمّية — وآخرُ طلبٍ معروفٍ إن غاب."""
    return round((p.get("bid") or 0) * mult(p) * p["qty"], 2)


def equity(st: dict) -> float:
    return round(st["cash"] + sum(mark_of(p) for p in st["positions"]), 2)


def tier(eq: float) -> tuple[float, int]:
    """(نسبةُ رأس المال للصفقة الواحدة، أقصى عدد المراكز)."""
    for lim, frac, n in TIERS:
        if eq < lim:
            return frac, n
    return TIERS[-1][1], TIERS[-1][2]


def _pid(contract: str) -> str:
    return hashlib.sha1(f"{contract}|{time.time()}".encode()).hexdigest()[:10]


def buy(st: dict, k: dict, qty: float, why: list[str], src: str = "saqr", px: float | None = None, kind: str = "option") -> dict:
    """شراءٌ بسعر العرض (أو سعرِ المالك اليدويّ) وعمولةِ السوق — يُخصم من النقد. والسهمُ بلا أجلٍ ولا تنفيذ."""
    px = float(px if px is not None else k["ask"])
    m = 100 if kind == "option" else 1
    fee = fee_of(st.get("market", "us"), kind, qty, px)
    cost = round(px * m * qty + fee, 2)
    st["cash"] = round(st["cash"] - cost, 2)
    stop = k.get("stop") or (px * (STOP if kind == "option" else STOCK_STOP))
    p = {"id": _pid(k["contract"]), "kind": kind, "contract": k["contract"], "symbol": k["symbol"], "name": k.get("name"),
         "type": k.get("type", "stock"), "strike": k.get("strike"), "expiry": k.get("expiry"), "t": k.get("t"),
         "qty": int(qty) if kind == "option" else round(float(qty), 4), "entry_px": round(px, 4), "cost": cost, "fee_in": fee, "opened": _iso(),
         "stop": round(stop, 4), "stop0": round(stop, 4), "peak": float(k.get("bid") or px), "bid": k.get("bid"), "ask": k.get("ask"), "S": k.get("price"),
         "S0": k.get("price"), "target": k.get("target"), "target_label": k.get("target_label"), "delta": k.get("delta"),
         "iv": k.get("iv"), "dte0": k.get("dte"), "why": why, "src": src, "auto": src == "saqr", "marked": _iso()}
    st["positions"].append(p)
    return p


def sell(st: dict, pid: str, px: float, reason: str, note: str = "") -> dict | None:
    """بيعٌ بسعر الطلب (أو سعرِ المالك اليدويّ) وعمولةٍ لكلّ عقد — يُضاف إلى النقد، ويُنقل المركزُ إلى المغلقة بربحه بعد العمولات."""
    p = next((x for x in st["positions"] if x["id"] == pid), None)
    if not p:
        return None
    fee = fee_of(st.get("market", "us"), kind_of(p), p["qty"], px)
    proceeds = round(px * mult(p) * p["qty"] - fee, 2)
    st["cash"] = round(st["cash"] + proceeds, 2)
    st["positions"] = [x for x in st["positions"] if x["id"] != pid]
    pl = round(proceeds - p["cost"], 2)
    c = {**p, "exit_px": round(px, 4), "proceeds": proceeds, "fee_out": fee, "pl": pl, "pl_pct": round(pl / p["cost"] * 100, 1) if p["cost"] else None,
         "closed": _iso(), "reason": reason, "reason_ar": REASON_AR.get(reason, reason), "note": note}
    st["closed"] = ([c] + st["closed"])[:500]
    return c


# ══ القواعد (دوالُّ صافية — يختبرها الحارس) ══

def trail(p: dict, bid: float) -> None:
    """الوقفُ المتحرّك — لا ينزل أبداً. العقد: من +50٪ إلى سعر الدخول ومن +80٪ إلى 75٪ من القمّة؛ السهم: من +8٪ إلى الدخول ومن +12٪
    إلى 94٪ من القمّة."""
    be, on, keep = (TRAIL_BE, TRAIL_ON, TRAIL_KEEP) if kind_of(p) == "option" else STOCK_TRAIL
    p["peak"] = max(float(p.get("peak") or 0), bid)
    e = p["entry_px"]
    if p["peak"] >= e * be:
        p["stop"] = max(p["stop"], e)
    if p["peak"] >= e * on:
        p["stop"] = max(p["stop"], round(p["peak"] * keep, 4))


def exit_rule(p: dict, bid: float | None, S: float | None, dte: int, tr: dict | None, news: dict | None) -> tuple[str, str] | None:
    """(السبب، الشرح) إن وجب الخروج — وإلا None. الترتيب: الأجلُ ثمّ الوقفُ ثمّ الجنيُ ثمّ الهدفُ ثمّ الأطروحة."""
    stock = kind_of(p) == "stock"
    call = stock or p["type"] == "call"
    base = STOCK_STOP if stock else STOP
    if not stock and dte <= EXIT_DTE:
        return "time", f"بقي {dte} يوماً على الانتهاء — يتسارع التآكل."
    if bid is not None and bid > 0:
        if bid <= p["stop"]:
            moved = p["stop"] > (p.get("stop0") or p["entry_px"] * base) + 1e-9
            return ("trail" if moved else "stop"), (f"سعرُ الطلب {bid:.2f} عند الوقف {p['stop']:.2f}"
                                                   + (f" (رُفع بعد قمّة {p['peak']:.2f})" if moved else
                                                      f" — {round((p.get('stop0') or p['entry_px'] * base) / p['entry_px'] * 100)}٪ من سعر الشراء {p['entry_px']:.2f}") + ".")
        if stock and p.get("opened"):
            held = (_now() - datetime.fromisoformat(p["opened"])).days
            if held >= STOCK_TIME_DAYS and bid < p["entry_px"] * STOCK_TIME_GAIN:
                return "stale", f"مضى {held} يوماً ولم يتقدّم السهمُ 3٪ — يُحرَّر المالُ لفرصةٍ أفضل."
        if not stock and bid >= p["entry_px"] * TAKE:
            return "take", f"تضاعف العقد: {p['entry_px']:.2f} ⇐ {bid:.2f}."
    if S is not None and p.get("target") and ((call and S >= p["target"]) or (not call and S <= p["target"])):
        return "target", f"بلغ السهمُ {S:,.2f} الهدفَ {p['target']:,.2f}."
    if tr:
        # السهمُ مركزُ شراءٍ (كعقد الشراء) — لا يُقرأ «stock» بيعاً فيُكسر مع كلّ مسارٍ صاعد
        v, why = OP.verdict({"type": "call" if call else "put", "target": p.get("target") or (math.inf if call else 0)}, None, None, 999, tr, news)
        if v == "broken":
            return "broken", why
    return None


def us_clock(now: datetime | None = None) -> tuple[datetime, datetime] | None:
    """(افتتاحُ الجلسة الرسمية، إغلاقُها) لليوم الأمريكيّ — أو None للعطلة ونهاية الأسبوع."""
    from app.services.market_session import NY, _us_day
    n = (now or _now()).astimezone(NY)
    day = _us_day(n.date())
    if not day:
        return None
    return datetime.combine(n.date(), day[2], NY), datetime.combine(n.date(), day[3], NY)


def event_block(events: list[dict], now: datetime) -> dict | None:
    """حدثٌ عالي الأثر يمنع الدخول: قبله بساعتين (والفيدراليُّ بيومٍ كامل) وبعده بنصف ساعة."""
    for e in events or []:
        if e.get("impact") != "High":
            continue
        try:
            at = datetime.fromisoformat(e["at"])
        except (KeyError, ValueError):
            continue
        fed = any(w.lower() in str(e.get("title") or "").lower() for w in FED_RX)
        if at - timedelta(hours=FED_BEFORE_H if fed else EVENT_BEFORE_H) <= now <= at + timedelta(minutes=EVENT_AFTER_M):
            return e
    return None


def gates(st: dict, now: datetime, clock: tuple[datetime, datetime] | None, events: list[dict]) -> list[str]:
    """ما يمنع الدخولَ الجديد الآن (فارغةٌ = مفتوح)؛ والخروجُ لا تمنعه بوّابة."""
    out = []
    if not st.get("on"):
        out.append("صقرٌ موقوفٌ بأمر المالك.")
    if not clock or not (clock[0] <= now <= clock[1]):
        out.append("خارج الجلسة الرسمية.")
    else:
        if now < clock[0] + timedelta(minutes=OPEN_WAIT):
            out.append("أوّلُ ربع ساعةٍ من الجلسة: الفوارقُ واسعةٌ والأسعارُ مضطربة — لا دخول.")
        if now > clock[1] - timedelta(minutes=CLOSE_WAIT):
            out.append("آخرُ عشرين دقيقةً من الجلسة — لا دخولَ جديد.")
    ev = event_block(events, now)
    if ev:
        out.append(f"حدثٌ اقتصاديٌّ عالي الأثر: {ev.get('title')} ({ev.get('riyadh', '')[-5:]} بتوقيت الرياض) — لا دخولَ حوله.")
    eq, d = equity(st), st.get("day") or {}
    if d.get("start_eq") and eq <= d["start_eq"] * (1 - DAY_LOSS):
        out.append(f"قاطعُ اليوم: الخسارةُ اليوم {(1 - eq / d['start_eq']) * 100:.0f}٪ — لا دخولَ حتى الغد.")
    if (d.get("new") or 0) >= MAX_NEW_DAY:
        out.append(f"بلغ صقرٌ {MAX_NEW_DAY} صفقاتٍ اليوم — حدُّه اليوميّ.")
    return out


def cooling(st: dict, sym: str, now: datetime) -> bool:
    lim = (now - timedelta(days=COOL_DAYS)).isoformat()
    return any(c["symbol"] == sym and c["reason"] in ("stop", "broken") and c["closed"] >= lim for c in st["closed"])


def size(budget: float, ask: float) -> int:
    """أكبرُ عددِ عقودٍ تتّسع له الميزانيةُ مع العمولة."""
    one = ask * 100 + FEE
    return int(budget // one) if one > 0 else 0


def pick_expiries(exps: list[dict]) -> list[dict]:
    win = [e for e in exps if MIN_DTE <= e["dte"] <= MAX_DTE]
    out = []
    for t in EXP_TARGETS:
        if win:
            e = min(win, key=lambda x: abs(x["dte"] - t))
            if e not in out:
                out.append(e)
    return out


# ══ السوق ══

async def movers() -> list[str]:
    """الأنشطُ تداولاً اليومَ في السوق الأمريكيّ كلّه (قيمةُ التداول ثمّ الحجمُ النسبيّ) — أسهمٌ وصناديقُ فوق ملياري دولار وحجمٍ يوميٍّ كبير؛
    مخبّأةٌ نصفَ ساعة. ‏TradingView ببصمة المتصفّح (‏docs/FETCH_METHOD.md)."""
    from app.services import cache
    hit = cache.get("saqr:movers")
    if hit is not None:
        return hit

    def blocking(sort_by: str, n: int) -> list[str]:
        from curl_cffi import requests as cr
        body = {"filter": [{"left": "market_cap_basic", "operation": "greater", "right": 2e9},
                           {"left": "close", "operation": "greater", "right": 3},
                           {"left": "average_volume_10d_calc", "operation": "greater", "right": 2e6},
                           {"left": "type", "operation": "in_range", "right": ["stock", "fund"]},
                           {"left": "exchange", "operation": "in_range", "right": ["NASDAQ", "NYSE", "AMEX"]}],
                "columns": ["name", "close", "change", "relative_volume_10d_calc", "Value.Traded"],
                "sort": {"sortBy": sort_by, "sortOrder": "desc"}, "range": [0, n]}
        with cr.Session(impersonate="chrome") as s:
            r = s.post("https://scanner.tradingview.com/america/scan", data=json.dumps(body), timeout=10,
                       headers={"Content-Type": "application/json", "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"})
        if r.status_code != 200:
            return []
        return [str((row.get("d") or [""])[0]).upper() for row in (json.loads(r.text or "{}").get("data") or []) if row.get("d")]
    out: list[str] = []
    for sort_by, n in (("Value.Traded", 50), ("relative_volume_10d_calc", 20)):
        try:
            for s in await asyncio.to_thread(blocking, sort_by, n):
                if s and s.replace(".", "").isalnum() and s not in out:
                    out.append(s.replace(".", "-"))
        except Exception as e:                                    # noqa: BLE001
            logger.debug("صقر/الأنشط: {}", type(e).__name__)
    if out:
        cache.set("saqr:movers", out, 1800)
    return out


async def trends() -> tuple[dict, int]:
    """مسارُ كلِّ رمزٍ في مجال صقر: القائمةُ الأسيلُ (مخبّأة) والأنشطُ اليوم (يُحسب لما ليس فيها ويُخبَّأ ستّ ساعات)؛ ومعه عددُ الأنشط."""
    from app.services import cache
    from app.services.market_data import market_service as M
    sc = dict(await OP.scan())
    extra = [s for s in await movers() if s not in sc][:40]
    sem = asyncio.Semaphore(6)

    async def one(s):
        hit = cache.get(f"saqr:tr:{s}")
        if hit is not None:
            return s, hit
        async with sem:
            try:
                bars = await asyncio.wait_for(M.get_bars(s, "1d"), 25) or []
            except Exception:                                     # noqa: BLE001
                return s, None
        tr = OP.trend_of(bars)
        if tr:
            cache.set(f"saqr:tr:{s}", tr, 6 * 3600)
        return s, tr
    for s, tr in await asyncio.gather(*(one(s) for s in extra)):
        if tr and tr["close"] >= OP.MIN_PRICE:
            sc[s] = tr
    return sc, len(extra)


async def quote_position(p: dict) -> tuple[float | None, float | None, float | None, int]:
    """(الطلب، العرض، سعرُ السهم، الأيامُ الباقية) لمركزٍ قائم — حيّان من السلسلة، وللسهم الأمريكيّ من ياهو المباشر."""
    from app.services.options_chain import chain
    if kind_of(p) == "stock":
        from app.services.live_quote import yahoo_quotes
        row = (await yahoo_quotes([p["symbol"]])).get(p["symbol"]) or {}
        last = row.get("regularMarketPrice")
        bid = row.get("bid") or None
        ask = row.get("ask") or None
        if not bid and isinstance(last, (int, float)):
            bid = round(last * 0.9995, 4)
        return bid, ask, (float(last) if isinstance(last, (int, float)) else None), 999
    dte = max(0, (datetime.fromisoformat(p["expiry"]).date() - _now().date()).days)
    t = p.get("t")
    if not t:
        base = await chain(p["symbol"])
        e = next((x for x in (base or {}).get("expirations") or [] if x["date"] == p["expiry"]), None)
        t = p["t"] = e["t"] if e else None
    ch = await chain(p["symbol"], t) if t else None
    if not ch:
        return None, None, None, dte
    row = next((r for r in ch["calls" if p["type"] == "call" else "puts"] if r.get("contract") == p["contract"]), None)
    S = float(ch.get("price") or 0) or None
    if not row:
        return None, None, S, dte
    return (row.get("bid") or None), (row.get("ask") or None), S, dte


async def best_for(sym: str, call: bool, budget: float, tr: dict, ctx: dict) -> tuple[dict | None, str]:
    """أفضلُ عقدٍ لسهمٍ واتّجاه ضمن ميزانية الصفقة: آجالُ 21–200 يوماً، وقواعدُ صقر، وعرضٌ وطلبٌ حيّان، وتآكلٌ ≤ 3٪، ثمّ حكمُ المستشار."""
    from app.services import option_advisor as AD
    from app.services.options_chain import chain
    base = await chain(sym)
    if not base or not base.get("price"):
        return None, "لا سلسلةَ خيارات"
    best, why, cheapest = None, "لا عقدَ يستوفي قواعد صقر", None
    for e in pick_expiries(base.get("expirations") or []):
        ch = await chain(sym, e["t"])
        if not ch:
            continue
        S = float(ch["price"] or base["price"])
        T = max(e["dte"], 1) / 365
        ref = OP.atm_iv(ch, S, T)
        if ref is None:
            continue
        rows = ch["calls"] if call else ch["puts"]
        for k in OP.candidates(rows, S, e["dte"], call, tr, ref_iv=ref, rules=RULES):
            if k["px_src"] != "ask":
                continue
            one = k["ask"] * 100 + FEE
            cheapest = one if cheapest is None else min(cheapest, one)
            if one > budget:
                continue
            row = dict(next((r for r in rows if r.get("contract") == k["contract"]), {}))
            AD.enrich_rows([row], S, e["dte"], call)
            g = row.get("g") or {}
            burn = -g.get("theta", 0) / (k["ask"] * 100) if k["ask"] > 0 and g.get("theta", 0) < 0 else 0
            if burn > MAX_BURN:
                continue
            if best is None or k["score"] > best["score"]:
                best = {**k, "expiry": e["date"], "t": e["t"], "symbol": sym, "name": base.get("name"), "price": S, "row": row,
                        "theta": g.get("theta"), "gamma": g.get("gamma"), "vega": g.get("vega")}
    if not best:
        return None, (f"{why} ضمن {budget:,.0f} دولار — أرخصُ عقدٍ صالح {cheapest:,.0f}" if cheapest else why)
    lvl, pros, cons = AD.judge(best["row"], call, best["price"], best["dte"], ctx, best["expiry"])
    best.update(verdict=lvl, pros=pros, cons=cons)
    best.pop("row", None)
    if lvl != "ok":
        return None, "المستشار: " + (cons[0] if cons else "بحذر")
    return best, ""


def thesis(sym: str, call: bool, tr: dict, news: dict | None, k: dict, chg: float | None) -> list[str]:
    out = [f"المسارُ {tr['state']}: الإغلاق {tr['close']:,.2f} و{'فوق' if tr['close'] >= tr['sma200'] else 'دون'} متوسّط 200 ({tr['sma200']:,.2f})، "
           f"وتغيّرُ ثلاثة أشهر {tr['ret3m']:+.1f}٪."]
    if news and news.get("impact") and news.get("impact") != "محايد":
        out.append(f"الأخبار ({news['impact']}): {news.get('event') or ''}".strip())
    if chg is not None:
        out.append(f"حركةُ اليوم {chg:+.2f}٪ — لا تعاكس الصفقة.")
    out.append(f"العقد: دلتا {k['delta']:+.2f} · تذبذب {k['iv']:.0f}٪ · تآكل {abs(k.get('theta') or 0):.2f} دولار يومياً · "
               f"احتمالُ الربح {k['pop']:.0f}٪ · فارق {k['spread_pct']:.1f}٪.")
    out.append(f"الهدف {k['target']:,.2f} ({k['target_label']}) والتعادل {k['breakeven']:,.2f} — العائدُ عند الهدف {k['rr']:.1f}× الكلفة.")
    out.extend((k.get("pros") or [])[:2])
    return out


def stock_pick(sym: str, row: dict, tr: dict, budget: float) -> dict | None:
    """السهمُ الأمريكيّ بدلَ عقده: العرضُ الحيّ (أو آخرُ سعرٍ بانزلاقٍ صغير)، وكمّيةٌ تتّسع لها الميزانيةُ مع العمولة (جزءٌ من السهم
    بأربعة منازل)، ووقفٌ −7٪، والهدفُ قمّةُ السنة إن بعدت 5٪ فأكثر وإلا +15٪."""
    last = row.get("regularMarketPrice")
    ask = row.get("ask") or (round(last * 1.0005, 4) if isinstance(last, (int, float)) else None)
    bid = row.get("bid") or (round(last * 0.9995, 4) if isinstance(last, (int, float)) else None)
    if not ask or ask <= 0 or budget < 5:
        return None
    qty = math.floor((budget - 0.35) / ask * 10_000) / 10_000
    while qty > 0 and qty * ask + fee_of("us", "stock", qty, ask) > budget:
        qty = math.floor(qty * 0.995 * 10_000) / 10_000
    if qty * ask < 5:
        return None
    hi = tr.get("hi52") or 0
    tgt, lbl = (hi, "قمّة السنة") if hi >= ask * 1.05 else (round(ask * 1.15, 2), "+15٪")
    return {"contract": sym, "symbol": sym, "name": row.get("shortName"), "type": "stock", "ask": ask, "bid": bid, "price": last or ask,
            "qty": qty, "stop": round(ask * STOCK_STOP, 4), "target": round(tgt, 2), "target_label": lbl}


def stock_thesis(tr: dict, news: dict | None, chg: float | None, why_not_option: str, k: dict) -> list[str]:
    out = [f"المسارُ {tr['state']}: الإغلاق {tr['close']:,.2f} و{'فوق' if tr['close'] >= tr['sma200'] else 'دون'} متوسّط 200 ({tr['sma200']:,.2f})، "
           f"وتغيّرُ ثلاثة أشهر {tr['ret3m']:+.1f}٪."]
    if news and news.get("impact") and news.get("impact") != "محايد":
        out.append(f"الأخبار ({news['impact']}): {news.get('event') or ''}".strip())
    out.append(f"لماذا السهمُ لا العقد: {why_not_option}")
    if chg is not None:
        out.append(f"حركةُ اليوم {chg:+.2f}٪ — لا تعاكس الصفقة.")
    out.append(f"الوقف {k['stop']:.2f} (−7٪) والهدف {k['target']:,.2f} ({k['target_label']}).")
    return out


# ══ الدورة ══

async def _notify(text: str) -> None:
    try:
        from app.services.saqr_bot import bot
        if bot.enabled:
            await bot.send(text, keyboard=False)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("صقر/تلغرام: {}", type(e).__name__)


def _title(p: dict) -> str:
    if kind_of(p) == "stock":
        return f"{p['symbol']}{(' ' + p['name']) if p.get('name') else ''} · سهم"
    return f"{p['symbol']} {'Call' if p['type'] == 'call' else 'Put'} {p['strike']:g} · {p['expiry']}"


def _roll_day(st: dict, now: datetime) -> None:
    from app.services.market_session import NY
    d = now.astimezone(NY).date().isoformat()
    if (st.get("day") or {}).get("date") != d:
        st["day"] = {"date": d, "start_eq": equity(st), "new": 0}


def _point(st: dict) -> None:
    eq = equity(st)
    pts = st.setdefault("equity", [])
    if pts and pts[-1][0][:16] == _iso()[:16]:
        pts[-1] = [_iso(), eq]
    else:
        pts.append([_iso(), eq])
    st["equity"] = pts[-2500:]


async def _review(st: dict, now: datetime, scan_tr: dict | None) -> list[dict]:
    """مراجعةُ المراكز: سعرُها الحيّ ووقفُها المتحرّك وقاعدةُ خروجها — صقرٌ يبيع مراكزَه، ومراكزُ المالك اليدوية يُنبَّه عليها ولا تُمسّ."""
    from app.services import cache
    out = []
    for p in list(st["positions"]):
        bid, ask, S, dte = await quote_position(p)
        if bid:
            p.update(bid=bid, marked=_iso())
            trail(p, bid)
        if ask:
            p["ask"] = ask
        if S:
            p["S"] = S
        tr = (scan_tr or cache.get("optpicks:scan:v3") or {}).get(p["symbol"]) or cache.get(f"saqr:tr:{p['symbol']}")
        news = cache.get(f"optpicks:news:{p['symbol']}")
        r = exit_rule(p, bid, S, dte, tr, news)
        if not r:
            continue
        code, why = r
        if not p.get("auto"):
            if p.get("alert") != code:
                p["alert"] = code
                log(st, "alert", f"إشارةُ خروجٍ لمركزك اليدويّ {_title(p)}: {REASON_AR[code]} — {why}", p["symbol"])
                await _notify(f"🦅 <b>صقر — إشارةُ خروج</b>\n{html.escape(_title(p))}\n{html.escape(REASON_AR[code])}: {html.escape(why)}")
            continue
        if not bid:
            log(st, "info", f"{_title(p)}: {REASON_AR[code]} لكن لا طلبَ الآن — يُعاد في الدورة التالية.", p["symbol"])
            continue
        c = sell(st, p["id"], bid, code, why)
        if c:
            out.append(c)
            unit = "عقد" if kind_of(c) == "option" else "سهم"
            log(st, "sell", f"بيع {c['qty']:g} {unit} × {_title(c)} بسعر {bid:.2f} — {REASON_AR[code]}: {why} · النتيجة {c['pl']:+,.2f} دولار ({c['pl_pct']:+.1f}٪) بعد العمولات.",
                c["symbol"])
            await _notify(f"🦅 <b>صقر — بيع</b>\n{html.escape(_title(c))}\n{c['qty']:g} {unit} × {bid:.2f} · {html.escape(REASON_AR[code])}\n"
                          f"النتيجة {c['pl']:+,.2f}$ ({c['pl_pct']:+.1f}٪) بعد العمولات\nرأس المال الآن {equity(st):,.2f}$")
    return out


async def _hunt(st: dict, now: datetime) -> dict | None:
    """البحثُ عن صفقةٍ جديدة ودخولُها — يُكتب كلُّ مرفوضٍ بسببه في الإشارات."""
    from app.services import option_advisor as AD
    from app.services.live_quote import yahoo_quotes
    eq = equity(st)
    frac, seats = tier(eq)
    if len(st["positions"]) >= seats:
        return None
    budget = min(st["cash"], eq * frac)
    if budget < 10:
        st["signals"] = [{"at": _iso(), "sym": "—", "verdict": "refused", "why": f"النقدُ المتاح {st['cash']:,.2f} دولار لا يكفي عقداً."}]
        return None
    _JOB["msg"] = "قراءةُ مسارات السوق"
    tr_all, n_movers = await trends()
    held = {p["symbol"] for p in st["positions"]}
    pool = [s for s, t in sorted(tr_all.items(), key=lambda kv: -kv[1]["strength"])
            if s not in held and not cooling(st, s, now)][:SHORTLIST]
    _JOB["msg"] = "قراءةُ الأخبار"
    try:
        news = await OP.read_news({s: tr_all[s] for s in pool})
    except Exception:                                             # noqa: BLE001
        news = {}
    st["health"]["news"] = bool(news)
    sig, picks = [], []
    sides = {}
    for s in pool:
        side, note = OP.direction(tr_all[s], news.get(s))
        if side:
            sides[s] = side
        else:
            sig.append({"sym": s, "verdict": "refused", "why": note})
    q = await yahoo_quotes(list(sides)) if sides else {}
    deep = []
    for s, side in sides.items():
        row = q.get(s) or {}
        chg = row.get("regularMarketChangePercent")
        et = row.get("earningsTimestamp")
        if isinstance(chg, (int, float)) and ((side == "call" and chg < -FIGHT_PCT) or (side == "put" and chg > FIGHT_PCT)):
            sig.append({"sym": s, "side": side, "verdict": "refused", "why": f"حركةُ اليوم {chg:+.1f}٪ تعاكس الصفقة — ينتظر."})
            continue
        if isinstance(et, (int, float)) and 0 <= et - now.timestamp() <= EARN_DAYS * 86400:
            sig.append({"sym": s, "side": side, "verdict": "refused",
                        "why": f"أرباحُ الشركة {datetime.fromtimestamp(et, timezone.utc).date().isoformat()} — ينهار التذبذبُ بعدها."})
            continue
        deep.append((s, side, chg if isinstance(chg, (int, float)) else None))
    _JOB["msg"] = "فحصُ العقود ويونانياتها"
    stock_alt: list[tuple[str, float | None, str]] = []
    for s, side, chg in deep[:DEEP]:
        try:
            ctx = await AD._context(s)
            k, why = await best_for(s, side == "call", budget, tr_all[s], ctx)
        except Exception as e:                                    # noqa: BLE001
            k, why = None, f"تعذّر الفحص ({type(e).__name__})"
        if k:
            k["chg"] = chg
            picks.append(k)
            sig.append({"sym": s, "side": side, "verdict": "accepted", "contract": k["contract"], "score": k["score"],
                        "why": f"دلتا {k['delta']:+.2f} · احتمالُ ربح {k['pop']:.0f}٪ · عائدٌ عند الهدف {k['rr']:.1f}× · كلفة {k['cost']:,.0f}$"})
        else:
            sig.append({"sym": s, "side": side, "verdict": "refused", "why": why})
            if side == "call" and "سلسلة" not in why and "تعذّر" not in why:
                stock_alt.append((s, chg, why))
        if len(picks) >= 3:
            break
    st["health"]["quotes"] = _iso() if (q or picks) else st["health"].get("quotes")
    chosen = max(picks, key=lambda k: k["score"]) if picks else None
    pos = None
    if chosen:
        qty = size(budget, chosen["ask"])
        if qty >= 1:
            pos = buy(st, chosen, qty, thesis(chosen["symbol"], chosen["type"] == "call", tr_all[chosen["symbol"]],
                                             news.get(chosen["symbol"]), chosen, chosen.get("chg")))
            st["day"]["new"] = (st["day"].get("new") or 0) + 1
            for x in sig:
                if x.get("contract") == chosen["contract"]:
                    x["verdict"] = "chosen"
            log(st, "buy", f"شراء {qty} × {_title(pos)} بسعر {pos['entry_px']:.2f} (الكلفة مع العمولة {pos['cost']:,.2f}$) — "
                           f"الوقف {pos['stop']:.2f} والهدف {pos['target']:,.2f}.", pos["symbol"])
            await _notify(f"🦅 <b>صقر — شراء</b>\n{html.escape(_title(pos))}\n{qty} عقد × {pos['entry_px']:.2f} = {pos['cost']:,.2f}$ مع العمولة\n"
                          f"الوقف {pos['stop']:.2f} · الهدف {pos['target']:,.2f}\n" + html.escape(pos["why"][0]))
    elif stock_alt:
        # ‏D764: «السوقُ الأمريكيّ له كاملُ الصلاحية — عقودٌ وأسهم»: مسارٌ صاعدٌ وعقودُه غيرُ مناسبة الآن (تذبذبٌ غالٍ أو فارقٌ واسع أو
        # ميزانيةٌ لا تتّسع) ⇐ السهمُ نفسُه، بالعرض الحيّ وجزءٍ من السهم إن لزم (يدعمه IBKR)، ووقفٍ −7٪ وهدفٍ فنيّ
        s0, chg0, why0 = stock_alt[0]
        k = stock_pick(s0, q.get(s0) or {}, tr_all[s0], budget)
        if k:
            pos = buy(st, k, k["qty"], stock_thesis(tr_all[s0], news.get(s0), chg0, why0, k), kind="stock")
            st["day"]["new"] = (st["day"].get("new") or 0) + 1
            sig.append({"sym": s0, "side": "call", "verdict": "chosen", "contract": s0,
                        "why": f"السهمُ نفسُه بدل العقد ({why0}) — {pos['qty']:g} سهم × {pos['entry_px']:.2f}"})
            log(st, "buy", f"شراء {pos['qty']:g} سهم من {s0} بسعر {pos['entry_px']:.2f} (الكلفة مع العمولة {pos['cost']:,.2f}$) — "
                           f"الوقف {pos['stop']:.2f} والهدف {pos['target']:,.2f}.", s0)
            await _notify(f"🦅 <b>صقر — شراء سهم</b>\n{html.escape(_title(pos))}\n{pos['qty']:g} سهم × {pos['entry_px']:.2f} = {pos['cost']:,.2f}$ مع العمولة\n"
                          f"الوقف {pos['stop']:.2f} · الهدف {pos['target']:,.2f}\n" + html.escape(pos["why"][0]))
    st["signals"] = [{"at": _iso(), **x} for x in sig][:60]
    st["scan_meta"] = {"at": _iso(), "universe": len(tr_all), "movers": n_movers, "pool": len(pool), "deep": min(len(deep), DEEP),
                       "budget": round(budget, 2), "tier": {"frac": frac, "seats": seats}}
    return pos


async def cycle(force: bool = False) -> dict:
    """دورةُ صقر: في الجلسة الرسمية وحدها — مراجعةُ المراكز كلَّ دورة، والبحثُ عن جديدٍ كلَّ عشرين دقيقة (أو بأمر المالك)."""
    from app.services.econ_calendar import raw_week, shape
    from app.services.live_quote import sessions
    async with _LOCK:
        _JOB.update(on=True, msg="يبدأ", at=_iso())
        try:
            st = load()
            now = _now()
            ses = (await sessions()).get("us") or {}
            st["session"] = {k: ses.get(k) for k in ("state", "label", "detail", "next", "holiday")}
            st["last_check"] = _iso()
            if ses.get("state") != "open":
                save(st)
                return {"ran": False, "why": f"السوقُ الأمريكيّ {ses.get('label') or 'مغلق'} — صقرٌ يعمل في الجلسة الرسمية وحدها."}
            _roll_day(st, now)
            _JOB["msg"] = "مراجعةُ المراكز"
            exits = await _review(st, now, None)
            try:
                events = shape(await raw_week(), impacts=("High",))
                st["health"]["events"] = True
            except Exception:                                     # noqa: BLE001
                events, st["health"]["events"] = [], False
            g = gates(st, now, us_clock(now), events)
            st["gates"] = g
            pos = None
            due = force or not st.get("last_scan") or (now - datetime.fromisoformat(st["last_scan"])).total_seconds() >= SCAN_EVERY - 30
            if not g and due:
                st["last_scan"] = _iso()
                pos = await _hunt(st, now)
            st["last_cycle"] = _iso()
            st["cycles"] = (st.get("cycles") or 0) + 1
            _point(st)
            save(st)
            return {"ran": True, "exits": len(exits), "bought": pos["contract"] if pos else None, "gates": g, "equity": equity(st)}
        except Exception as e:                                    # noqa: BLE001
            logger.warning("صقر: {}", type(e).__name__)
            return {"ran": False, "why": f"تعذّرت الدورة ({type(e).__name__})"}
        finally:
            _JOB.update(on=False, msg="")


# ══ أوامرُ المالك — تعديلاتُه تتقدّم على الحساب الآليّ ══

async def _stock_quote(market: str, sym: str) -> tuple[float | None, float | None, str | None]:
    """(العرض، الطلب، الاسم) لسهمٍ — السعوديُّ من لقطة «تداول» الحيّة، والأمريكيُّ من ياهو المباشر."""
    if _mk(market) == "sa":
        from app.services import tadawul_market as TM
        r = TM.snapshot().get(sym.replace(".SR", "")) or {}
        return r.get("ask") or r.get("price"), r.get("bid") or r.get("price"), r.get("name_en")
    from app.services.live_quote import yahoo_quotes
    r = (await yahoo_quotes([sym])).get(sym) or {}
    last = r.get("regularMarketPrice")
    return (r.get("ask") or last), (r.get("bid") or last), r.get("shortName")


async def manual_open(contract: str, qty: float, price: float | None = None, market: str = "us") -> dict:
    """مركزٌ نفّذه المالك بنفسه: عقدٌ أمريكيّ (رمزُ OCC) أو سهمٌ أمريكيّ أو سعوديّ — بسعره إن كتبه وإلا بسعر العرض الحيّ."""
    from app.services.options_chain import chain, parse_option
    market = _mk(market)
    sym = str(contract or "").strip().upper().replace(".SR", "")
    o = parse_option(sym) if market == "us" else None
    if not sym or qty <= 0:
        raise ValueError("رمزٌ غيرُ صالح أو كمّيةٌ صفر.")
    async with _LOCK:
        st = load(market)
        if o:
            base = await chain(o["root"])
            e = next((x for x in (base or {}).get("expirations") or [] if x["date"] == o["expiry"]), None)
            ch = await chain(o["root"], e["t"]) if e else None
            row = next((r for r in (ch or {}).get("calls" if o["type"] == "call" else "puts", []) if r.get("contract") == sym), None)
            ask = price or (row or {}).get("ask") or (row or {}).get("sask")
            if not ask:
                raise ValueError("لا سعرَ عرضٍ لهذا العقد الآن — اكتب سعرَ التنفيذ الذي نفّذتَ به.")
            k = {"contract": sym, "symbol": o["root"], "type": o["type"], "strike": o["strike"], "expiry": o["expiry"],
                 "t": e["t"] if e else None, "ask": float(ask), "bid": (row or {}).get("bid"), "price": (ch or {}).get("price"), "target": None}
            p = buy(st, k, int(qty), ["مركزٌ أدخله المالك يدوياً."], src="manual", px=float(ask))
        else:
            if market == "sa" and not (sym.isdigit() and len(sym) == 4):
                raise ValueError("رمزُ الشركة السعودية أربعةُ أرقام (مثل 2222).")
            ask, bid, name = await _stock_quote(market, sym)
            ask = price or ask
            if not ask:
                raise ValueError("لا سعرَ لهذا السهم الآن — اكتب السعرَ الذي نفّذتَ به.")
            k = {"contract": sym, "symbol": sym, "name": name, "type": "stock", "ask": float(ask), "bid": bid, "price": ask, "target": None}
            p = buy(st, k, float(qty), ["مركزٌ أدخله المالك يدوياً."], src="manual", px=float(ask), kind="stock")
        log(st, "manual", f"المالك أدخل {p['qty']:g} × {_title(p)} بسعر {p['entry_px']:.2f}.", p["symbol"])
        _point(st)
        save(st)
        return p


async def manual_close(pid: str, price: float | None = None, market: str = "us") -> dict:
    market = _mk(market)
    async with _LOCK:
        st = load(market)
        p = next((x for x in st["positions"] if x["id"] == pid), None)
        if not p:
            raise ValueError("لا مركزَ بهذا المعرّف.")
        px = price
        if px is None:
            if market == "sa":
                _, bid, _ = await _stock_quote("sa", p["symbol"])
            else:
                bid, _, _, _ = await quote_position(p)
            px = bid or p.get("bid")
        if not px:
            raise ValueError("لا سعرَ طلبٍ الآن — اكتب السعرَ الذي بعتَ به.")
        c = sell(st, pid, float(px), "manual", "أغلقه المالك.")
        log(st, "manual", f"المالك أغلق {_title(c)} بسعر {float(px):.2f} — النتيجة {c['pl']:+,.2f}.", c["symbol"])
        _point(st)
        save(st)
        return c


async def set_capital(amount: float, market: str = "us") -> dict:
    """بدءُ تجربةٍ جديدة برأس مالٍ يحدّده المالك (والهدفُ مئةُ ضعفه) — والتجربةُ السابقة تُحفظ ملخّصةً في «التجارب»."""
    market = _mk(market)
    async with _LOCK:
        old = load(market)
        st = fresh(amount, old.get("on", True), market)
        if old.get("closed") or old.get("positions"):
            st["runs"] = ([{"started": old["started"], "ended": _iso(), "capital": old["capital"], "equity": equity(old),
                            "trades": len(old["closed"])}] + old.get("runs", []))[:20]
        log(st, "info", f"بدأت تجربةٌ جديدة برأس مال {amount:,.2f} {st['ccy']} — والهدف {st['goal']:,.0f}.")
        save(st)
        return st


async def toggle(on: bool, market: str = "us") -> dict:
    async with _LOCK:
        st = load(market)
        st["on"] = bool(on)
        log(st, "info", "شغّل المالكُ صقراً." if on else "أوقف المالكُ صقراً — لا دخولَ جديد، والمراكزُ تُراجَع بقواعد خروجها.")
        save(st)
        return st


# ══ العرض ══

def _sa_job() -> dict:
    from app.services import saqr_sa as SA
    return dict(SA._JOB)


def _sa_rules() -> dict:
    from app.services import saqr_sa as SA
    return SA.rules()


def view(market: str = "us") -> dict:
    """حالُ صقر للوحة: الملخّصُ والمراكزُ والمغلقةُ والمنحنى والإشاراتُ والسجلُّ وحالُ الأنظمة."""
    market = _mk(market)
    st = load(market)
    eq = equity(st)
    closed = st["closed"]
    wins = [c for c in closed if c["pl"] > 0]
    from app.services.market_session import NY
    today = _now().astimezone(NY).date().isoformat()
    tday = [c for c in closed if datetime.fromisoformat(c["closed"]).astimezone(NY).date().isoformat() == today]
    cost_open = sum(p["cost"] for p in st["positions"])
    val_open = sum(mark_of(p) for p in st["positions"])
    if market == "sa":
        from app.services import saqr_sa as SA
        frac, seats = SA.tier(eq)
    else:
        frac, seats = tier(eq)
    try:
        from app.services.saqr_bot import bot
        tg = bool(bot.enabled)
    except Exception:                                             # noqa: BLE001
        tg = False
    pts = st.get("equity") or []
    return {
        "market": market, "ccy": st.get("ccy", "USD"), "on": st.get("on"), "capital": st["capital"], "goal": st.get("goal", GOAL), "cash": st["cash"], "equity": eq,
        "pl": round(eq - st["capital"], 2), "pl_pct": round((eq / st["capital"] - 1) * 100, 2) if st["capital"] else None,
        "progress": round(min(1.0, max(0.0, math.log(max(eq, 1) / st["capital"]) / math.log(st.get("goal", GOAL) / st["capital"]))) * 100, 1)
        if st["capital"] and st.get("goal", GOAL) > st["capital"] else None,
        "started": st["started"], "tier": {"frac": frac, "seats": seats},
        "positions": [{**p, "value": mark_of(p), "pl": round(mark_of(p) - p["cost"], 2),
                       "pl_pct": round((mark_of(p) / p["cost"] - 1) * 100, 1) if p["cost"] and p.get("bid") else None} for p in st["positions"]],
        "closed": closed[:60], "n_closed": len(closed), "wins": len(wins), "losses": len(closed) - len(wins),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "realized": round(sum(c["pl"] for c in closed), 2),
        "fees": round(sum((c.get("fee_in") if c.get("fee_in") is not None else FEE * c["qty"]) + (c.get("fee_out") if c.get("fee_out") is not None else FEE * c["qty"])
                          for c in closed) + sum((p.get("fee_in") if p.get("fee_in") is not None else FEE * p["qty"]) for p in st["positions"]), 2),
        "today": {"wins": sum(1 for c in tday if c["pl"] > 0), "losses": sum(1 for c in tday if c["pl"] <= 0), "realized": round(sum(c["pl"] for c in tday), 2),
                  "new": (st.get("day") or {}).get("new", 0) if (st.get("day") or {}).get("date") == today else 0},
        "exposure": {"contracts": sum(p["qty"] for p in st["positions"]), "cost": round(cost_open, 2), "value": round(val_open, 2),
                     "ret": round((val_open / cost_open - 1) * 100, 1) if cost_open else None},
        "equity_curve": pts[-600:], "signals": st.get("signals") or [], "log": (st.get("log") or [])[:120], "gates": st.get("gates") or [],
        "scan": st.get("scan_meta"), "session": st.get("session"), "last_cycle": st.get("last_cycle"), "last_check": st.get("last_check"),
        "health": {**(st.get("health") or {}), "telegram": tg}, "broker": st.get("broker") or {"linked": False, "name": "IBKR"},
        "runs": st.get("runs") or [], "running": dict(_JOB if market == "us" else _sa_job()),
        "regime": st.get("regime"), "geo": st.get("geo"),
        "rules": _sa_rules() if market == "sa" else {"fee": FEE, "stop": STOP, "take": TAKE, "dte": [MIN_DTE, MAX_DTE], "max_spread": RULES["max_spread"] * 100,
                  "stock": {"stop": STOCK_STOP, "trail": list(STOCK_TRAIL), "time_days": STOCK_TIME_DAYS},
                  "delta": [RULES["min_delta"], RULES["max_delta"]], "burn": MAX_BURN * 100, "exit_dte": EXIT_DTE, "day_loss": DAY_LOSS * 100,
                  "max_new_day": MAX_NEW_DAY, "tiers": [[(None if math.isinf(a) else a), b, c] for a, b, c in TIERS]},
    }
