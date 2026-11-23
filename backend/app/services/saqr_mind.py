"""عقلُ صقر الواحد — قراءةٌ واحدةٌ للعالم يتقاسمها السوقان والتقرير (‏D788 — بأمر المالك 2026-11-23).

قال المالك: «صقرٌ الأمريكيّ وصقرٌ السعوديّ كلاهما صقرٌ واحد — التفريقُ بين الأمريكيّ والسعوديّ في الاستخدام فقط… فيصير عنده اطّلاع: يعرف الأخبارَ
العالمية وما تأثيرُها على بعض الشركات السعودية — لكلّ شركةٍ بما يخصّها: النفطُ والجيوسياسية، وأشباهُ الموصلات وقطعُ الكابلات… ونظرتُنا في قسم
الأبحاث يساعدهم فيها صقر»، و«ما فكرةُ «شراء حذر» طولَ المدّة؟ هل نظرتُنا تعتمد على الرسم الفنيّ والأخبار؟».

وكانت «نظرتُنا» على تاسي خمسَ إشاراتٍ فنيةٍ وحدها (‏research_paper.view_of) — فتبقى «شراء حذر» ما دام المؤشّرُ فوق متوسّطاته مهما قالت الأخبار؛
وكان صقرٌ السعوديّ يقرأ الخطرَ الجيوسياسيّ وحده، والأمريكيُّ لا يقرأ العالمَ أصلاً. فهنا قراءةٌ واحدة:

  ١ ‏world(): عناوينُ الأخبار في 36 ساعة (محليةٌ وعالمية من قاعدة الأخبار) وحقائقُ السوق (برنت · تاسي · ‏S&P 500 · ‏VIX) ⇐ النموذج يستخرج
    «المحاور» (النفط · الفائدة · الجيوسياسية · الرقائق…) بأثرها على قطاعات السوقين ونبرةَ كلّ سوق — محروسةً: لا رقمَ إلّا من العناوين والحقائق،
    والقطاعُ من القائمة وحدها. مخبّأةٌ ساعتين ومحفوظة، فيقرؤها صقرٌ السعوديّ والأمريكيّ والتقريرُ نسخةً واحدة.
  ٢ ‏hits(): لكلّ شركةٍ ما يخصّ قطاعَها من المحاور — عضوُ «الأحداث» في المجلس يذكرها ويتحفّظ بها.
  ٣ ‏outlook_sa(): «نظرتُنا» على تاسي من صقر: الإشاراتُ الفنيةُ الخمس أساسٌ، ثمّ نبرةُ العالم للسوق السعوديّ، ومسارُ تاسي، واتّساعُ الجلسة،
    والخطرُ الجيوسياسيّ، ونفطُ خمسة أيام، والحدثُ عالي الأثر القريب — بأسبابها مكتوبةً.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger

KEY = "saqr:mind:world"
TTL = 2 * 3600
TONES = ("إيجابي", "محايد", "سلبي")
DIRS = ("إيجابي", "سلبي")
# قطاعاتُ تريدنق فيو للسوق الأمريكيّ بأسمائها العربية (الحقلُ ‏sector في المُصفّي)
US_SECTORS = {
    "Electronic Technology": "أشباه الموصلات والإلكترونيات", "Technology Services": "البرمجيات والإنترنت",
    "Health Technology": "الأدوية والتقنية الطبية", "Health Services": "الخدمات الصحية", "Finance": "المال والبنوك",
    "Energy Minerals": "الطاقة والنفط", "Utilities": "المرافق", "Communications": "الاتصالات",
    "Retail Trade": "الاستهلاك والتجزئة", "Consumer Non-Durables": "الاستهلاك والتجزئة", "Consumer Durables": "الاستهلاك والتجزئة",
    "Consumer Services": "الاستهلاك والتجزئة", "Producer Manufacturing": "الصناعة والنقل", "Industrial Services": "الصناعة والنقل",
    "Transportation": "الصناعة والنقل", "Non-Energy Minerals": "المعادن والمواد", "Process Industries": "المعادن والمواد",
    "Commercial Services": "الخدمات", "Distribution Services": "الخدمات", "Miscellaneous": "الخدمات",
}
US_LIST = sorted(set(US_SECTORS.values()))


def sa_sectors() -> list[str]:
    try:
        from app.data.saudi_directory import SYMBOL_TO_SECTOR_AR
        return sorted({v for v in SYMBOL_TO_SECTOR_AR.values() if v})
    except Exception:                                             # noqa: BLE001
        return []


def sector_of(sym: str, market: str, tv_sector: str | None = None) -> str | None:
    """قطاعُ الشركة بالعربية: السعوديُّ من دليلنا، والأمريكيُّ من قطاع تريدنق فيو."""
    if market == "sa":
        try:
            from app.data.saudi_directory import sector_of as sa_sector
            return sa_sector(str(sym).replace(".SR", ""))
        except Exception:                                         # noqa: BLE001
            return None
    return US_SECTORS.get(tv_sector or "")


WORLD_PROMPT = """أنت «صقر» — محلّلٌ واحدٌ للسوقين السعوديّ والأمريكيّ. أمامك عناوينُ الأخبار في آخر 36 ساعة (محليةٌ وعالمية) وحقائقُ السوق.
اقرأها وحدها — لا تُضف حدثاً ولا رقماً غيرَ مذكور — واستخرج المحاورَ التي تحرّك الأسهمَ الآن: النفطُ وأوبك، الفائدةُ والفيدراليّ، الجيوسياسيةُ
والممرّاتُ البحرية، أشباهُ الموصلات والتقنية، الصين، الدولار، السلع، قطاعٌ بعينه… ولكلّ محورٍ أثرُه على قطاعات السوقين — من القائمتين وحدهما.
قطاعاتُ السوق السعودي: {sa}
قطاعاتُ السوق الأمريكي: {us}
ثمّ نبرةُ كلّ سوقٍ من هذه المحاور وحقائقه (إيجابي · محايد · سلبي) بجملةٍ تذكر السبب. وإن خلت العناوينُ من محورٍ مؤثّرٍ فالقائمةُ فارغةٌ والنبرةُ «محايد».
أعد JSON فقط:
{{"themes": [{{"name": "اسمُ المحور بكلمتين", "dir": "إيجابي" أو "سلبي", "strength": 1 أو 2 أو 3, "why": "جملةٌ من العناوين نفسها",
   "sa": ["قطاعٌ سعوديٌّ من القائمة"], "us": ["قطاعٌ أمريكيٌّ من القائمة"]}}],
 "tone_sa": "إيجابي" أو "محايد" أو "سلبي", "why_sa": "جملة", "tone_us": "إيجابي" أو "محايد" أو "سلبي", "why_us": "جملة"}}

