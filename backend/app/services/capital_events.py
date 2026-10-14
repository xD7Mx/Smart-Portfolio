"""‏D674: أحداثُ رأس المال من إفصاحات «تداول» — نوعُ الحدث وتاريخُه، لا نسبتُه.

عددُ الأسهم من القوائم (الربحُ ÷ ربحيةِ السهم) يتخلّف عن كلّ تغيّرٍ في رأس المال حتى تُنشر قوائمُ بعده، وحَكَمُ السوق (الأسهمُ المصدرة
اليوم) يعرف العددَ ولا يعرف سببه. والسببُ يقلب الحكم:
  · منحةٌ أو تجزئةٌ أو تخفيضٌ لإطفاء خسائر — أسهمٌ بلا نقد: عددُ السوق صوابٌ والقوائمُ صحيحةٌ كما هي.
  · زيادةٌ بمقابل (حقوقُ أولوية · طرحٌ خاصّ · استحواذٌ بأسهم) — أسهمٌ ومعها نقدٌ أو أصولٌ ليست في القوائم بعد: لا عددُ القوائم صوابٌ
    ولا عددُ السوق، فلا رقمَ حتى تُنشر قوائمُ تشملها.
قِيس (‏capital_events_door · run 38437807275): الإفصاحاتُ تحمل الحدثَ لـ11 من 15 شركةً يخالف عددُها السوق، بنوعه وتاريخه؛ وقاعدةُ
النسبة (منحةٌ معياريّة ±1٪) سقطت لأنّ المنحةَ القديمة (المتقدمة 2022 · الجزيرة تكافل 2023) سبقت القوائمَ بسنوات فليست سببَ الفرق.
فالمعيارُ: حدثٌ **بعد** آخر قوائم، ونوعُه.

الحصّادُ يقرأ قائمةَ الإفصاحات وحدَها (طلبٌ لكلّ شركة، بتمهّل)، والقائمةُ تُجدَّد أسبوعياً — لا نصَّ يُجلب ولا رقمَ يُختلق.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta

from loguru import logger

STORE = "capev:events"       # {sym: {"h": "YYYY-MM-DD", "ev": [{"k": kind, "d": "YYYY-MM-DD", "t": title}]}}
MAX_AGE_DAYS = 7
LINK_DAYS = 400              # إعلانُ «زيادة رأس المال» بلا نوعٍ يرث نوعَ أقرب توصيةٍ قبله في هذه المدّة
DEVIATION = 1.15             # فرقُ العدد الذي يستدعي السؤالَ عن الحدث

_REDUCTION = re.compile(r"capital\s+(decrease|reduction)|(reduc|decreas)\w*\s+(of\s+)?(its\s+|the\s+)?(company.s\s+)?(share\s+)?capital|"
                        r"تخفيض\s+رأس", re.I)
_PAID = re.compile(r"rights?\s+issues?|right\s+shares|new\s+shares\s+subscription|privately|private\s+placement|"
                   r"for\s+the\s+purpose\s+of\s+acquir|by\s+means\s+of\s+a\s+capital\s+increase|in\s+exchange\s+for|"
                   r"share\s+purchase\s+and\s+subscription|حقوق\s+(ال)?أولوية|طرح\s+خاص|مقابل\s+الاستحواذ", re.I)
_BONUS = re.compile(r"bonus|bouns|stock\s+split|share\s+split|منحة|تجزئة", re.I)
_INCREASE = re.compile(r"capital\s+increase|increas\w*\s+(of\s+)?(its\s+|the\s+)?(company.s\s+)?(share\s+)?capital|زيادة\s+رأس", re.I)
_FRACTION = re.compile(r"fraction|كسور", re.I)
# الحدثُ النافذ لا المعلَن: التوصيةُ وتقديمُ الطلب وتعيينُ المستشار ودعوةُ الجمعية لا تغيّر عدداً — قِيس في الحصاد الأوّل
# (run 38491266548): «ميثانول» و«البحر الأحمر» حُجبتا بطلب حقوق أولويةٍ لم يُنفَّذ. فالمعتبرُ ما يدلّ على التنفيذ:
# نتائجُ الجمعية أو الطرح، والتخصيص، وتعويضُ أصحاب الحقوق، وبدءُ تداول الحقوق، وإيداعُ الكسور، وإدراجُ الأسهم الجديدة.
_EFFECTIVE = re.compile(r"results?\s+of\s+(the\s+)?(extraordinary\s+|ordinary\s+)?general\s+assembly|"
                        r"results?\s+of\s+(the\s+)?(rump|remaining)\s+offering|allo(cation|tment)\s+of\s+(the\s+)?(right|new|shares)|"
                        r"distribution\s+of\s+compensation|start\s+of\s+(the\s+)?rights?\s+issues?\s+trading|"
                        r"deposit\s+of\s+(the\s+)?(amounts|proceeds|sums)|(sale|selling)\s+of\s+(the\s+)?(shares\s+)?fraction|"
                        r"listing\s+of\s+(the\s+)?new\s+shares|نتائج\s+(اجتماع\s+)?الجمعية|إيداع|تخصيص", re.I)


def classify(title: str | None) -> str | None:
    """نوعُ الحدث من عنوان الإفصاح: ‎reduction · paid · bonus · increase (بلا نوع) — أو لا شيء."""
    t = str(title or "")
    if _REDUCTION.search(t):
        return "reduction"
    if _PAID.search(t):
        return "paid"
    if _BONUS.search(t):
        return "bonus"
    if _INCREASE.search(t):
        # بيعُ كسور الأسهم لا يكون إلّا من منحة (حقوقُ الأولوية تُعوَّض بعنوانها) — فهو نوعٌ لا مجهول
        return "bonus" if _FRACTION.search(t) else "increase"
    return None


def effective(title: str | None) -> bool:
    """أيدلّ العنوانُ على حدثٍ نُفِّذ (لا توصيةٍ ولا طلبٍ ولا دعوة)؟"""
    return bool(_EFFECTIVE.search(str(title or "")))


def resolve(events: list[dict]) -> list[dict]:
    """«زيادةُ رأس المال» بلا نوع (نتائجُ الجمعية · المستجدّات) ترث نوعَ أقرب حدثٍ مسمّى قبلها — التوصيةُ تسبق الإقرار."""
    ev = sorted((dict(e) for e in events if e.get("d")), key=lambda e: e["d"])
    for j, e in enumerate(ev):
        if e["k"] != "increase":
            continue
        d0 = date.fromisoformat(e["d"])
        for p in reversed(ev[:j]):
            if p["k"] in ("paid", "bonus") and (d0 - date.fromisoformat(p["d"])).days <= LINK_DAYS:
                e["k"] = p["k"]
                break
    return ev


def _store() -> dict:
    from app.services import lastgood
    return dict(lastgood.load(STORE) or {})


def events_of(symbol: str) -> list[dict]:
    s = re.sub(r"\D", "", str(symbol or ""))[:4]
    return resolve(((_store().get(s) or {}).get("ev")) or [])


def kind_after(symbol: str, as_of: str | None) -> dict | None:
    """أثقلُ حدثٍ **نافذٍ** بعد تاريخ آخر قوائم ← {kind, date, title}: الزيادةُ بمقابل أوّلاً (فيها نقدٌ غائب)، ثمّ المنحةُ
    والتخفيض. والمعلَنُ الذي لم يُنفَّذ لا يغيّر عدداً فلا يُحكم به."""
    if not as_of:
        return None
    after = [e for e in events_of(symbol) if e["d"] > str(as_of)[:10] and effective(e.get("t"))]
    for k in ("paid", "bonus", "reduction"):
        hit = [e for e in after if e["k"] == k]
        if hit:
            last = hit[-1]
            return {"kind": k, "date": last["d"], "title": last.get("t")}
    return None


def harvested(symbol: str) -> bool:
    s = re.sub(r"\D", "", str(symbol or ""))[:4]
    return bool((_store().get(s) or {}).get("h"))


async def harvest(symbols: list[str] | None = None, max_age_days: int = MAX_AGE_DAYS, pause: float = 1.5,
                  limit: int | None = None) -> dict:
    """يقرأ قائمةَ إفصاحات كلّ شركةٍ لم تُقرأ منذ ‎max_age_days ويحفظ أحداثَ رأس مالها — الأقدمُ قراءةً أوّلاً."""
    from app.services import lastgood
    from app.services.tadawul_disclosure import list_for
    if symbols is None:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market, is_nomu
        symbols = [s for s in main_market(MARKET_UNIVERSE) if not is_nomu(s)]
    store = _store()
    cut = (date.today() - timedelta(days=max_age_days)).isoformat()
    due = sorted((re.sub(r"\D", "", str(s))[:4] for s in symbols), key=lambda s: (store.get(s) or {}).get("h") or "")
    due = [s for s in due if len(s) == 4 and ((store.get(s) or {}).get("h") or "") <= cut]
    if limit:
        due = due[:limit]
    done, failed, with_ev = 0, 0, 0
    for s in due:
        try:
            rows = await list_for(s, 80)
        except Exception as e:                                     # noqa: BLE001
            logger.debug("أحداثُ رأس المال {}: {}", s, e)
            rows = []
        if not rows:
            failed += 1                                            # الفراغُ تعذّرٌ لا «لا أحداث» — يُعاد في الجولة التالية
            await asyncio.sleep(pause)
            continue
        ev = [{"k": k, "d": str(r.get("date"))[:10], "t": str(r.get("title") or "")[:200]}
              for r in rows if r.get("date") and (k := classify(r.get("title")))]
        store = _store()                                           # لا يُكتب فوق ما حفظته عمليّةٌ أخرى أثناء الجولة
        store[s] = {"h": date.today().isoformat(), "ev": ev}
        lastgood.save(STORE, store)
        done += 1
        with_ev += bool(ev)
        await asyncio.sleep(pause)
    return {"due": len(due), "read": done, "failed": failed, "with_events": with_ev}
