"""صقر — وكيلُ التداول الآليّ لعقود الخيارات الأمريكية (‏D763 · بأمر المالك 2026-11-18).

«أضف تبويباً اسمه صقر… وكيلُ تداولٍ آليّ… يبدأ من ميزانية 100 دولار ويحاول أن يوصلها إلى 10,000… السوقُ الأمريكيّ كاملٌ قدّام عينه،
عقودُ الخيارات كاملة والسترايكات كاملة… يختار بحسب الميزانية الموجودة في المحفظة… لازم يفهم أنّ الموضوع جدّ، ما هو محاكاة ولا لعب».

فصقرٌ يدير **محفظةَ خياراتٍ مستقلّة** (لا تمسّ محفظةَ المالك السعودية ولا أرقامَها): نقدٌ ومراكزُ وصفقاتٌ مغلقة ومنحنى رأس مال.
والتنفيذُ بأسعار السوق الحقيقية لحظتَها — الشراءُ بسعر العرض والبيعُ بسعر الطلب وعمولةُ الوسيط على كلّ عقد — حتى يُربط وسيطٌ (‏IBKR)؛
فالنتيجةُ ما كان سيحدث فعلاً لا ما يُتمنّى. وكلُّ قرارٍ (دخولٌ أو رفضٌ أو خروج) مكتوبٌ بسببه في سجلّ التطبيق — ولا يُرسل صقرُ التداول إلى تلغرام شيئاً (‏D767 بأمر المالك:
«تلغرامُ للتقارير اليومية ومهامّ صقر الأساسية وحدها»).

الدخولُ (كلّ عشرين دقيقة في الجلسة الرسمية، ومقعدٌ شاغرٌ ونقدٌ يكفي):
  ١ السوقُ كلُّه (‏D766): كلُّ ورقةٍ لها عقودُ خيارات (دليلُ سيبوي) وسائلة، والأساسُ أوّلاً (‏saqr_universe: لا شطبَ ولا ضيقَ ماليّ ولا ضعفَ
    ولا خسارةً محترقة ولا دينَ مفرط ولا صندوقَ مرفوع)، ثمّ المسارُ من المُصفّي نفسِه.
  ٢ الاتجاهُ من المسار، والخبرُ القويُّ المعاكس يُسقطه (قراءةُ النموذج لعناوين عشرة أيام).
  ٣ لا يعاكس حركةَ اليوم، ولا يدخل قبل أرباح الشركة بثلاثة أيام (ينهار التذبذبُ بعدها).
  ٤ العقد: أجلُ 21–200 يوماً، عرضٌ وطلبٌ حيّان بفارقٍ ≤ 8٪، اهتمامٌ مفتوح ≥ 100، دلتا 0.35–0.80، تعادلٌ دون الهدف الفنيّ وعائدٌ عنده،
     تآكلٌ يوميّ ≤ 3٪ — ثمّ حكمُ المستشار بيونانياته كلِّها «مناسب» لا «بحذر».
  ٥ الحجم بالطبقة: دون 500 دولار نصفُ رأس المال لمركزين، ودون 2,000 ثلثُه لثلاثة، ودون 10,000 خُمسُه لخمسة، وما فوقها عُشرُه لثمانية.
بوّاباتٌ تمنع الدخول: أوّلُ ربع ساعةٍ وآخرُ عشرين دقيقةً من الجلسة، وحدثٌ اقتصاديٌّ عالي الأثر قريب (قرارُ الفيدراليّ يوماً كاملاً)،
وخسارةُ اليوم 15٪ (قاطع)، وثلاثُ صفقاتٍ في اليوم، ولا عودةَ إلى سهمٍ خرج بوقفٍ قبل خمسة أيام.
الخروجُ (كلّ خمس دقائق): وقفٌ عند 60٪ من سعر الشراء، ومن +50٪ يرتفع الوقفُ إلى الدخول ومن +80٪ إلى 75٪ من القمّة، وجنيٌ عند التضاعف
أو بلوغِ السهم الهدفَ، وخروجٌ قبل 14 يوماً من الانتهاء، وعند انكسار الأطروحة."""
import asyncio
import hashlib
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
# ‏D764 (قيس على الخادم 2026-11-18): «محضرُ الفيدراليّ» عالي الأثر في التقويم وكان يحجب يومَ التداول كلَّه كقرار الفائدة — فاليومُ الكاملُ للقرار
# وبيانِه ومؤتمرِه وتوقّعاتِه وحدها، والمحضرُ والخطاباتُ ساعتان كسائر الأحداث العالية الأثر
FED_RX = ("FOMC Statement", "Federal Funds Rate", "FOMC Press Conference", "FOMC Economic Projections")
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
REASON_AR = {"tp": "بلغ أمرُ جني الربح", "sl": "بلغ أمرُ وقف الخسارة", "stop": "بلغ الوقف", "trail": "وقفٌ متحرّكٌ يحمي الربح", "take": "تضاعف العقد — جنيُ الربح", "target": "بلغ السهمُ الهدف",
             "time": "اقترب الأجل", "broken": "انكسرت الأطروحة", "manual": "إغلاقٌ يدويّ من المالك", "stale": "لم يتقدّم — يُحرَّر المال",
             "regime": "انقلب السوقُ العامّ", "geo": "خطرٌ جيوسياسيّ", "results": "نتائجُ ربعيةٌ مخيّبة"}
# ‏D767 (المالك): «أضف خيارَ تحديد الميزانية… خلّ فيه مرونة، أقدر أغيّر الخيارات — هو العقلُ المدبّر وأنا أضع الأوامر»
DEFAULTS = {"per_trade": None, "max_positions": None, "instruments": "both", "sides": "both",
            "opt_stop": round((1 - STOP) * 100), "stock_stop": round((1 - STOCK_STOP) * 100), "take_x": TAKE, "mode": "balanced", "day_target": None}
LIMITS = {"per_trade": (5, 1_000_000), "max_positions": (1, 12), "opt_stop": (20, 70), "stock_stop": (2, 20), "take_x": (1.3, 5.0),
          "day_target": (1, 1_000_000)}
