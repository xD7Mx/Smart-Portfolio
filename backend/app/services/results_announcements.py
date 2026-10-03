"""‏D580: النتائجُ الربعية من إعلانات «تداول» — جدولٌ موحَّدٌ تنشره كلُّ شركة.

قِيس (كاشف results_ann_door): تبويبُ ملفّات XBRL في «تداول» يتوقّف عند 2022–2025 لكثيرٍ من الشركات
(سابك آخرُ ملفٍّ فيه يناير 2024، والتأمينُ منذ المعيار 17)، فامتنع القرارُ لستٍّ وخمسين شركةً بحجّة
«آخرُ قائمةٍ عمرُها 9 أشهر» وهي نشرت نتائجَ يونيو. وإعلانُ النتائج نفسُه يحمل جدولاً موحَّداً:
المبيعاتُ (أو إيرادُ التأمين)، وإجماليُّ الربح، والتشغيليّ، وصافي الربح، وحقوقُ الملكية، وربحيةُ السهم —
للربع (الحاليّ · المماثل · التغيّر · السابق · التغيّر) وللفترة حتى تاريخه (الحاليّ · المماثل · التغيّر)،
ثمّ سطرُ الوحدة «جميع الأرقام بالـ (مليار|مليون|الاف) ريال سعودي».

    from app.services.results_announcements import latest, refresh
    latest("2010")            # ← {as_of, months, quarter{…}, ytd{…}, unit, announced}
    await refresh(["2010"])   # يجلب ويحفظ
"""
from __future__ import annotations

import re
from datetime import date

from loguru import logger

STORE = "results:{}"
_UNITS = {"مليار": 1e9, "مليون": 1e6, "الاف": 1e3, "آلاف": 1e3, "ألف": 1e3, "الف": 1e3}
_EN_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"), 1)}
_AR_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7,
              "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}
# الحقلُ ← وسومُه (الأوّلُ الذي يطابق يُؤخذ)
_FIELDS = (
    ("revenue", ("المبيعات/الايرادات", "المبيعات/الإيرادات", "إيراد التأمين", "اجمالي دخل العمليات",
                 "إجمالي دخل العمليات", "إجمالي الإيرادات", "الإيرادات")),
    ("gross_profit", ("اجمالي الربح", "إجمالي الربح")),
    ("operating_income", ("الربح (الخسارة) التشغيلي",)),
    ("net_income", ("صافي الربح (الخسارة)",)),
    ("equity", ("إجمالي حقوق الملكية",)),
    ("eps", ("ربحية (خسارة) السهم",)),
)


def is_results_title(title: str) -> bool:
    """إعلانُ نتائجٍ ماليةٍ فعليّ — لا التقديريةُ ولا نتائجُ الجمعيات."""
    t = (title or "").lower()
    if any(w in t for w in ("estimated", "تقديري", "assembly", "الجمعية", "corrective", "تصحيحي")):
        return False
    return "financial result" in t or "النتائج المالية" in t


def _date(text: str) -> str | None:
    t = text or ""
    for pat, order in ((r"(20\d\d)-(\d{1,2})-(\d{1,2})", "ymd"), (r"(\d{1,2})[/-](\d{1,2})[/-](20\d\d)", "dmy"),
                       (r"(20\d\d)/(\d{1,2})/(\d{1,2})", "ymd")):
        m = re.search(pat, t)
        if m:
            g = m.groups()
            y, mo, d = (g[0], g[1], g[2]) if order == "ymd" else (g[2], g[1], g[0])
            try:
                return date(int(y), int(mo), int(d)).isoformat()
            except ValueError:
                continue
    m = re.search(r"(\d{1,2})[\s-]+([A-Za-z؀-ۿ]+)[\s-]+(20\d\d)", t)
    if m:
        mo = _EN_MONTHS.get(m.group(2).lower()) or _AR_MONTHS.get(m.group(2).rstrip("م"))
        if mo:
            try:
                return date(int(m.group(3)), mo, int(m.group(1))).isoformat()
            except ValueError:
                return None
    return None


def _months(title: str, as_of: str | None) -> int | None:
    t = (title or "").lower()
    for w, n in (("three", 3), ("ثلاث", 3), ("(3)", 3), ("six", 6), ("الستة", 6), ("ستة", 6), ("(6)", 6),
                 ("nine", 9), ("التسعة", 9), ("تسعة", 9), ("(9)", 9), ("annual", 12), ("السنوية", 12), ("year", 12)):
        if w in t:
            return n
    return {3: 3, 6: 6, 9: 9, 12: 12}.get(int(as_of[5:7])) if as_of else None


def _num(x: str) -> float | None:
    x = (x or "").strip().replace(",", "").replace("%", "")
    if x in ("", "-", "—"):
        return None
    try:
        return float(x)
    except ValueError:
        return None


