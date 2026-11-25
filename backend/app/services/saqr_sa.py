"""صقر السعوديّ — صيدُ الشركات في السوق السعوديّ (‏D764 · بأمر المالك 2026-11-18).

«أطوّر صقر ليكون للسوق السعوديّ والأمريكيّ… يصيد فرصاً لها علاقةٌ باختيار الشركات في السوق السعوديّ لأنه لا يمتلك عقودَ خيارات بعد…
ولكلٍّ منهما استراتيجيتُه الذكية الدقيقة. السوقُ السعوديّ يتأثّر بالنتائج الربعية لكلّ شركة، ويتأثّر بالأحداث الجيوسياسية، ويتأثّر بهبوط
المؤشّر العامّ — مع أنه لا يمثّل الاقتصادَ السعوديّ القويّ، لكنّ الشركاتِ تتأثّر بتاسي».

فاستراتيجيتُه من خبرة المالك نفسِها، وكلُّ ركنٍ من مصدرٍ في التطبيق:
  ١ تاسي أوّلاً: مسارُه من شموعه اليومية — هابطٌ ⇐ لا دخول (الشركاتُ تتبعه)، وعرضيٌّ ⇐ نصفُ الحجم، ويومُ هلعٍ (−1.5٪) ⇐ لا دخولَ اليوم.
  ٢ المخاطرُ الكلّية (داخليّةٌ لا تُعرض — ‏D767): النموذجُ يقرأ عناوينَ السوق في 36 ساعة ومعها حركةُ برنت ⇐ خطرٌ (منخفض · متوسّط · مرتفع) — المرتفعُ
     يمنع الدخولَ ويُخرج الخاسر، والمتوسّطُ (أو تعذُّرُ القراءة) نصفُ الحجم.
  ٣ النتائجُ الربعية (أرقام · إعلاناتُ تداول): نموُّ صافي الربح عن الربع المماثل 15٪ فأكثر بإعلانٍ حديث ⇐ محفّز؛ خسارةٌ أو تراجعٌ 15٪ ⇐
     مستبعَد؛ وربعٌ انتهى ونتائجُه لم تصدر في مهلتها ⇐ لا دخولَ قبل المفاجأة.
  ٤ الشركة: سيولةٌ (قيمةُ تداول اليوم ≥ 5 ملايين ريال) وفارقٌ ≤ 0.6٪، ومسارٌ صاعدٌ فوق متوسّط 50 وقوّةٌ على تاسي في ثلاثة أشهر، ولا
     يطارد يوماً فوق +6٪ ولا يدخل يوماً دون −2٪.
  ٥ التنفيذ: الشراءُ بسعر العرض والبيعُ بسعر الطلب من لقطة «تداول» الحيّة، وعمولةُ 0.155٪ لكلّ جهة، وأسهمٌ صحيحة؛ والحجمُ بالطبقة.
الخروج: وقفٌ −6٪ ومتحرّك (من +8٪ إلى الدخول ومن +12٪ إلى 94٪ من القمّة)، والهدفُ الفنيّ، وانقلابُ تاسي على مركزٍ خاسر، والخطرُ
الجيوسياسيّ المرتفع على مركزٍ خاسر، ونتائجُ مخيّبةٌ صدرت بعد الدخول، وستّةُ أسابيع بلا تقدّم. والدفترُ مستقلٌّ (‏saqr/ledger_sa.json) لا يمسّ
محفظةَ المالك — وقراءةُ الأخبار من قاعدة البيانات قراءةٌ لا كتابة."""
import asyncio
import math
import re
from datetime import date, datetime, timedelta, timezone

from loguru import logger

from app.services import option_picks as OP
from app.services import saqr_trader as SQ

TIERS = ((10_000, 0.25, 4), (50_000, 0.20, 5), (math.inf, 0.10, 8))
STOP = 0.94
MIN_PRICE, MIN_TURNOVER, MAX_SPREAD = 5.0, 5e6, 0.006
MAX_UP, MAX_DOWN = 6.0, -2.0
GROWTH, RESULTS_FRESH = 15.0, 50
OPEN_WAIT, CLOSE_WAIT = 15, 20
TASI_PANIC = -1.5
DAY_LOSS, MAX_NEW_DAY, COOL_DAYS = 0.10, 2, 5
SCAN_EVERY, POOL = 20 * 60, 15
_JOB = {"on": False, "msg": "", "at": None}
LEVELS = ("منخفض", "متوسط", "مرتفع")


def tier(eq: float) -> tuple[float, int]:
    for lim, frac, n in TIERS:
        if eq < lim:
            return frac, n
    return TIERS[-1][1], TIERS[-1][2]


def sa_clock(now: datetime | None = None) -> tuple[datetime, datetime] | None:
    """(الافتتاح 10:00، الإغلاق 15:00) بتوقيت الرياض ليوم تداولٍ سعوديّ — أو None."""
    from app.services.market_session import RY, _sa_day
    n = (now or SQ._now()).astimezone(RY)
    day = _sa_day(n.date())
    if not day:
        return None
    return datetime.combine(n.date(), day[1], RY), datetime.combine(n.date(), day[2], RY)