CHOICES = {"instruments": ("both", "options", "stocks"), "sides": ("both", "calls"), "mode": ("attack", "balanced")}
LABEL_AR = {"per_trade": "حدُّ الصفقة", "max_positions": "أقصى المراكز", "opt_stop": "وقفُ العقد ٪", "stock_stop": "وقفُ السهم ٪", "take_x": "جنيُ العقد ×",
            "instruments": "الأداة", "sides": "الاتجاه", "mode": "النمط", "day_target": "هدفُ اليوم"}
VALUE_AR = {"both": "الكلّ", "options": "عقودٌ فقط", "stocks": "أسهمٌ فقط", "calls": "شراءٌ فقط", "attack": "هجوميّ", "balanced": "متوازن"}
# ‏D768 (المالك 2026-11-19): «صقرٌ الأمريكيّ ممتازٌ في الاصطياد لكنّه متحفّظٌ جداً، خجول — يجب أن يكون وحشاً شرساً… ميزانيةُ 100 دولار للعقد
# الواحد ويختار كما يشاء، والسوقُ الأمريكيّ كلُّه معه… أبغاه كلَّ يوم يشتغل، وأقلُّ شيءٍ 100 دولار ربحاً». وقيس على دفتره (2026-11-18):
# رأسُ ماله 100 تُقسَم نصفين فميزانيةُ الصفقة 50 وأرخصُ عقدٍ صالحٍ 96–111 ⇐ اشترى كسورَ سهمين بخمسين لكلٍّ؛ والمسحُ كلَّ عشرين دقيقة، وثلاثُ
# صفقاتٍ يومياً، وآجالٌ 30–120 يوماً بطيئةُ الحركة، وكلُّ تحفّظٍ من المستشار رفضٌ، وحركةُ يومٍ 1٪ تُسقط الإشارة (7 من 21 رُفضت بها).
# فالنمطُ الهجوميُّ للأمريكيّ افتراضاً (والمتوازنُ بأمر المالك): ميزانيةُ الصفقة أمرُ المالك لا نصفُ رأس المال، ومقعدٌ لكلّ ميزانيةِ صفقة،
# والمسحُ كلَّ دورة، وعشرُ صفقاتٍ يومياً، وآجالٌ 7–60 يوماً أسرعُ حركةً، وتحفّظُ المستشار يُكتب في المبرّر ولا يُسقط («لا» وحدها تُسقط)،
# والوقفُ المتحرّكُ أبكر. والحمايةُ باقية: الأساسُ قبل الفنّ، ووقفٌ لكلّ صفقة، وقاطعُ خسارة اليوم، ولا دخولَ قبيل الأرباح ولا حول قرار الفيدراليّ.
PROFILES = {
    "balanced": {"min_dte": MIN_DTE, "max_dte": MAX_DTE, "exp": EXP_TARGETS, "burn": MAX_BURN, "scan": SCAN_EVERY, "max_new": MAX_NEW_DAY,
                 "fight": FIGHT_PCT, "cool": COOL_DAYS, "open_wait": OPEN_WAIT, "close_wait": CLOSE_WAIT, "fed_h": FED_BEFORE_H,
                 "event_h": EVENT_BEFORE_H, "day_loss": DAY_LOSS, "exit_dte": EXIT_DTE, "trail": (TRAIL_BE, TRAIL_ON, TRAIL_KEEP), "rules": RULES,
                 "warn_ok": False},
    "attack": {"min_dte": 7, "max_dte": 60, "exp": (14, 30, 45), "burn": 0.10, "scan": 5 * 60, "max_new": 10, "fight": 2.5, "cool": 2,
               "open_wait": 10, "close_wait": 15, "fed_h": 4, "event_h": 1, "day_loss": 0.20, "exit_dte": 3, "trail": (1.3, 1.5, 0.80),
               "rules": {**RULES, "min_delta": 0.30, "max_delta": 0.75, "min_pop": 0.20}, "warn_ok": True},
}
# ‏D771 (المالك 2026-11-20): «لا نختار إلا طويلَ المدى… أبغاه يشتغل مثل السكرتير يطلع لي العقود وأنا أختار… وزرٌ أوقف التداولَ الآليّ… بالميزانية
# التي نحدّدها 150»: فالأمريكيُّ متوازنٌ طويلُ الأجل، وميزانيةُ العقد 150، والتداولُ الآليُّ موقوفٌ حتى يشغّله المالك (وإن شغّله فمن القائمة وحدها)
US_DEFAULTS = {"mode": "balanced", "per_trade": 150, "day_target": 100, "auto": False}
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
            "health": {}, "runs": [], "broker": {"linked": False, "name": m["broker"]}, "settings": {}}


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


def cfg(st: dict) -> dict:
    """إعداداتُ المالك فوق الافتراضيّ — وما لم يُضبط فصقرٌ يقرّره بطبقته."""
    if st.get("market") == "sa":
        return {**DEFAULTS, "stock_stop": 6, **(st.get("settings") or {}), "mode": "balanced"}   # السعوديّ −6٪ ومتوازنٌ دائماً
    return {**DEFAULTS, **US_DEFAULTS, **(st.get("settings") or {})}


def profile(st: dict) -> dict:
    """عتباتُ النمط (‏D768): الهجوميُّ للأمريكيّ افتراضاً، والمتوازنُ بأمر المالك وللسعوديّ دائماً."""
    return PROFILES["attack" if cfg(st).get("mode") == "attack" and st.get("market", "us") == "us" else "balanced"]


def day_status(st: dict) -> dict:
    """ربحُ اليوم من رأس مال أوّله (المحقَّقُ وغيرُ المحقَّق) وهدفُ المالك — يُعرض في اللوحة."""
    d, tgt = st.get("day") or {}, cfg(st).get("day_target")
    pl = round(equity(st) - d["start_eq"], 2) if d.get("start_eq") else None
    return {"date": d.get("date"), "pl": pl, "target": tgt, "hit": d.get("hit"), "new": d.get("new", 0),
            "progress": round(max(0.0, min(1.0, pl / tgt)) * 100, 1) if tgt and pl is not None else None}