الحقائق:
{facts}

العناوين:
{heads}
"""


async def _headlines(hours: int = 36, limit: int = 60) -> list[tuple[str, str]]:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.market import MarketNews
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(MarketNews.headline, MarketNews.provider).where(MarketNews.published_at >= since)
                                     .order_by(MarketNews.published_at.desc()).limit(limit))).all()
        return [(str(h), str(p or "")) for h, p in rows if h]
    except Exception as e:                                        # noqa: BLE001
        logger.debug("عقلُ صقر/العناوين: {}", type(e).__name__)
        return []


async def _trend(sym: str) -> dict | None:
    from app.services import option_picks as OP
    from app.services.market_data import market_service as M
    try:
        return OP.trend_of(await asyncio.wait_for(M.get_bars(sym, "1d"), 25) or [])
    except Exception:                                             # noqa: BLE001
        return None


async def facts() -> dict:
    """حقائقُ السوق المشتركة: برنت · تاسي · ‏S&P 500 · ‏VIX — وما تعذّر غائبٌ لا يُخمَّن."""
    from app.services import saqr_sa as SA
    out: dict = {}
    try:
        out["brent"] = await SA.brent()
    except Exception:                                             # noqa: BLE001
        out["brent"] = None
    try:
        r = await SA.regime()
        out["tasi"] = {k: r.get(k) for k in ("verdict", "close", "sma50", "sma200", "ret3m", "chg")} if r else None
    except Exception:                                             # noqa: BLE001
        out["tasi"] = None
    spx = await _trend("^GSPC")
    out["spx"] = {k: spx.get(k) for k in ("state", "close", "sma50", "sma200", "ret3m")} if spx else None
    vix = await _trend("^VIX")
    out["vix"] = round(float(vix["close"]), 2) if vix and isinstance(vix.get("close"), (int, float)) else None
    return out


def facts_text(f: dict) -> str:
    b, t, s = f.get("brent") or {}, f.get("tasi") or {}, f.get("spx") or {}
    L = []
    if b:
        L.append(f"برنت {b.get('px')} دولاراً — اليوم {b.get('chg'):+.1f}٪" + (f" وخمسة أيام {b['chg5']:+.1f}٪" if isinstance(b.get("chg5"), (int, float)) else ""))
    if t:
        L.append(f"تاسي {t.get('close')} — مسارُه {t.get('verdict')}" + (f"، واليوم {t['chg']:+.2f}٪" if isinstance(t.get("chg"), (int, float)) else ""))
    if s:
        L.append(f"S&P 500 {s.get('close')} — مسارُه {s.get('state')}")
    if f.get("vix") is not None:
        L.append(f"مؤشّرُ الخوف VIX {f['vix']}")
    return "\n".join(f"- {x}" for x in L) or "- غيرُ متوفّرة"


def _pool(heads: list[tuple[str, str]], f: dict) -> list[float]:
    from app.services.saqr_council import _numbers
    return _numbers([h for h, _ in heads]) + _numbers(f)


def validate(obj: dict | None, heads: list[tuple[str, str]], f: dict) -> dict | None:
    """قراءةُ النموذج محروسة: المحورُ باتجاهٍ وقوّةٍ معروفين، وقطاعاتُه من القائمتين وحدهما، وجملتُه بلا رقمٍ ليس في العناوين والحقائق."""
    from app.services.chart_read import clean_text
    if not isinstance(obj, dict):
        return None
    pool, sa_ok, dropped = _pool(heads, f), set(sa_sectors()), 0
    themes = []
    for t in obj.get("themes") or []:
        if not isinstance(t, dict) or t.get("dir") not in DIRS:
            continue
        try:
            k = int(t.get("strength") or 0)
        except (TypeError, ValueError):
            continue
        why = clean_text(t.get("why"), pool)
        if not (1 <= k <= 3) or not why:
            dropped += 1
            continue
        sa = [x for x in (t.get("sa") or []) if x in sa_ok][:6]
        us = [x for x in (t.get("us") or []) if x in US_LIST][:6]
        if not sa and not us:
            continue
        themes.append({"name": str(t.get("name") or "")[:40], "dir": t["dir"], "strength": k, "why": why, "sa": sa, "us": us})
    tone = {m: (obj.get(f"tone_{m}") if obj.get(f"tone_{m}") in TONES else "محايد") for m in ("sa", "us")}
    why = {m: clean_text(obj.get(f"why_{m}"), pool) or "" for m in ("sa", "us")}
    return {"themes": themes[:8], "tone_sa": tone["sa"], "why_sa": why["sa"], "tone_us": tone["us"], "why_us": why["us"], "dropped": dropped}


async def world(force: bool = False) -> dict | None:
    """قراءةُ العالم الواحدة — مخبّأةٌ ساعتين ومحفوظة؛ وتعذّرُ النموذج يعيد آخرَ قراءةٍ محفوظةٍ بتاريخها، أو None."""
    from app.services import cache, lastgood
    from app.services import research_desk as RD
    if not force:
        hit = cache.get(KEY)
        if hit is not None:
            return hit or None
    heads, f = await _headlines(), await facts()
    out = None
    if heads or f.get("brent") or f.get("tasi"):
        prompt = WORLD_PROMPT.format(sa="، ".join(sa_sectors()), us="، ".join(US_LIST), facts=facts_text(f),
                                     heads="\n".join(f"- {h} ({p})" for h, p in heads) or "- لا عناوين")
        try:
            got = await RD._gemini([{"text": prompt}], max_tokens=1800, temperature=0.1)
        except Exception as e:                                    # noqa: BLE001
            logger.debug("عقلُ صقر/النموذج: {}", type(e).__name__)
            got = None
        v = validate(got, heads, f)
        if v:
            out = {**v, "facts": f, "n_heads": len(heads), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            lastgood.save(KEY, out)
    if out is None:
        old = lastgood.load(KEY)
        out = old if isinstance(old, dict) and old.get("themes") is not None else None
    cache.set(KEY, out or {}, TTL if out else 900)
    return out


def hits(w: dict | None, market: str, sector: str | None) -> list[dict]:
    """محاورُ العالم التي تخصّ قطاعَ الشركة في سوقها — الأقوى أوّلاً."""
    if not w or not sector:
        return []
    key = "sa" if market == "sa" else "us"
    return sorted([t for t in w.get("themes") or [] if sector in (t.get(key) or [])], key=lambda t: -t["strength"])


def theme_line(t: dict) -> str:
    return f"{t['name']} ({t['dir']}{' بقوّة' if t['strength'] >= 3 else ''}): {t['why']}"


# ══ «نظرتُنا» على تاسي من صقر ══════════════════════════════════════════════════════════════════════════
def _signals(t: dict) -> int:
    c, rsi = t.get("close"), t.get("rsi")
    return sum(1 for ok in (
        t.get("sma50") is not None and c is not None and c > t["sma50"],
        t.get("sma200") is not None and c is not None and c > t["sma200"],
        t.get("sma10") is not None and t.get("sma50") is not None and t["sma10"] > t["sma50"],
        (t.get("macd_hist") or 0) > 0,
        rsi is not None and 50 <= rsi < 70) if ok)


def outlook_from(tech: dict, breadth: dict | None, w: dict | None, f: dict | None, geo: dict | None, events: list[dict] | None) -> dict:
    """«نظرتُنا» من صقر — دالّةٌ خالصة: الإشاراتُ الفنيةُ الخمس أساس (0–5)، ثمّ يضيف كلُّ شاهدٍ أو ينقص بسببه:
    نبرةُ العالم للسوق السعوديّ (±1) · مسارُ تاسي الهابط (−1) · اتّساعُ الجلسة (مرتفعةٌ ثلثٌ فأقلّ −0.5 · ثلثان فأكثر +0.5) · الخطرُ الجيوسياسيّ
    (مرتفع −1 · متوسّط −0.5) · برنت خمسة أيام (−5٪ فأسوأ −0.5 · +5٪ فأكثر +0.5) — والحدثُ عالي الأثر خلال يومين لا يرفعها فوق «شراء حذر»،
    والقوّةُ النسبية 70 فأكثر «جني الأرباح» ما لم تهبط القراءةُ دونه."""
    s = _signals(tech)
    sc, why = float(s), [f"الإشاراتُ الفنية {s} من 5 (فوق متوسّطي 50 و200، و10 فوق 50، والماكد، والقوّةُ النسبية)"]
    tone = (w or {}).get("tone_sa")
    if tone == "إيجابي":
        sc += 1
        why.append("العالم: " + ((w or {}).get("why_sa") or "نبرةٌ إيجابيةٌ للسوق السعودي"))
    elif tone == "سلبي":
        sc -= 1
        why.append("العالم: " + ((w or {}).get("why_sa") or "نبرةٌ سلبيةٌ للسوق السعودي"))
    t = (f or {}).get("tasi") or {}
    if t.get("verdict") == "هابط":
        sc -= 1
        why.append("مسارُ تاسي هابط")
    up, dn = (breadth or {}).get("up"), (breadth or {}).get("down")
    if isinstance(up, (int, float)) and isinstance(dn, (int, float)) and up + dn > 0:
        r = up / (up + dn)
        if r <= 1 / 3:
            sc -= 0.5
            why.append(f"الاتّساعُ ضعيف: {int(up)} مرتفعة مقابل {int(dn)} منخفضة")
        elif r >= 2 / 3:
            sc += 0.5
            why.append(f"الاتّساعُ قويّ: {int(up)} مرتفعة مقابل {int(dn)} منخفضة")
    lv = (geo or {}).get("level")
    if lv == "مرتفع":
        sc -= 1
        why.append("الخطرُ الجيوسياسيّ مرتفع" + (f": {geo.get('why')}" if geo.get("why") else ""))
    elif lv == "متوسط":
        sc -= 0.5
        why.append("الخطرُ الجيوسياسيّ متوسّط")
    b5 = ((f or {}).get("brent") or {}).get("chg5")
    if isinstance(b5, (int, float)):
        if b5 <= -5:
            sc -= 0.5
            why.append(f"برنت {b5:+.1f}٪ في خمسة أيام — يضغط على السوق السعودي")
        elif b5 >= 5:
            sc += 0.5
            why.append(f"برنت {b5:+.1f}٪ في خمسة أيام")
    hi = [e for e in events or [] if e.get("impact") == "High"]
    rsi = tech.get("rsi")
    if rsi is not None and rsi >= 70 and sc >= 3:
        view = "جني الأرباح"
        why.append(f"القوّةُ النسبية {rsi:.0f} — تشبّعٌ شرائيّ")
    elif sc >= 4.5:
        view = "شراء"
    elif sc >= 3.5:
        view = "شراء حذر" if (tech.get("chg") or 0) >= 0 or sc >= 4 else "احتفاظ"
    elif sc >= 2.5:
        view = "احتفاظ"
    elif sc >= 1.5:
        view = "محايد"
    elif sc >= 0.5:
        view = "نظرة حذرة"
    else:
        view = "اتجاه هابط"
    if hi and view == "شراء":
        view = "شراء حذر"
        why.append(f"حدثٌ عالي الأثر خلال يومين: {hi[0].get('ar') or hi[0].get('title')}")
    return {"view": view, "score": round(sc, 1), "signals": s, "why": why[:6]}


async def outlook_sa(market: dict) -> dict | None:
    """«نظرتُنا» على تاسي من صقر بشواهدها كلِّها — أو None إن غاب الأساسُ الفنيّ."""
    tech = (market or {}).get("tech") or {}
    if tech.get("close") is None:
        return None
    from app.services import saqr_council as CN
    from app.services import saqr_sa as SA
    w = await world()
    try:
        g = await SA.geo()
    except Exception:                                             # noqa: BLE001
        g = None
    try:
        evs = await CN.events("sa")
    except Exception:                                             # noqa: BLE001
        evs = []
    out = outlook_from(tech, market.get("breadth"), w, (w or {}).get("facts") or await facts(), g, evs)
    out["themes"] = [theme_line(t) for t in (w or {}).get("themes") or [] if t.get("sa")][:4]
    return out