def parse(text: str, title: str = "") -> dict | None:
    """متنُ الإعلان ← {as_of, months, unit, quarter{…}, ytd{…}} بالريال — أو None إن لم يكن فيه الجدول."""
    t = text or ""
    um = re.search(r"جميع الأرقام بالـ?\s*\(\s*([^)]+?)\s*\)", t)
    unit = next((v for k, v in _UNITS.items() if um and k in um.group(1)), None)
    if not unit:
        return None
    quarter: dict = {}
    ytd: dict = {}
    for line in t.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        label, vals = cells[0], cells[1:]
        if "سبب" in label:
            continue
        for key, tags in _FIELDS:
            if not any(label.startswith(tag) or tag in label for tag in tags):
                continue
            cur = _num(vals[0]) if vals else None
            scale = 1.0 if key == "eps" else unit
            v = cur * scale if cur is not None else None
            # خمسُ خاناتٍ = الربع (حاليّ · مماثل · تغيّر · سابق · تغيّر)؛ ثلاثٌ أو اثنتان = الفترةُ حتى تاريخه
            bucket = quarter if len(vals) >= 5 else ytd
            bucket.setdefault(key, v)
            break
    if not quarter and not ytd:
        return None
    as_of = _date(title) or _date(re.search(r"المنتهية في[^\n|]{0,40}", t).group(0)
                                  if re.search(r"المنتهية في", t) else "")
    if not as_of:
        return None
    return {"as_of": as_of, "months": _months(title, as_of), "unit": unit,
            "quarter": quarter, "ytd": ytd}


def latest(symbol: str) -> dict | None:
    from app.services import lastgood
    raw = lastgood.load(STORE.format(str(symbol).replace(".SR", "").strip())) or {}
    items = [x for x in raw.get("items") or [] if x.get("as_of")]
    return max(items, key=lambda x: x["as_of"]) if items else None


async def read_symbol(symbol: str, size: int = 30) -> dict:
    """يقرأ إعلاناتِ النتائج للشركة (الجديدَ وحده) ويحفظها."""
    from app.services import lastgood
    from app.services import tadawul_disclosure as D
    sym = str(symbol).replace(".SR", "").strip()
    key = STORE.format(sym)
    old = lastgood.load(key) or {}
    known = {x.get("id"): x for x in old.get("items") or []}
    items, new = [], 0
    for it in await D.list_for(sym, size=size):
        if not is_results_title(it.get("title") or ""):
            continue
        if it.get("id") in known:
            items.append(known[it["id"]])
            continue
        det = await D.detail(it["url"])
        p = parse((det or {}).get("text") or "", it.get("title") or "")
        if p:
            items.append({**p, "id": it.get("id"), "announced": it.get("date")})
            new += 1
        if len(items) >= 6:
            break
    rec = {"at": date.today().isoformat(), "items": items or old.get("items") or []}
    lastgood.save(key, rec)
    return {"symbol": sym, "new": new, "latest": (latest(sym) or {}).get("as_of")}


def due(symbols: list[str], today: date | None = None) -> list[str]:
    """من يحتاج قراءة: لا سجلَّ له، أو آخرُ نتيجةٍ أقدمُ من 80 يوماً ولم يُفحص منذ ثلاثة أيام."""
    from app.services import lastgood
    today = today or date.today()
    out = []
    for s in symbols:
        raw = lastgood.load(STORE.format(s)) or {}
        if not raw:
            out.append((10 ** 6, s))
            continue
        lt = (latest(s) or {}).get("as_of")
        try:
            age = (today - date.fromisoformat(lt)).days if lt else 10 ** 5
            checked = (today - date.fromisoformat(raw.get("at"))).days
        except (TypeError, ValueError):
            age, checked = 10 ** 5, 10 ** 5
        if age > 80 and checked >= 3:
            out.append((age, s))
    return [s for _, s in sorted(out, reverse=True)]


async def refresh(symbols: list[str] | None = None, limit: int = 80, conc: int = 3) -> dict:
    """يقرأ من حان دورُه (أو رموزاً بأعيانها) — الأقدمَ أوّلاً، بحدٍّ في الجولة."""
    import asyncio
    if symbols is None:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        symbols = due(sorted(main_market(MARKET_UNIVERSE).keys()))[:limit]
    sem = asyncio.Semaphore(conc)
    rep = {"symbols": len(symbols), "new": 0, "failed": 0}

    async def one(s):
        async with sem:
            try:
                r = await read_symbol(s)
                rep["new"] += r["new"]
            except Exception as e:                                # noqa: BLE001
                rep["failed"] += 1
                logger.warning(f"نتائجُ الإعلانات {s}: {type(e).__name__}: {str(e)[:100]}")
    await asyncio.gather(*(one(s) for s in symbols))
    logger.info(f"نتائجُ الإعلانات: {rep}")
    return rep