def day_lock(st: dict) -> int:
    """بلغ هدفَ اليوم ⇐ كلُّ مركزٍ رابحٍ لصقر يُحمى وقفُه عند سعر دخوله (لا يعود اليومُ الأخضرُ أحمرَ منه)، والصيدُ مستمرٌّ بلا سقف."""
    ds = day_status(st)
    if not ds["target"] or ds["pl"] is None or ds["pl"] < ds["target"]:
        return 0
    n = 0
    for p in st["positions"]:
        if p.get("auto") and not p.get("owner") and (p.get("bid") or 0) > p["entry_px"] and p["stop"] < p["entry_px"]:
            p["stop"] = round(p["entry_px"], 4)
            n += 1
    if not st["day"].get("hit"):
        st["day"]["hit"] = _iso()
        log(st, "info", f"بلغ هدفَ اليوم: {ds['pl']:+,.2f} من {ds['target']:,.0f} — الرابحاتُ محميّةٌ عند سعر دخولها ({n})، والصيدُ مستمرٌّ بلا سقف.")
    return n


def seats_budget(st: dict, eq: float, frac: float, seats: int) -> tuple[int, float]:
    """(أقصى المراكز، ميزانيةُ الصفقة الواحدة) بعد أوامر المالك: لا تتجاوز ما حدّده ولا ما في النقد."""
    c = cfg(st)
    if st.get("market", "us") == "us" and c["per_trade"]:
        # ‏D768: ميزانيةُ الصفقة أمرُ المالك لا نصفُ رأس المال، ومقعدٌ لكلّ ميزانيةِ صفقةٍ في رأس المال (1–12)
        unit = float(c["per_trade"])
        seats = int(c["max_positions"]) if c["max_positions"] else max(1, min(12, int(eq // unit)))
        return seats, min(unit, st["cash"])
    if c["max_positions"]:
        seats = int(c["max_positions"])
    budget = min(st["cash"], eq * frac)
    if c["per_trade"]:
        budget = min(budget, float(c["per_trade"]), st["cash"])
    return seats, budget


def apply_settings(st: dict, upd: dict) -> list[str]:
    """يطبّق أوامرَ المالك ويعيد ما تغيّر بالعربية — والقيمةُ خارج حدودها تُرفض بسببها. والميزانيةُ تُعدَّل بلا محوٍ للسجلّ: الفرقُ يُضاف
    إلى النقد أو يُسحب منه (فلا يتغيّر الربحُ المحسوب)، والسحبُ لا يتجاوز النقدَ الحرّ."""
    c, done = cfg(st), []
    if upd.get("equity_to") not in (None, ""):
        # ‏D769 (المالك): «المحفظةُ الآن — إذا صارت مثلاً 100 أرجعُ أعدّلها من جديد»: قيمتُها الآن كما يكتبها، والفرقُ تمويلٌ يُضاف إلى النقد
        # أو يُسحب منه — فلا يتغيّر الربحُ المحسوب ولا السجلّ
        tgt = round(float(upd["equity_to"]), 2)
        if not (10 <= tgt <= 1_000_000):
            raise ValueError("قيمةُ المحفظة بين 10 و1,000,000.")
        upd = {**upd, "budget": round(st["capital"] + tgt - equity(st), 2)}
    if upd.get("budget") not in (None, ""):
        nb = round(float(upd["budget"]), 2)
        if not (10 <= nb <= 1_000_000):
            raise ValueError("الميزانيةُ بين 10 و1,000,000.")
        delta = round(nb - st["capital"], 2)
        if delta < 0 and -delta > st["cash"] + 1e-9:
            raise ValueError(f"لا يُسحب {-delta:,.2f} والنقدُ الحرّ {st['cash']:,.2f} — أغلق مراكزَ أوّلاً أو اختر ميزانيةً أعلى.")
        if delta:
            st["cash"] = round(st["cash"] + delta, 2)
            st["capital"] = nb
            st["goal"] = round(nb * GOAL_X, 2)
            st["day"]["start_eq"] = round((st["day"].get("start_eq") or 0) + delta, 2)
            st.setdefault("fundings", []).append({"at": _iso(), "delta": delta, "budget": nb})
            done.append(f"الميزانية {nb - delta:,.2f} ⇐ {nb:,.2f}")
    if "auto" in upd and upd["auto"] is not None:
        c["auto"] = bool(upd["auto"])
        done.append("التداولُ الآليّ: " + ("يعمل — من قائمة صقر وحدها" if c["auto"] else "موقوف — صقرٌ يُعدّ القائمةَ وينفّذ أوامرك"))
    if st.get("market") == "sa" and upd.get("mode") not in (None, "balanced"):
        raise ValueError("النمطُ الهجوميُّ للسوق الأمريكيّ وحده.")
    for k in ("per_trade", "max_positions", "opt_stop", "stock_stop", "take_x", "day_target"):
        if k in upd:
            v = upd[k]
            if v in (None, "", 0):
                if k in ("per_trade", "max_positions", "day_target"):
                    c[k] = None
                    done.append(f"{LABEL_AR[k]}: " + ("بلا هدف" if k == "day_target" else "تلقائيّ"))
                continue
            v = float(v)
            lo, hi = LIMITS[k]
            if not (lo <= v <= hi):
                raise ValueError(f"القيمةُ {v:g} خارج حدودها ({lo:g}–{hi:g}).")
            c[k] = int(v) if k == "max_positions" else round(v, 2)
            done.append(f"{LABEL_AR[k]}: {c[k]:g}")
    for k, opts in CHOICES.items():
        if k in upd and upd[k] is not None:
            if upd[k] not in opts:
                raise ValueError("خيارٌ غيرُ معروف.")
            c[k] = upd[k]
            done.append(f"{LABEL_AR[k]}: {VALUE_AR.get(c[k], c[k])}")
    st["settings"] = c
    return done


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
    stop = k["stop"] if k.get("stop") is not None else (px * (STOP if kind == "option" else STOCK_STOP))
    p = {"id": _pid(k["contract"]), "kind": kind, "contract": k["contract"], "symbol": k["symbol"], "name": k.get("name"),
         "type": k.get("type", "stock"), "strike": k.get("strike"), "expiry": k.get("expiry"), "t": k.get("t"),
         "qty": int(qty) if kind == "option" else round(float(qty), 4), "entry_px": round(px, 4), "cost": cost, "fee_in": fee, "opened": _iso(),
         "stop": round(stop, 4), "stop0": round(stop, 4), "take_x": k.get("take_x"), "trail": k.get("trail"), "exit_dte": k.get("exit_dte"), "peak": float(k.get("bid") or px), "bid": k.get("bid"), "ask": k.get("ask"), "S": k.get("price"),
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
    if p.get("owner"):                      # ‏D771: مركزٌ بأوامر المالك — أمراه وحدهما (جنيٌ ووقف) لا وقفٌ متحرّك
        p["peak"] = max(float(p.get("peak") or 0), bid)
        return
    be, on, keep = (p.get("trail") or (TRAIL_BE, TRAIL_ON, TRAIL_KEEP)) if kind_of(p) == "option" else STOCK_TRAIL
    p["peak"] = max(float(p.get("peak") or 0), bid)
    e = p["entry_px"]
    if p["peak"] >= e * be:
        p["stop"] = max(p["stop"], e)
    if p["peak"] >= e * on:
        p["stop"] = max(p["stop"], round(p["peak"] * keep, 4))


def exit_rule(p: dict, bid: float | None, S: float | None, dte: int, tr: dict | None, news: dict | None) -> tuple[str, str] | None:
    """(السبب، الشرح) إن وجب الخروج — وإلا None. الترتيب: الأجلُ ثمّ الوقفُ ثمّ الجنيُ ثمّ الهدفُ ثمّ الأطروحة."""
    if p.get("owner"):
        # ‏D771 (المالك): «إمّا يُقفل إلين يحقّق هدفه أو أنا أضغط إغلاق — وأحدّد جميعَ الأوامر»: جنيُ الربح ووقفُ الخسارة كما كتبهما، وخروجٌ قبل الانتهاء
        if kind_of(p) == "option" and dte <= (p.get("exit_dte") or EXIT_DTE):
            return "time", f"بقي {dte} يوماً على الانتهاء — يتسارع التآكل."
        if bid is not None and bid > 0:
            if p.get("stop") and bid <= p["stop"]:
                return "sl", f"سعرُ الطلب {bid:.2f} عند أمر الوقف {p['stop']:.2f}" + (f" (−{p['sl_pct']:g}٪)." if p.get("sl_pct") else ".")
            if p.get("take_x") and bid >= p["entry_px"] * p["take_x"]:
                return "tp", f"سعرُ الطلب {bid:.2f} بلغ أمرَ جني الربح {p['entry_px'] * p['take_x']:.2f}" + (f" (+{p['tp_pct']:g}٪)." if p.get("tp_pct") else ".")
        return None
    stock = kind_of(p) == "stock"
    call = stock or p["type"] == "call"
    base = STOCK_STOP if stock else STOP
    if not stock and dte <= (p.get("exit_dte") or EXIT_DTE):
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
        if not stock and bid >= p["entry_px"] * (p.get("take_x") or TAKE):
            return "take", f"تضاعف العقد: {p['entry_px']:.2f} ⇐ {bid:.2f}."
    if S is not None and p.get("target") and ((call and S >= p["target"]) or (not call and S <= p["target"])):
        return "target", f"بلغ السهمُ {S:,.2f} الهدفَ {p['target']:,.2f}."
    if tr and not p.get("managed"):
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


def event_block(events: list[dict], now: datetime, fed_h: float = FED_BEFORE_H, ev_h: float = EVENT_BEFORE_H) -> dict | None:
    """حدثٌ عالي الأثر يمنع الدخول: قبله بساعتين (والفيدراليُّ بيومٍ كامل) وبعده بنصف ساعة."""
    for e in events or []:
        if e.get("impact") != "High":
            continue
        try:
            at = datetime.fromisoformat(e["at"])
        except (KeyError, ValueError):
            continue
        fed = any(w.lower() in str(e.get("title") or "").lower() for w in FED_RX)
        if at - timedelta(hours=fed_h if fed else ev_h) <= now <= at + timedelta(minutes=EVENT_AFTER_M):
            return e
    return None


def _mins(n: int) -> str:
    return {10: "عشر دقائق", 15: "ربع ساعةٍ", 20: "عشرين دقيقةً"}.get(n, f"{n} دقيقة")


def gates(st: dict, now: datetime, clock: tuple[datetime, datetime] | None, events: list[dict]) -> list[str]:
    """ما يمنع الدخولَ الجديد الآن (فارغةٌ = مفتوح)؛ والخروجُ لا تمنعه بوّابة."""
    out, pf = [], profile(st)
    if not st.get("on"):
        out.append("صقرٌ موقوفٌ بأمر المالك.")
    if not clock or not (clock[0] <= now <= clock[1]):
        out.append("خارج الجلسة الرسمية.")
    else:
        if now < clock[0] + timedelta(minutes=pf["open_wait"]):
            out.append(f"أوّلُ {_mins(pf['open_wait'])} من الجلسة: الفوارقُ واسعةٌ والأسعارُ مضطربة — لا دخول.")
        if now > clock[1] - timedelta(minutes=pf["close_wait"]):
            out.append(f"آخرُ {_mins(pf['close_wait'])} من الجلسة — لا دخولَ جديد.")
    ev = event_block(events, now, pf["fed_h"], pf["event_h"])
    if ev:
        out.append(f"حدثٌ اقتصاديٌّ عالي الأثر: {ev.get('title')} ({ev.get('riyadh', '')[-5:]} بتوقيت الرياض) — لا دخولَ حوله.")
    eq, d = equity(st), st.get("day") or {}
    if d.get("start_eq") and eq <= d["start_eq"] * (1 - pf["day_loss"]):
        out.append(f"قاطعُ اليوم: الخسارةُ اليوم {(1 - eq / d['start_eq']) * 100:.0f}٪ — لا دخولَ حتى الغد.")
    if (d.get("new") or 0) >= pf["max_new"]:
        out.append(f"بلغ صقرٌ {pf['max_new']} صفقاتٍ اليوم — حدُّه اليوميّ.")
    return out


def cooling(st: dict, sym: str, now: datetime) -> bool:
    lim = (now - timedelta(days=profile(st)["cool"])).isoformat()
    return any(c["symbol"] == sym and c["reason"] in ("stop", "broken") and c["closed"] >= lim for c in st["closed"])


AFFORD_X = 3.5        # عقدٌ بدلتا نحو 0.35 وأجلِ شهرٍ أو شهرين يكلّف نحو 3.5 أضعافِ سعر السهم (قيس: أرخصُ صالحٍ لـCAT ‏2,321 ولـSLV ‏154)
EXTRA_CHEAP = 12      # مقاعدُ إضافيةٌ في القائمة القصيرة للأسهم التي تتّسع الميزانيةُ لعقودها


def affordable(close: float, budget: float) -> bool:
    return close * AFFORD_X <= budget * 1.2


def shortlist(tr_all: dict, held: set, cooling_fn, budget: float) -> list[str]:
    """القائمةُ القصيرة (‏D764 — قيس على السوق الحيّ: كانت مقاعدُها الأربعةُ والعشرون تذهب لمساراتٍ عرضية ولأسهمٍ كبيرةٍ لا تتّسع الميزانيةُ
    لعقدها فلا يصيد صقرٌ بمئة دولار شيئاً): ذوو الاتجاه وحدهم بقوّة مسارهم، ثمّ مقاعدُ إضافيةٌ لذوي الاتجاه الذين تتّسع الميزانيةُ لعقودهم."""
    ranked = [s for s, t in sorted(tr_all.items(), key=lambda kv: -kv[1]["strength"])
              if s not in held and not cooling_fn(s) and t["state"] in ("صاعد", "هابط")]
    top = ranked[:SHORTLIST]
    cheap = [s for s in ranked[SHORTLIST:] if affordable(tr_all[s]["close"], budget)][:EXTRA_CHEAP]
    return top + cheap


def size(budget: float, ask: float) -> int:
    """أكبرُ عددِ عقودٍ تتّسع له الميزانيةُ مع العمولة."""
    one = ask * 100 + FEE
    return int(budget // one) if one > 0 else 0


def pick_expiries(exps: list[dict], pf: dict | None = None) -> list[dict]:
    pf = pf or PROFILES["balanced"]
    win = [e for e in exps if pf["min_dte"] <= e["dte"] <= pf["max_dte"]]
    out = []
    for t in pf["exp"]:
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


async def best_for(sym: str, call: bool, budget: float, tr: dict, ctx: dict, pf: dict | None = None) -> tuple[dict | None, str]:
    """أفضلُ عقدٍ لسهمٍ واتّجاه ضمن ميزانية الصفقة: آجالُ 21–200 يوماً، وقواعدُ صقر، وعرضٌ وطلبٌ حيّان، وتآكلٌ ≤ 3٪، ثمّ حكمُ المستشار."""
    from app.services import option_advisor as AD
    from app.services.options_chain import chain
    base = await chain(sym)
    if not base or not base.get("price"):
        return None, "لا سلسلةَ خيارات"
    pf = pf or PROFILES["balanced"]
    best, why, cheapest = None, "لا عقدَ يستوفي قواعد صقر", None
    for e in pick_expiries(base.get("expirations") or [], pf):
        ch = await chain(sym, e["t"])
        if not ch:
            continue
        S = float(ch["price"] or base["price"])
        T = max(e["dte"], 1) / 365
        ref = OP.atm_iv(ch, S, T)
        if ref is None:
            continue
        rows = ch["calls"] if call else ch["puts"]
        for k in OP.candidates(rows, S, e["dte"], call, tr, ref_iv=ref, rules=pf["rules"]):
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
            if burn > pf["burn"]:
                continue
            if best is None or k["score"] > best["score"]:
                best = {**k, "expiry": e["date"], "t": e["t"], "symbol": sym, "name": base.get("name"), "price": S, "row": row,
                        "theta": g.get("theta"), "gamma": g.get("gamma"), "vega": g.get("vega")}
    if not best:
        return None, (f"{why} ضمن {budget:,.0f} دولار — أرخصُ عقدٍ صالح {cheapest:,.0f}" if cheapest else why)
    lvl, pros, cons = AD.judge(best["row"], call, best["price"], best["dte"], ctx, best["expiry"])
    best.update(verdict=lvl, pros=pros, cons=cons)
    best.pop("row", None)
    if lvl == "no" or (lvl == "warn" and not pf["warn_ok"]):
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
    if k.get("verdict") == "warn" and k.get("cons"):
        out.append(f"تحفّظُ المستشار (يقبله النمطُ الهجوميّ): {k['cons'][0]}")
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
    out.append(f"الوقف {k['stop']:.2f} والهدف {k['target']:,.2f} ({k['target_label']}).")
    return out


# ══ الدورة ══

def _title(p: dict) -> str:
    if kind_of(p) == "stock":
        return f"{p['symbol']}{(' ' + p['name']) if p.get('name') else ''} · سهم"
    return f"{p['symbol']} {'Call' if p['type'] == 'call' else 'Put'} {p['strike']:g} · {p['expiry']}"


def _roll_day(st: dict, now: datetime) -> None:
    from app.services.market_session import NY
    d = now.astimezone(NY).date().isoformat()
    if (st.get("day") or {}).get("date") != d:
        st["day"] = {"date": d, "start_eq": equity(st), "new": 0, "hit": None}


def _point(st: dict) -> None:
    eq = equity(st)
    pts = st.setdefault("equity", [])
    if pts and pts[-1][0][:16] == _iso()[:16]:
        pts[-1] = [_iso(), eq]
    else:
        pts.append([_iso(), eq])
    st["equity"] = pts[-2500:]


async def _review(st: dict, now: datetime, scan_tr: dict | None) -> list[dict]:
    """مراجعةُ المراكز: سعرُها الحيّ ووقفُها المتحرّك وقاعدةُ خروجها — صقرٌ يبيع مراكزَه، ومراكزُ المالك اليدوية يُنبَّه عليها في السجلّ ولا تُمسّ."""
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
        tr = cache.get(f"saqr:tr:{p['symbol']}") or (scan_tr or cache.get("optpicks:scan:v3") or {}).get(p["symbol"])
        news = cache.get(f"optpicks:news:{p['symbol']}")
        r = exit_rule(p, bid, S, dte, tr, news)
        if not r:
            continue
        code, why = r
        if not p.get("auto"):
            if p.get("alert") != code:
                p["alert"] = code
                log(st, "alert", f"إشارةُ خروجٍ لمركزك اليدويّ {_title(p)}: {REASON_AR[code]} — {why}", p["symbol"])
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
    return out


async def _hunt(st: dict, now: datetime) -> dict | None:
    """التداولُ الآليّ (‏D771 — المالك: «أنت المتعلّم وهو فقط المنفّذ… لا نختار إلا طويلَ المدى»): يشتري من قائمة صقر نفسِها — الأعلى
    إيجابياتٍ أوّلاً — عقداً طويلَ الأجل بعرضه الحيّ ضمن ميزانية العقد، بوقفه وجنيه من أوامر المالك. لا أسهمَ ولا عقودَ قصيرة."""
    from app.services import saqr_list as SL
    eq = equity(st)
    frac, seats = tier(eq)
    seats, budget = seats_budget(st, eq, frac, seats)
    c = cfg(st)
    if len(st["positions"]) >= seats:
        return None
    lst = SL.load() or {}
    held = {p["symbol"] for p in st["positions"]} | {o["symbol"] for o in st.get("orders") or []}
    for it in lst.get("items") or []:
        if it["symbol"] in held or cooling(st, it["symbol"], now) or (it["type"] == "put" and c["sides"] == "calls"):
            continue
        q = await contract_quote(it["contract"])
        if not q or not q["live"] or not q["ask"]:
            continue
        qty = size(budget, q["ask"])
        if qty < 1:
            continue
        k = {**{x: it[x] for x in ("contract", "symbol", "name", "type", "strike", "expiry", "t", "target", "target_label", "delta", "iv")},
             "ask": q["ask"], "bid": q["bid"], "price": q["price"], "dte": q["dte"],
             "stop": round(q["ask"] * (1 - c["opt_stop"] / 100), 4), "take_x": c["take_x"]}
        why = [f"من قائمة صقر ({lst.get('label') or ''}): {it['grade']} — {len(it['pros'])} إيجابيات و{len(it['cons'])} سلبيات."] + it["pros"][:4] \
            + [f"تحفّظ: {x}" for x in it["cons"][:2]]
        pos = buy(st, k, qty, why)
        st["day"]["new"] = (st["day"].get("new") or 0) + 1
        log(st, "buy", f"شراءٌ آليٌّ من القائمة: {qty} × {_title(pos)} بسعر {pos['entry_px']:.2f} (الكلفة مع العمولة {pos['cost']:,.2f}$) — "
                       f"الوقف {pos['stop']:.2f} والجني ×{pos['take_x']:g}.", pos["symbol"])
        return pos
    return None


# ══ أوامرُ المالك (‏D771): شراءٌ بسعره، وأمرا البيع — جنيُ الربح ووقفُ الخسارة — وأوامرٌ معلّقةٌ حتى تُنفَّذ أو تُلغى ══

async def contract_quote(contract: str) -> dict | None:
    """عرضُ عقدٍ بعينه وطلبُه (حيّان، أو من آخر جلسة إن أُغلق السوق) وسعرُ سهمه وأجلُه — من سلسلته."""
    from app.services.options_chain import chain, parse_option
    o = parse_option(contract)
    if not o:
        return None
    base = await chain(o["root"])
    e = next((x for x in (base or {}).get("expirations") or [] if x["date"] == o["expiry"]), None)
    ch = await chain(o["root"], e["t"]) if e else None
    row = next((r for r in (ch or {}).get("calls" if o["type"] == "call" else "puts", []) if r.get("contract") == contract), None)
    if not row:
        return None
    ask, bid = row.get("ask") or None, row.get("bid") or None
    return {"o": o, "t": e["t"], "dte": e["dte"], "ask": ask or row.get("sask"), "bid": bid or row.get("sbid"), "live": bool(ask),
            "price": (ch or {}).get("price"), "name": (base or {}).get("name")}


def _fill(st: dict, o: dict, ask: float, q: dict) -> dict:
    k = {"contract": o["contract"], "symbol": o["symbol"], "name": o.get("name"), "type": o["type"], "strike": o["strike"], "expiry": o["expiry"],
         "t": o.get("t"), "ask": ask, "bid": q.get("bid"), "price": q.get("price"), "target": None,
         "stop": round(ask * (1 - o["sl_pct"] / 100), 4) if o.get("sl_pct") else 0.0,
         "take_x": round(1 + o["tp_pct"] / 100, 4) if o.get("tp_pct") else None}
    tp = f"جنيٌ عند {ask * k['take_x']:.2f} (+{o['tp_pct']:g}٪)" if k["take_x"] else "بلا أمر جني"
    sl = f"وقفٌ عند {k['stop']:.2f} (−{o['sl_pct']:g}٪)" if k["stop"] else "بلا وقف"
    p = buy(st, k, o["qty"], [f"أمرُ المالك: شراءٌ بسعر {ask:.2f} — {tp} · {sl} · وخروجٌ قبل الانتهاء بـ{EXIT_DTE} يوماً."], src="manual", px=ask)
    p.update(auto=True, managed=True, owner=True, tp_pct=o.get("tp_pct"), sl_pct=o.get("sl_pct"))
    log(st, "buy", f"نُفّذ أمرُ المالك: {o['qty']} × {_title(p)} بسعر {ask:.2f} (الكلفة {p['cost']:,.2f}$) — {tp} · {sl}.", p["symbol"])
    return p


def _check_order(qty, limit, tp_pct, sl_pct) -> tuple[int, float | None, float | None, float | None]:
    qty = int(qty or 0)
    if qty < 1:
        raise ValueError("الكمّيةُ عقدٌ واحدٌ فأكثر.")
    limit = round(float(limit), 2) if limit not in (None, "", 0) else None
    tp_pct = float(tp_pct) if tp_pct not in (None, "", 0) else None
    sl_pct = float(sl_pct) if sl_pct not in (None, "", 0) else None
    if limit is not None and limit <= 0:
        raise ValueError("سعرُ الشراء غيرُ صالح.")
    if tp_pct is not None and not (5 <= tp_pct <= 500):
        raise ValueError("جنيُ الربح بين 5٪ و500٪.")
    if sl_pct is not None and not (5 <= sl_pct <= 95):
        raise ValueError("وقفُ الخسارة بين 5٪ و95٪.")
    return qty, limit, tp_pct, sl_pct


async def place_order(contract: str, qty, limit=None, tp_pct=None, sl_pct=None, market: str = "us") -> dict:
    """أمرُ شراءٍ من المالك: العرضُ الحيُّ عند سعره أو دونه والسوقُ مفتوح ⇐ يُنفَّذ الآن بالعرض؛ وإلا أمرٌ معلّقٌ يُنفَّذ في الجلسة متى بلغ
    العرضُ سعرَه (وبلا سعرٍ فعند أوّل عرضٍ حيّ) — حتى يلغيه المالك. ومعه أمرا البيع: جنيُ الربح ووقفُ الخسارة بالنسبة من سعر الشراء."""
    from app.services.live_quote import sessions
    if _mk(market) != "us":
        raise ValueError("الأوامرُ لعقود السوق الأمريكيّ.")
    sym = str(contract or "").strip().upper()
    qty, limit, tp_pct, sl_pct = _check_order(qty, limit, tp_pct, sl_pct)
    q = await contract_quote(sym)
    if not q:
        raise ValueError("العقدُ غيرُ موجودٍ في السلسلة الآن.")
    open_now = ((await sessions()).get("us") or {}).get("state") == "open"
    async with _LOCK:
        st = load("us")
        o = {"id": _pid(sym), "contract": sym, "symbol": q["o"]["root"], "name": q.get("name"), "type": q["o"]["type"], "strike": q["o"]["strike"],
             "expiry": q["o"]["expiry"], "t": q["t"], "qty": qty, "limit": limit, "tp_pct": tp_pct, "sl_pct": sl_pct, "created": _iso()}
        ask = q["ask"] if q["live"] else None
        if open_now and ask and (limit is None or ask <= limit):
            if ask * 100 * qty + FEE * qty > st["cash"] + 1e-9:
                raise ValueError(f"الكلفةُ {ask * 100 * qty + FEE * qty:,.2f}$ والنقدُ الحرّ {st['cash']:,.2f}$ — اضبط قيمةَ المحفظة أو قلّل العقود.")
            _fill(st, o, ask, q)
        else:
            ref = limit or q["ask"] or 0
            if ref and ref * 100 * qty + FEE * qty > st["cash"] + 1e-9:
                raise ValueError(f"الكلفةُ نحو {ref * 100 * qty + FEE * qty:,.2f}$ والنقدُ الحرّ {st['cash']:,.2f}$ — اضبط قيمةَ المحفظة أو قلّل العقود.")
            st.setdefault("orders", []).append(o)
            log(st, "manual", f"أمرُ شراءٍ معلّق: {qty} × {_title(o)} " + (f"عند {limit:.2f} أو أقلّ" if limit else "عند أوّل عرضٍ في الجلسة")
                + (f" — جني +{tp_pct:g}٪" if tp_pct else "") + (f" · وقف −{sl_pct:g}٪" if sl_pct else "") + ".", o["symbol"])
        _point(st)
        save(st)
        return o


async def cancel_order(oid: str, market: str = "us") -> None:
    async with _LOCK:
        st = load(_mk(market))
        o = next((x for x in st.get("orders") or [] if x["id"] == oid), None)
        if not o:
            raise ValueError("لا أمرَ بهذا المعرّف.")
        st["orders"] = [x for x in st["orders"] if x["id"] != oid]
        log(st, "manual", f"ألغى المالك أمرَ الشراء {_title(o)}.", o["symbol"])
        save(st)


async def set_orders(pid: str, tp_pct=None, sl_pct=None, market: str = "us") -> dict:
    """أمرا البيع لمركزٍ قائم (لصقر أو للمالك): جنيُ الربح ووقفُ الخسارة بالنسبة من سعر الشراء — وفارغٌ = بلا أمر. ومن يومها يُدار بأمري المالك."""
    _, _, tp_pct, sl_pct = _check_order(1, None, tp_pct, sl_pct)
    async with _LOCK:
        st = load(_mk(market))
        p = next((x for x in st["positions"] if x["id"] == pid), None)
        if not p:
            raise ValueError("لا مركزَ بهذا المعرّف.")
        e = p["entry_px"]
        p.update(owner=True, auto=True, managed=True, tp_pct=tp_pct, sl_pct=sl_pct, take_x=round(1 + tp_pct / 100, 4) if tp_pct else None,
                 stop=round(e * (1 - sl_pct / 100), 4) if sl_pct else 0.0)
        p["stop0"] = p["stop"]
        log(st, "manual", f"المالك ضبط أمرَي {_title(p)}: " + (f"جنيٌ عند {e * p['take_x']:.2f} (+{tp_pct:g}٪)" if tp_pct else "بلا جني")
            + " · " + (f"وقفٌ عند {p['stop']:.2f} (−{sl_pct:g}٪)" if sl_pct else "بلا وقف") + ".", p["symbol"])
        save(st)
        return p


async def _fill_orders(st: dict) -> int:
    """في الجلسة: كلُّ أمرٍ معلّقٍ بلغ العرضُ الحيُّ سعرَه يُنفَّذ بالعرض — والنقدُ الذي لا يكفي يُبقيه منتظراً بسببه."""
    n = 0
    for o in list(st.get("orders") or []):
        q = await contract_quote(o["contract"])
        if not q or not q["live"] or not q["ask"]:
            continue
        ask = q["ask"]
        if o.get("limit") is not None and ask > o["limit"]:
            o["note"] = f"العرضُ الآن {ask:.2f} فوق سعرك {o['limit']:.2f}"
            continue
        if ask * 100 * o["qty"] + FEE * o["qty"] > st["cash"] + 1e-9:
            o["note"] = f"النقدُ الحرّ {st['cash']:,.2f}$ لا يكفي — ينتظر"
            continue
        _fill(st, o, ask, q)
        st["orders"] = [x for x in st["orders"] if x["id"] != o["id"]]
        n += 1
    return n


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
            day_lock(st)
            _JOB["msg"] = "أوامرُ المالك"
            filled = await _fill_orders(st)
            # ‏D771: قائمةُ صقر تُبنى في الجلسة (العرضُ والطلبُ حيّان) — كلَّ ساعتين، وآخرُها قبل الإغلاق للجلسة القادمة
            from app.services import saqr_list as SL
            SL.kick(cfg(st), {p["symbol"] for p in st["positions"]}, now, us_clock(now))
            try:
                events = shape(await raw_week(), impacts=("High",))
                st["health"]["events"] = True
            except Exception:                                     # noqa: BLE001
                events, st["health"]["events"] = [], False
            g = gates(st, now, us_clock(now), events)
            st["gates"] = g
            pos = None
            due = force or not st.get("last_scan") or (now - datetime.fromisoformat(st["last_scan"])).total_seconds() >= profile(st)["scan"] - 30
            if not g and due and cfg(st).get("auto"):
                st["last_scan"] = _iso()
                pos = await _hunt(st, now)
            st["last_cycle"] = _iso()
            st["cycles"] = (st.get("cycles") or 0) + 1
            _point(st)
            save(st)
            return {"ran": True, "exits": len(exits), "filled": filled, "bought": pos["contract"] if pos else None, "gates": g, "equity": equity(st)}
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


async def manual_open(contract: str, qty: float, price: float | None = None, market: str = "us", managed: bool = False) -> dict:
    """مركزٌ يختاره المالك أو نفّذه بنفسه: عقدٌ أمريكيّ (رمزُ OCC) أو سهمٌ أمريكيّ أو سعوديّ — بسعره إن كتبه وإلا بسعر العرض الحيّ.
    و«يديره صقر» (‏D769 — المالك: «المركزُ يُقفل إلين يحقّق هدفه أو أنا أضغط إغلاق»): وقفٌ وجنيٌ ووقفٌ متحرّكٌ بأوامر المالك، ويبيعه صقر عندها."""
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
            if managed:
                c, pf = cfg(st), profile(st)
                k.update(stop=round(float(ask) * (1 - c["opt_stop"] / 100), 4), take_x=c["take_x"], trail=list(pf["trail"]), exit_dte=pf["exit_dte"])
            p = buy(st, k, int(qty), [_manual_why(managed, k, float(ask))], src="manual", px=float(ask))
        else:
            if market == "sa" and not (sym.isdigit() and len(sym) == 4):
                raise ValueError("رمزُ الشركة السعودية أربعةُ أرقام (مثل 2222).")
            ask, bid, name = await _stock_quote(market, sym)
            ask = price or ask
            if not ask:
                raise ValueError("لا سعرَ لهذا السهم الآن — اكتب السعرَ الذي نفّذتَ به.")
            k = {"contract": sym, "symbol": sym, "name": name, "type": "stock", "ask": float(ask), "bid": bid, "price": ask, "target": None}
            if managed:
                k["stop"] = round(float(ask) * (1 - cfg(st)["stock_stop"] / 100), 4)
            p = buy(st, k, float(qty), [_manual_why(managed, k, float(ask))], src="manual", px=float(ask), kind="stock")
        if managed:
            p["auto"], p["managed"] = True, True
        log(st, "manual", f"المالك {'اختار' if managed else 'أدخل'} {p['qty']:g} × {_title(p)} بسعر {p['entry_px']:.2f}"
                          + (f" — يديره صقر: الوقف {p['stop']:.2f}." if managed else "."), p["symbol"])
        _point(st)
        save(st)
        return p


def _manual_why(managed: bool, k: dict, px: float) -> str:
    if not managed:
        return "مركزٌ أدخله المالك يدوياً."
    tx = k.get("take_x")
    return (f"اختاره المالك بنفسه — ويديره صقر: وقفٌ عند {k['stop']:.2f}" + (f" وجنيٌ عند {px * tx:.2f} (×{tx:g})" if tx else "")
            + "، ووقفٌ متحرّكٌ يحمي الربح؛ أو يُغلقه المالك متى شاء.")


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


async def settings(upd: dict, market: str = "us") -> list[str]:
    """أوامرُ المالك (‏D767): الميزانيةُ وحدُّ الصفقة وأقصى المراكز والأداةُ والاتجاهُ والوقفان والجني — تُطبَّق على الصفقات الجديدة، والميزانيةُ فوراً."""
    async with _LOCK:
        st = load(market)
        done = apply_settings(st, upd or {})
        if done:
            log(st, "manual", "المالك عدّل الإعدادات: " + " · ".join(done) + ".")
            _point(st)
        save(st)
        return done


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


def _us_rules(st: dict) -> dict:
    pf = profile(st)
    # ‏D771: العقودُ من قائمة صقر — محرّكُ «عقود الخيارات» الطويل (150–430 يوماً · فارقٌ ≤ 10٪ · دلتا 0.30–0.85)
    return {"fee": FEE, "stop": STOP, "take": TAKE, "dte": [OP.MIN_DTE, OP.MAX_DTE], "max_spread": OP.MAX_SPREAD * 100, "list": True,
            "stock": {"stop": STOCK_STOP, "trail": list(STOCK_TRAIL), "time_days": STOCK_TIME_DAYS}, "mode": cfg(st)["mode"],
            "delta": [OP.MIN_DELTA, OP.MAX_DELTA], "burn": pf["burn"] * 100, "exit_dte": pf["exit_dte"], "day_loss": pf["day_loss"] * 100,
            "max_new_day": pf["max_new"], "scan_min": pf["scan"] // 60, "fight": pf["fight"], "open_wait": pf["open_wait"], "close_wait": pf["close_wait"],
            "fed_h": pf["fed_h"], "trail": list(pf["trail"]), "warn_ok": pf["warn_ok"], "cool": pf["cool"],
            "tiers": [[(None if math.isinf(a) else a), b, c] for a, b, c in TIERS]}


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
    seats, _b = seats_budget(st, eq, frac, seats)
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
        "health": st.get("health") or {}, "settings": cfg(st), "pulse": st.get("pulse"), "day": day_status(st), "orders": st.get("orders") or [], "broker": st.get("broker") or {"linked": False, "name": "IBKR"},
        "runs": st.get("runs") or [], "running": dict(_JOB if market == "us" else _sa_job()),
        "regime": st.get("regime"), "geo": st.get("geo"),
        "rules": _sa_rules() if market == "sa" else _us_rules(st),
    }