def quarter_end(today: date) -> date:
    """آخرُ نهاية ربعٍ مضت (31 مارس · 30 يونيو · 30 سبتمبر · 31 ديسمبر)."""
    for m, d in ((12, 31), (9, 30), (6, 30), (3, 31)):
        q = date(today.year, m, d)
        if q <= today:
            return q
    return date(today.year - 1, 12, 31)


def parse_date(v) -> date | None:
    s = str(v or "").strip()
    for rx, order in ((r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "ymd"), (r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", "dmy")):
        m = re.search(rx, s)
        if m:
            a, b, c = (int(x) for x in m.groups())
            try:
                return date(a, b, c) if order == "ymd" else date(c, b, a)
            except ValueError:
                return None
    return None


def results_state(q: dict | None, ann: dict | None, today: date) -> tuple[str, str, float | None]:
    """(الحال، الشرح، النموّ٪) لنتائج الشركة الربعية: strong · neutral · weak · pending · unknown.
    ‏`q` من «أرقام» (صافي الربح: السابقُ والحاليّ والتغيّر وتاريخُ الإعلان)، و‏`ann` من إعلان «تداول» (نهايةُ الفترة وتاريخُ الإعلان)."""
    qe = quarter_end(today)
    window = 90 if qe.month == 12 else 30
    days = (today - qe).days
    period = parse_date((ann or {}).get("as_of"))
    announced = parse_date((ann or {}).get("announced")) or parse_date((q or {}).get("date"))
    covered = (period is not None and period >= qe) or (period is None and announced is not None and announced > qe)
    if not covered and days <= window:
        return "pending", f"نتائجُ الربع المنتهي {qe.isoformat()} لم تصدر بعد (مهلتُها {window} يوماً) — لا دخولَ قبل المفاجأة.", None
    g = (q or {}).get("change_pct")
    cur = (q or {}).get("current")
    if not isinstance(g, (int, float)):
        return "unknown", "لا نتائجَ ربعيةً مقروءة.", None
    if isinstance(cur, (int, float)) and cur <= 0:
        return "weak", "خسارةٌ في آخر ربع.", g
    if g <= -GROWTH:
        return "weak", f"صافي الربح {g:+.0f}٪ عن الربع المماثل.", g
    age = (today - announced).days if announced else None
    if g >= GROWTH and (age is None or age <= RESULTS_FRESH):
        return "strong", f"صافي الربح {g:+.0f}٪ عن الربع المماثل" + (f" (أُعلن {announced.isoformat()})" if announced else "") + ".", g
    return "neutral", f"صافي الربح {g:+.0f}٪ عن الربع المماثل.", g


def results_of(sym: str, today: date) -> tuple[str, str, float | None]:
    from app.services import argaam_results as AR
    from app.services import results_announcements as RA
    try:
        q = (AR.for_symbol(sym) or {}).get("quarter")
    except Exception:                                             # noqa: BLE001
        q = None
    try:
        ann = RA.latest(sym)
    except Exception:                                             # noqa: BLE001
        ann = None
    return results_state(q, ann, today)


async def regime() -> dict | None:
    """تاسي: مسارُه من شموعه اليومية وحركةُ اليوم — مخبّأٌ عشرَ دقائق."""
    from app.services import cache
    from app.services.live_quote import tv_scan
    from app.services.market_data import market_service as M
    hit = cache.get("saqr:sa:regime")
    if hit is not None:
        return hit
    try:
        bars = await asyncio.wait_for(M.get_bars("^TASI.SR", "1d"), 25) or []
    except Exception:                                             # noqa: BLE001
        bars = []
    tr = OP.trend_of(bars)
    if not tr:
        return None
    rows = await tv_scan("ksa", ["TADAWUL:TASI"], ["close", "change"])
    row = next(iter(rows.values()), None) or {}
    chg = row.get("change") if isinstance(row.get("change"), (int, float)) else None
    down = tr["state"] == "هابط" or (tr["close"] < tr["sma200"] and tr["slope50"] < 0)
    out = {**tr, "chg": chg, "close_live": row.get("close"), "verdict": "هابط" if down else tr["state"]}
    cache.set("saqr:sa:regime", out, 600)
    return out


GEO_PROMPT = """أنت محلّلُ مخاطر للسوق السعوديّ (تاسي). أمامك عناوينُ الأخبار في آخر 36 ساعة وحركةُ خام برنت.
قدّر الخطرَ الجيوسياسيَّ والكلّيَّ على الأسهم السعودية خلال الأيام القادمة: توتّراتٌ إقليمية، حروب، عقوبات، قراراتُ أوبك+، صدماتُ النفط،
قراراتُ الفيدراليّ، أزماتٌ عالمية. لا تخترع حدثاً غير مذكور؛ وإن لم يكن في العناوين ما يدلّ على خطرٍ فالخطرُ «منخفض».
أعد JSON فقط: {"level": "منخفض" أو "متوسط" أو "مرتفع", "why": "جملةٌ واحدة بالعربية تذكر الحدثَ بعينه", "sectors": ["القطاعاتُ الأشدّ تأثّراً"]}
"""


async def geo() -> dict | None:
    """الخطرُ الجيوسياسيّ: عناوينُ السوق في 36 ساعة (قراءةٌ من قاعدة البيانات) وبرنت ⇐ قراءةُ النموذج — مخبّأةٌ ساعة؛ وتعذّرُها None."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import MarketNews
    from app.services import cache
    from app.services import research_desk as RD
    from app.services.market_data import market_service as M
    hit = cache.get("saqr:sa:geo")
    if hit is not None:
        return hit
    since = SQ._now() - timedelta(hours=36)
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(MarketNews.headline, MarketNews.provider).where(MarketNews.published_at >= since)
                                     .order_by(MarketNews.published_at.desc()).limit(45))).all()
    except Exception as e:                                        # noqa: BLE001
        logger.debug("صقر السعوديّ/الأخبار: {}", type(e).__name__)
        rows = []
    brent = ""
    try:
        bb = [float(b["close"]) for b in (await asyncio.wait_for(M.get_bars("BZ=F", "1d"), 20) or []) if b.get("close")][-6:]
        if len(bb) >= 2:
            brent = f"برنت {bb[-1]:.2f} دولاراً — اليوم {(bb[-1] / bb[-2] - 1) * 100:+.1f}٪" + (f" وخمسة أيام {(bb[-1] / bb[0] - 1) * 100:+.1f}٪" if len(bb) >= 6 else "")
    except Exception:                                             # noqa: BLE001
        pass
    if not rows and not brent:
        return None
    heads = "\n".join(f"- {h} ({p or ''})" for h, p in rows) or "- لا عناوين"
    try:
        got = await RD._gemini([{"text": GEO_PROMPT + f"\n{brent}\n\nالعناوين:\n{heads}"}], max_tokens=600, temperature=0.1)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("صقر السعوديّ/النموذج: {}", type(e).__name__)
        got = None
    if not isinstance(got, dict) or got.get("level") not in LEVELS:
        return None
    out = {"level": got["level"], "why": str(got.get("why") or "")[:240], "sectors": [str(x)[:40] for x in (got.get("sectors") or [])][:5],
           "brent": brent, "n": len(rows), "at": SQ._iso()}
    cache.set("saqr:sa:geo", out, 3600)
    return out


async def trend(sym: str) -> dict | None:
    from app.services import cache
    from app.services.market_data import market_service as M
    hit = cache.get(f"saqr:sa:tr:{sym}")
    if hit is not None:
        return hit
    try:
        bars = await asyncio.wait_for(M.get_bars(f"{sym}.SR", "1d"), 25) or []
    except Exception:                                             # noqa: BLE001
        return None
    tr = OP.trend_of(bars)
    if tr:
        cache.set(f"saqr:sa:tr:{sym}", tr, 6 * 3600)
    return tr


async def vol_of(sym: str) -> float | None:
    """‏D832: التذبذبُ السنويُّ المحقَّق من آخر ستين جلسة — لنسبة النجاح بنموذج العقد نفسِه (‏saqr_team.odds_stock)."""
    from app.services import cache
    from app.services.market_data import market_service as M
    hit = cache.get(f"saqr:sa:vol:{sym}")
    if hit is not None:
        return hit or None
    try:
        bars = await asyncio.wait_for(M.get_bars(f"{sym}.SR", "1d"), 25) or []
    except Exception:                                             # noqa: BLE001
        return None
    cl = [b.get("close") for b in bars[-61:] if b.get("close")]
    rets = [math.log(b / a) for a, b in zip(cl, cl[1:]) if a and b]
    if len(rets) < 30:
        return None
    m = sum(rets) / len(rets)
    v = round(math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(252), 4)
    cache.set(f"saqr:sa:vol:{sym}", v, 6 * 3600)
    return v


def gates(st: dict, now: datetime, clock: tuple[datetime, datetime] | None, reg: dict | None, g: dict | None) -> list[str]:
    """ما يمنع الدخولَ الجديد في السوق السعوديّ الآن (فارغةٌ = مفتوح)."""
    out = []
    if not st.get("on"):
        out.append("صقرٌ موقوفٌ بأمر المالك.")
    if not clock or not (clock[0] <= now <= clock[1]):
        out.append("خارج الجلسة الرسمية.")
    else:
        if now < clock[0] + timedelta(minutes=OPEN_WAIT):
            out.append("أوّلُ ربع ساعةٍ بعد الافتتاح: الأسعارُ تستقرّ — لا دخول.")
        if now > clock[1] - timedelta(minutes=CLOSE_WAIT):
            out.append("آخرُ عشرين دقيقةً قبل المزاد — لا دخولَ جديد.")
    if reg is None:
        out.append("مسارُ تاسي غيرُ متوفّر — لا دخولَ بلا قراءة السوق العامّ.")
    else:
        if reg["verdict"] == "هابط":
            out.append(f"تاسي هابط ({reg['close']:,.0f} دون متوسّطيه) — الشركاتُ تتبعه: لا دخول.")
        if isinstance(reg.get("chg"), (int, float)) and reg["chg"] <= TASI_PANIC:
            out.append(f"تاسي اليوم {reg['chg']:+.1f}٪ — يومُ هلع: لا دخولَ اليوم.")
    if g and g.get("level") == "مرتفع":
        out.append(f"خطرٌ جيوسياسيّ مرتفع: {g.get('why') or ''} — لا دخول.")
    eq, d = SQ.equity(st), st.get("day") or {}
    if d.get("start_eq") and eq <= d["start_eq"] * (1 - DAY_LOSS):
        out.append(f"قاطعُ اليوم: الخسارةُ اليوم {(1 - eq / d['start_eq']) * 100:.0f}٪ — لا دخولَ حتى الغد.")
    if (d.get("new") or 0) >= MAX_NEW_DAY:
        out.append(f"بلغ صقرٌ {MAX_NEW_DAY} صفقتين اليوم — حدُّه اليوميّ.")
    return out


def size_factor(reg: dict | None, g: dict | None) -> tuple[float, str]:
    """نصفُ الحجم مع تاسي العرضيّ، أو الخطرِ المتوسّط، أو تعذّرِ قراءة الأحداث."""
    why = []
    if reg and reg.get("verdict") == "عرضي":
        why.append("تاسي عرضيّ")
    if g is None:
        why.append("قراءةُ الأحداث غيرُ متوفّرة")
    elif g.get("level") == "متوسط":
        why.append("خطرٌ جيوسياسيّ متوسّط")
    return (0.5, "نصفُ الحجم: " + " و".join(why)) if why else (1.0, "")


def shares(budget: float, ask: float) -> int:
    one = ask * (1 + SQ.FEE_SA)
    return int(budget // one) if one > 0 else 0


def screen(row: dict, tasi_chg: float | None) -> str | None:
    """سببُ استبعاد الشركة من لقطتها الحيّة — أو None إن صلحت."""
    px, bid, ask = row.get("price"), row.get("bid"), row.get("ask")
    if not px or px < MIN_PRICE:
        return "سعرٌ دون 5 ريالات"
    if (row.get("turnover") or 0) < MIN_TURNOVER:
        return "سيولةُ اليوم دون 5 ملايين ريال"
    if not (bid and ask and ask > bid):
        return "لا عرضَ ولا طلبَ حيّين"
    if (ask - bid) / ((ask + bid) / 2) > MAX_SPREAD:
        return "الفارقُ بين العرض والطلب واسع"
    chg = row.get("change_pct")
    if isinstance(chg, (int, float)) and chg > MAX_UP:
        return f"صعد اليوم {chg:+.1f}٪ — لا مطاردة"
    if isinstance(chg, (int, float)) and chg < MAX_DOWN:
        return f"يهبط اليوم {chg:+.1f}٪"
    return None


async def brent() -> dict | None:
    """خامُ برنت: آخرُ إغلاقٍ وتغيّرُ اليوم وخمسةِ أيام — مخبّأٌ نصفَ ساعة."""
    from app.services import cache
    from app.services.market_data import market_service as M
    hit = cache.get("saqr:sa:brent")
    if hit is not None:
        return hit
    try:
        bb = [float(b["close"]) for b in (await asyncio.wait_for(M.get_bars("BZ=F", "1d"), 20) or []) if b.get("close")][-6:]
    except Exception:                                             # noqa: BLE001
        return None
    if len(bb) < 2:
        return None
    out = {"px": round(bb[-1], 2), "chg": round((bb[-1] / bb[-2] - 1) * 100, 2), "chg5": round((bb[-1] / bb[0] - 1) * 100, 2) if len(bb) >= 6 else None}
    cache.set("saqr:sa:brent", out, 1800)
    return out


def main_company(sym: str) -> bool:
    """شركةٌ في السوق الرئيسيّ لا في «نمو» ولا صندوقُ مؤشّر (‏D767): مرجعُ صقر السعوديّ ونبضِه مؤشّرُ السوق الرئيسيّ (تاسي)،
    و«نمو» والصناديقُ لا يتبعانه — قيس: لقطةُ ما بعد الإغلاق 396 رمزاً منها 123 من «نمو»."""
    from app.data.universe import is_etf, is_main
    return is_main(sym) and not is_etf(sym)


def pulse(snap: dict, today: date, oil: dict | None = None) -> dict:
    """نبضُ السوق السعوديّ من لقطة «تداول» الحيّة (‏D767 — المالك: «أعد صياغتها بشكلٍ احترافيّ»): اتّساعُ السوق (صاعدةٌ · هابطةٌ · ثابتة)،
    وقيمةُ التداول، والقطاعاتُ القائدةُ والمتأخّرة (متوسّطُ تغيّر شركاتها مرجّحاً بقيمة تداولها)، وموسمُ النتائج الربعية، وخامُ برنت."""
    from collections import Counter
    from app.data.saudi_directory import SYMBOL_TO_SECTOR_AR as SEC
    adv = dec = unch = 0
    turnover = 0.0
    sect: dict[str, list[float]] = {}
    for sym, r in snap.items():
        if not main_company(sym):
            continue
        ch, tv = r.get("change_pct"), r.get("turnover") or 0
        turnover += tv
        if not isinstance(ch, (int, float)):
            continue
        if ch > 0.05:
            adv += 1
        elif ch < -0.05:
            dec += 1
        else:
            unch += 1
        sec = SEC.get(sym)
        if sec and tv:
            a = sect.setdefault(sec, [0.0, 0.0])
            a[0] += ch * tv
            a[1] += tv
    ranked = sorted(((k, round(v[0] / v[1], 2)) for k, v in sect.items() if v[1] > 0), key=lambda kv: -kv[1])
    res = Counter(results_of(sym, today)[0] for sym in snap if main_company(sym))
    return {"at": SQ._iso(), "adv": adv, "dec": dec, "unch": unch, "turnover": round(turnover), "leaders": ranked[:3], "laggards": ranked[::-1][:3],
            "results": {k: res.get(k, 0) for k in ("strong", "neutral", "weak", "pending", "unknown")}, "quarter": quarter_end(today).isoformat(),
            "brent": oil}


def rules() -> dict:
    return {"market": "sa", "fee_pct": SQ.FEE_SA * 100, "stop": STOP, "trail": list(SQ.STOCK_TRAIL), "time_days": SQ.STOCK_TIME_DAYS,
            "min_turnover": MIN_TURNOVER, "max_spread": MAX_SPREAD * 100, "growth": GROWTH, "tasi_panic": TASI_PANIC, "day_loss": DAY_LOSS * 100,
            "max_new_day": MAX_NEW_DAY, "tiers": [[(None if math.isinf(a) else a), b, c] for a, b, c in TIERS]}


def _roll_day(st: dict, now: datetime) -> None:
    from app.services.market_session import RY
    d = now.astimezone(RY).date().isoformat()
    if (st.get("day") or {}).get("date") != d:
        st["day"] = {"date": d, "start_eq": SQ.equity(st), "new": 0}


async def _review(st: dict, now: datetime, snap: dict, reg: dict | None, g: dict | None) -> list[dict]:
    out = []
    today = now.date()
    for p in list(st["positions"]):
        row = snap.get(p["symbol"]) or {}
        bid, ask, last = row.get("bid"), row.get("ask"), row.get("price")
        if bid:
            p.update(bid=bid, marked=SQ._iso())
            SQ.trail(p, bid)
        if ask:
            p["ask"] = ask
        if last:
            p["S"] = last
        tr = await trend(p["symbol"])
        r = SQ.exit_rule(p, bid, last, 999, tr, None)
        losing = bid is not None and bid < p["entry_px"]
        if not r and reg and reg.get("verdict") == "هابط" and losing:
            r = ("regime", f"تاسي انقلب هابطاً والمركزُ خاسر ({bid:.2f} دون {p['entry_px']:.2f}) — الشركاتُ تتبعه.")
        if not r and g and g.get("level") == "مرتفع" and bid is not None and bid <= p["entry_px"] * 0.98:
            r = ("geo", f"خطرٌ جيوسياسيّ مرتفع ({g.get('why') or ''}) والمركزُ خاسر — يُحمى رأسُ المال.")
        if not r:
            stt, txt, _ = results_of(p["symbol"], today)
            ann_after = stt == "weak" and p.get("results_state") != "weak"
            if ann_after:
                r = ("results", f"صدرت نتائجُ مخيّبة بعد الدخول: {txt}")
        if not r:
            continue
        code, why = r
        if not p.get("auto"):
            if p.get("alert") != code:
                p["alert"] = code
                SQ.log(st, "alert", f"إشارةُ خروجٍ لمركزك اليدويّ {SQ._title(p)}: {SQ.REASON_AR[code]} — {why}", p["symbol"])
            continue
        if not bid:
            continue
        c = SQ.sell(st, p["id"], bid, code, why)
        if c:
            out.append(c)
            SQ.log(st, "sell", f"بيع {c['qty']:g} سهم من {SQ._title(c)} بسعر {bid:.2f} — {SQ.REASON_AR[code]}: {why} · النتيجة {c['pl']:+,.2f} ريال "
                               f"({c['pl_pct']:+.1f}٪) بعد العمولات.", c["symbol"])
    return out


def vp_exits(ask: float, stop_pct: float, tgt: float, lbl: str, rd: dict | None) -> tuple[float, str, float, str]:
    """الوقفُ والهدفُ للسهم السعوديّ ⇐ (الوقف، وصفُه، الهدف، وصفُه). ‏D818 (المالك: «في السعوديّ البروفايل يحسّن الدخولَ والوقفَ والهدف»):
    الوقفُ تحت قاعدة الحجم (أقربُ عقدةٍ كثيفةٍ تحت السعر، وإلّا حدُّ منطقة القيمة الأدنى) بـ1.5٪ إن وقعت داخل الوقف الثابت — قبولُ السعر تحتها
    فشلُ الصعود، والوقفُ الأضيقُ الأصدقُ يحمي رأسَ المال؛ والهدفُ عقدةُ الحجم الكثيف التالية إن سبقت الهدفَ الفنيّ وبعدت 5٪ فأكثر —
    هناك يتباطأ السعر. وبلا بروفايلٍ أو بسيولةٍ ضعيفة: الوقفُ الثابتُ والهدفُ الفنيّ كما كانا."""
    stop, stop_lbl = round(ask * (1 - stop_pct / 100), 3), f"−{stop_pct:g}٪"
    if rd and not rd.get("thin"):
        base = next((x for x in (rd.get("support"), rd.get("val")) if x and x < ask * 0.995), None)
        if base and round(base * 0.985, 3) > stop:
            stop, stop_lbl = round(base * 0.985, 3), f"تحت قاعدة الحجم {base:,.2f}"
        if rd.get("next") and ask * 1.05 <= rd["next"] < tgt:
            tgt, lbl = rd["next"], "عقدةُ حجمٍ كثيف"
    return stop, stop_lbl, tgt, lbl


async def _hunt(st: dict, now: datetime, snap: dict, reg: dict, g: dict | None) -> dict | None:
    from app.services import saqr_council as CN
    eq = SQ.equity(st)
    frac, seats = tier(eq)
    fac, fac_why = size_factor(reg, g)
    seats, budget = SQ.seats_budget(st, eq, frac * fac, seats)
    c = SQ.cfg(st)
    if len(st["positions"]) >= seats:
        return None
    today = now.date()
    held = {p["symbol"] for p in st["positions"]}
    tasi_chg = reg.get("chg")
    from app.data.saudi_directory import SUSPENDED, SYMBOL_TO_NAME
    from app.services import saqr_team as TEAM
    sig, pool = [], []
    # ‏D832 — بابُ صقر الواحد للسوقين: المنبعُ فرصُ اليوم التي وافق عليها صقرٌ كاملاً (كالأمريكيّ) — لا الشركاتُ كلُّها
    opps = {s_: x for s_, x in CN.opportunities("sa").items() if x.get("side") == "long"}
    floor = SQ.win_floor()
    _JOB["msg"] = "قراءةُ الشركات ونتائجها"
    for sym, row in snap.items():
        if sym in held or sym in SUSPENDED or not main_company(sym) or SQ.cooling(st, sym, now):
            continue
        if sym not in opps:
            continue
        row = {**row, "name_en": SYMBOL_TO_NAME.get(sym) or row.get("name_en")}
        why = screen(row, tasi_chg)
        if why:
            continue
        stt, txt, gr = results_of(sym, today)
        if stt in ("weak", "pending"):
            sig.append({"sym": sym, "name": row.get("name_en"), "verdict": "refused", "why": txt})
            continue
        rs_day = (row.get("change_pct") or 0) - (tasi_chg or 0)
        pre = {"strong": 30, "neutral": 10, "unknown": 0}[stt] + max(-5, min(5, rs_day)) * 2 + min(row.get("turnover") or 0, 1e8) / 1e8 * 10
        pool.append((pre, sym, row, stt, txt, gr))
    pool.sort(key=lambda x: -x[0])
    # ‏D786 (المالك: «التحليلُ الفنيّ خطوةٌ من بين الخطوات — يقرأ ويحلّل مثل الصفة البشرية ويربط بين كلّ شيء، وعملُنا القديم لا يلغيه الجديد»):
    # المرشّحون يُعرضون على مجلس صقر — المسارُ (قاعدتُه القديمة نفسُها) والرسمُ والنتائجُ والأخبارُ والأحداثُ والحيتانُ والمحلّلون —
    # ورفضُ عضوٍ يُسقط الصفقةَ بسببه، ثمّ «الرابط» يقرأ الأعضاءَ معاً قبل الشراء (وكان ‏D784 يرفض كلَّ ما لا فرصةَ له في الرسم)
    _JOB["msg"] = "صقر يقرأ: المسارَ والرسمَ والنتائجَ والأخبارَ والأحداثَ والحيتانَ والمحلّلين"
    cands = []
    for pre, sym, row, stt, txt, gr in pool[:POOL]:
        tr = await trend(sym)
        if not tr:
            sig.append({"sym": sym, "name": row.get("name_en"), "verdict": "refused", "why": "لا شموعَ كافيةً للمسار"})
            continue
        cr_side, cr_any, _ = await CN.chart_sa(sym)
        cands.append({"symbol": sym, "name": row.get("name_en"), "side": "long", "price": row.get("price"), "tr": tr, "rs3": tr["ret3m"] - reg["ret3m"],
                      "cr_side": cr_side, "cr_any": cr_any, "liq": (cr_any or cr_side or {}).get("liq"), "stt": stt, "stxt": txt, "_pre": pre, "_row": row})
    try:                                                          # ‏D788: قراءةُ العالم الواحدة — صقرٌ واحدٌ للسوقين
        from app.services import saqr_mind as SM
        w = await SM.world()
    except Exception:                                             # noqa: BLE001
        w = None
    evs = await CN.collect("sa", cands, {"events": await CN.events("sa"), "reg": reg, "geo": g, "world": w}) if cands else {}
    ok = []
    for cd in cands:
        sym, row, tr, rs3 = cd["symbol"], cd["_row"], cd["tr"], cd["rs3"]
        bd = CN.judge(evs[sym])
        board = CN.compact(bd)
        why_no = CN.gate_why(bd, None, "long", need_link=False)
        if why_no:
            sig.append({"sym": sym, "name": row.get("name_en"), "verdict": "refused", "why": why_no, "council": board})
            continue
        score = cd["_pre"] + min(max(rs3, 0), 30) + min(tr["strength"], 20) + bd["score"] / 2
        ask = row["ask"]
        hi = tr.get("hi52") or 0
        tgt, lbl = (min(hi, ask * 1.25), "قمّة السنة") if hi >= ask * 1.10 else (round(ask * 1.12, 2), "+12٪")
        rd = (evs.get(sym) or {}).get("vp_rd")
        stop, stop_lbl, tgt, lbl = vp_exits(ask, c["stock_stop"], tgt, lbl, rd)
        p_win = TEAM.odds_stock(ask, stop, tgt, await vol_of(sym))
        if floor and (p_win is None or p_win < floor):
            sig.append({"sym": sym, "name": row.get("name_en"), "verdict": "refused", "council": board,
                        "why": f"صقر يوافق ({bd['score']}/100) لكنّ نسبةَ نجاحه {'غيرُ متوفّرة' if p_win is None else f'{p_win:.0f}٪'} دون حدّك {floor:.0f}٪"
                               f" (الهدف {tgt:,.2f} قبل الوقف {stop:,.2f})"})
            continue
        k = {"contract": sym, "symbol": sym, "name": row.get("name_en"), "type": "stock", "ask": ask, "bid": row.get("bid"), "price": row.get("price"),
             "stop": stop, "stop_label": stop_lbl, "target": round(tgt, 2), "target_label": lbl, "score": round(score, 1),
             "vp": ({x: rd[x] for x in ("zone", "poc", "val", "vah", "wall", "next", "support", "window")} if rd else None),
             "results": cd["stxt"], "results_state": cd["stt"], "tr": tr, "rs3": rs3, "chg": row.get("change_pct"), "board": bd, "chart_read": cd["cr_side"], "p_win": p_win}
        good = next((m["say"] for m in bd["members"] if m["v"] == "ok" and m["role"] != "المسار"), None)
        sig.append({"sym": sym, "name": row.get("name_en"), "verdict": "accepted", "contract": sym, "score": k["score"], "council": board,
                    "why": f"صقر {bd['verdict']} ({bd['score']}/100 · {bd['oks']} شاهدٌ يؤيّد · {bd['warns']} تحفّظ)" + (f" · {good}" if good else "")})
        ok.append(k)
    # «الرابط» يقرأ أعلى ثلاثةٍ بالترتيب: أوّلُ من يقول «شراء» يُشترى، و«انتظار» أو «تجنّب» يُذكر سببُه — وتعذّرُه لا يمنع (قواعدُ المجلس وحدها)
    best, lk = None, None
    for k in sorted(ok, key=lambda x: -x["score"])[:3]:
        lk = await CN.link(k["symbol"], k["name"], "sa", "long", k["board"], chart=k.get("chart_read"), price=k["ask"])
        why_no = CN.gate_why(k["board"], lk, "long")              # ‏D832: وتعذّرُ القراءة الأخيرة يمنع — لا دخولَ آليّاً بشاهدٍ ناقص
        if why_no:
            for x in sig:
                if x.get("contract") == k["contract"] and x["verdict"] == "accepted":
                    x["why"] += f" · {why_no}"
            continue
        best = k
        break
    pos = None
    if best:
        qty = shares(budget, best["ask"])
        if qty >= 1:
            why = [f"تاسي {reg['verdict']}: {reg['close']:,.0f} و{'فوق' if reg['close'] >= reg['sma200'] else 'دون'} متوسّط 200" +
                   (f"، واليوم {reg['chg']:+.1f}٪" if isinstance(reg.get("chg"), (int, float)) else "") + ".",
                   f"حكمُ صقر: {best['board']['verdict']} ({best['board']['score']}/100).",
                   *CN.lines(best["board"]),
                   f"قراءةُ صقر الأخيرة ({lk['decision']} · ثقة {lk['confidence']}): {lk['link']}" + (f" التعارض: {lk['conflict']}" if lk.get("conflict") else ""),
                   (f"نسبةُ النجاح {best['p_win']:.0f}٪: يبلغ هدفَه قبل وقفه خلال {TEAM.STOCK_DAYS} يوماً" + (f" — وحدُّك {floor:.0f}٪" if floor else "")
                    + " (تقديرٌ من تذبذبه لا وعد).") if best.get("p_win") is not None else "نسبةُ النجاح غيرُ متوفّرة لهذا السهم.",
                   f"الوقف {best['stop']:.2f} ({best.get('stop_label') or ''}) والهدف {best['target']:,.2f} ({best['target_label']})." + (f" {fac_why}." if fac_why else "")]
            pos = SQ.buy(st, {k: v for k, v in best.items() if k not in ("board", "chart_read", "p_win")}, qty, why, kind="stock")
            pos["results_state"] = best["results_state"]
            st["day"]["new"] = (st["day"].get("new") or 0) + 1
            for x in sig:
                if x.get("contract") == best["contract"] and x["verdict"] == "accepted":
                    x["verdict"] = "chosen"
            SQ.log(st, "buy", f"شراء {qty} سهم من {SQ._title(pos)} بسعر {pos['entry_px']:.2f} (الكلفة مع العمولة {pos['cost']:,.2f} ريال) — "
                              f"الوقف {pos['stop']:.2f} والهدف {pos['target']:,.2f}.", pos["symbol"])
        else:
            sig.append({"sym": best["symbol"], "verdict": "refused", "why": f"ميزانيةُ الصفقة {budget:,.0f} ريال لا تتّسع لسهمٍ واحد بـ{best['ask']:.2f}"})
    order = {"chosen": 0, "accepted": 1, "refused": 2}
    st["signals"] = [{"at": SQ._iso(), **x} for x in sorted(sig, key=lambda x: order[x["verdict"]])][:60]
    st["scan_meta"] = {"at": SQ._iso(), "universe": len(snap), "movers": 0, "pool": len(pool), "deep": min(len(pool), POOL), "opps": len(opps), "floor": floor,
                       "budget": round(budget, 2), "tier": {"frac": frac, "seats": seats}, "factor": fac}
    return pos


def _reg_view(reg: dict | None) -> dict | None:
    return {k: reg.get(k) for k in ("verdict", "state", "close", "sma50", "sma200", "ret3m", "chg")} if reg else None


async def close_read() -> bool:
    """قراءةُ الإغلاق (‏D767): نبضُ السوق ومؤشّرُه من لقطة «تداول» بعد مزاد الإغلاق — ومرّةً بعد كلّ إقلاع — فلا تخلو اللوحةُ
    خارجَ الجلسة ولا تنتظر جلسةَ الغد. قراءةٌ وحدها: لا صيدَ ولا مراجعةَ ولا مساسَ بالدفتر."""
    from app.services import tadawul_market as TM
    async with SQ._LOCK:
        st = SQ.load("sa")
        snap, _live, at = TM.usable_rows()   # خارجَ الجلسة: لقطةُ آخر جلسةٍ المحفوظةُ بزمنها — والحيّةُ فارغةٌ بعد الإغلاق (قيس)
        if not snap:
            return False
        reg = await regime()
        st["regime"] = _reg_view(reg) or st.get("regime")
        pu = pulse(snap, SQ._now().date(), await brent())
        pu["at"] = at or pu["at"]            # الزمنُ زمنُ اللقطة لا زمنُ القراءة
        st["pulse"] = pu
        SQ.save(st)
        return True


async def cycle(force: bool = False) -> dict:
    """دورةُ صقر السعوديّ: في جلسة تداول وحدها — مراجعةُ المراكز كلَّ دورة، والصيدُ كلَّ عشرين دقيقة (أو بأمر المالك)."""
    from app.services import tadawul_market as TM
    from app.services.live_quote import sessions
    async with SQ._LOCK:
        _JOB.update(on=True, msg="يبدأ", at=SQ._iso())
        try:
            st = SQ.load("sa")
            now = SQ._now()
            ses = (await sessions()).get("sa") or {}
            st["session"] = {k: ses.get(k) for k in ("state", "label", "detail", "next", "holiday")}
            st["last_check"] = SQ._iso()
            if ses.get("state") != "open":
                SQ.save(st)
                return {"ran": False, "why": f"السوقُ السعوديّ {ses.get('label') or 'مغلق'} — صقرٌ يعمل في الجلسة وحدها."}
            TM.ensure_fresh()
            snap = TM.snapshot()
            if not snap:
                st["health"]["quotes"] = None
                SQ.save(st)
                return {"ran": False, "why": "لقطةُ «تداول» الحيّة غيرُ متوفّرة الآن."}
            st["health"]["quotes"] = SQ._iso()
            _roll_day(st, now)
            reg, g = await regime(), await geo()
            st["regime"] = _reg_view(reg)
            st["geo"] = g
            st["pulse"] = pulse(snap, now.date(), await brent())
            st["health"]["news"] = g is not None
            st["health"]["events"] = reg is not None
            _JOB["msg"] = "مراجعةُ المراكز"
            exits = await _review(st, now, snap, reg, g)
            gt = gates(st, now, sa_clock(now), reg, g)
            st["gates"] = gt
            pos = None
            due = force or not st.get("last_scan") or (now - datetime.fromisoformat(st["last_scan"])).total_seconds() >= SCAN_EVERY - 30
            if not gt and due and reg:
                st["last_scan"] = SQ._iso()
                pos = await _hunt(st, now, snap, reg, g)
            st["last_cycle"] = SQ._iso()
            st["cycles"] = (st.get("cycles") or 0) + 1
            SQ._point(st)
            SQ.save(st)
            return {"ran": True, "exits": len(exits), "bought": pos["symbol"] if pos else None, "gates": gt, "equity": SQ.equity(st)}
        except Exception as e:                                    # noqa: BLE001
            logger.warning("صقر السعوديّ: {}", type(e).__name__)
            return {"ran": False, "why": f"تعذّرت الدورة ({type(e).__name__})"}
        finally:
            _JOB.update(on=False, msg="")
