"""هيكلُ الملكية من «تداول» — المصدرُ الرسميّ أوّلاً (D277).

## تصحيحُ مسار

قال المالك: «لدينا مصدرُ السوق الرسميّ، ولا شيءَ غيرُ متوفّر — واعتبره
دليلَ تخاذل». وهو محقّ: «تداول» تنشر هذه البنودَ في صفحة كلّ شركة، وأنا
نفسي كنتُ قد اكتشفتُ نقاطَها (‏`foreginOwnerShip` ·
`historicalBoardMembersWithDates`) حين فتحتُ طبقةَ الجلب المنتحِل — ثمّ
ذهبتُ إلى «أرقام» وبنيتُ عليها طبقةَ متصفّحٍ ثقيلةً، وقلتُ «غير متوفّر»
عمّا هو متوفّر. فالترتيبُ يعود إلى موضعه: **تداول ← أرقام**.

## وكيف تُقرأ

البوّابةُ تُولّد معرِّفاتٍ في المسار، فلا يُثبَّت مسار. ولا يُثبَّت **اسمُ
النداء** أيضاً: تُقرأ أسماءُ النداءات الموجودةُ في صفحة الشركة نفسِها
وتُصنَّف بكلماتها (ownership · shareholder · board) — فإن غيّرت «تداول»
اسماً بقي الاكتشافُ عاملاً، وإن اختفى بندٌ قيل غيابُه ولم يُختلق.

بلا متصفّح، وبلا نداءٍ لكلّ شركة في وقت الطلب: القراءةُ في الجدولة.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

from loguru import logger

STORE_KEY = "tadawul_own:{sym}"
MAX_AGE_DAYS = 30
MAX_ROWS = 60

_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z]{4,60})=/")

# كلماتُ التصنيف: البندُ يُعرَف من اسم ندائه لا من ترتيبه في الصفحة.
KINDS = {
    "foreign": re.compile(r"foreg|foreign.*owner|owner.*foreign", re.I),
    "board": re.compile(r"board.*member|member.*board", re.I),
    "major_holders": re.compile(r"(major|large|top).*(share|holder)|holder.*struct", re.I),
}

# مرشّحاتُ أسماء الحقول — أيُّها وُجد قُرئ، وما لم يوجد غاب.
NAME_KEYS = ("name", "shareholderName", "memberName", "investorName",
             "nameAr", "nameEn", "ownerName", "categoryName", "type")
PCT_KEYS = ("percentage", "percent", "ownershipPercentage", "ratio",
            "ownership", "share", "value")


def _num(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = re.sub(r"[,\s%]", "", str(x or ""))
    try:
        return float(s)
    except ValueError:
        return None


def _pick(row: dict, keys) -> object:
    low = {str(k).lower(): v for k, v in row.items()}
    for k in keys:
        v = low.get(k.lower())
        if v not in (None, "", "-"):
            return v
    return None


def normalize(rows: list) -> list[dict]:
    """صفوفُ «اسمٌ · نسبة». وصفٌّ بلا اسمٍ أو نسبةٍ معقولةٍ يُترك."""
    out: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        name = _pick(r, NAME_KEYS)
        pct = _num(_pick(r, PCT_KEYS))
        if not name or pct is None or not (0.0 <= pct <= 100.0):
            continue
        row = {"name": str(name).strip(), "percent": round(pct, 4)}
        # حقولٌ إضافيةٌ تُقرأ إن وُجدت — ولا تُختلق.
        for key, names in (("position", ("position", "jobTitle", "title")),
                           ("at", ("date", "asOfDate", "updateDate"))):
            v = _pick(r, names)
            if v:
                row[key] = str(v).strip()
        out.append(row)
        if len(out) >= MAX_ROWS:
            break
    return out


async def company_page(sym: str) -> str | None:
    """صفحةُ الشركة في «تداول» — رابطُها من لقطة السوق لا مؤلَّفاً."""
    from app.services.tadawul_market import row_for
    from app.services.tadawul_http import fetch

    url = (row_for(sym) or {}).get("company_url")
    if not url:
        return None
    if url.startswith("/"):
        url = "https://www.saudiexchange.sa" + url
    status, body = await fetch(url)
    return body if status == 200 and body else None


async def read_symbol(sym: str) -> dict:
    """يقرأ ما تنشره «تداول» لشركةٍ — أو سببَ التعذّر بنصِّه."""
    from app.services.tadawul_http import fetch

    body = await company_page(sym)
    if not body:
        return {"error": "لم تُقرأ صفحةُ الشركة في «تداول»"}
    mb = _BASE_RE.search(body)
    if not mb:
        return {"error": "لم يُعثر على أساس الصفحة"}
    base = mb.group(1).rstrip("/")

    names = sorted(set(_EP_RE.findall(body)))
    if not names:
        return {"error": "لا نداءَ في صفحة الشركة", "names": []}

    out: dict = {"names_seen": names}
    for kind, rx in KINDS.items():
        hit = next((n for n in names if rx.search(n)), None)
        if not hit:
            continue
        ep = next(m.group(0) for m in _EP_RE.finditer(body) if m.group(1) == hit)
        status, raw = await fetch(f"{base}/{ep}",
                                  params={"requestLocale": "en"}, referer=base)
        if status != 200 or not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:                                         # noqa: BLE001
            continue
        rows = data.get("data") if isinstance(data, dict) else data
        got = normalize(rows if isinstance(rows, list) else [])
        if got:                       # بندٌ بلا صفٍّ مفهومٍ يغيب لا يُصفَّر
            out[kind] = got
            out[f"{kind}_call"] = hit
    return out


async def refresh(sym: str) -> dict:
    """يقرأ ويحفظ — ولا يُكتب شيءٌ حين لا يُقرأ شيء."""
    from app.services import lastgood

    sym = str(sym or "").replace(".SR", "").strip()
    rec = await read_symbol(sym)
    body = [k for k in KINDS if k in rec]
    if not body:
        return {"error": rec.get("error") or "لم يُقرأ بندٌ واحدٌ مفهوم",
                "names_seen": rec.get("names_seen", [])[:12]}
    rec |= {"symbol": sym, "as_of": datetime.now(timezone.utc).date().isoformat(),
            "source": "تداول — صفحة الشركة"}
    lastgood.save(STORE_KEY.format(sym=sym), rec)
    logger.info("ملكيةُ «تداول» {}: {}", sym, ", ".join(body))
    return {"ok": True, "symbol": sym, "sections": body}


def reading(symbol) -> dict | None:
    """المحفوظُ لشركةٍ — أو None إن غاب أو شاخ."""
    from app.services import lastgood
    m = re.search(r"\b(\d{4})\b", str(symbol or ""))
    if not m:
        return None
    rec = lastgood.load(STORE_KEY.format(sym=m.group(1)))
    if not isinstance(rec, dict):
        return None
    try:
        age = (date.today() - date.fromisoformat(str(rec.get("as_of")))).days
    except Exception:                                             # noqa: BLE001
        return None
    return None if age > MAX_AGE_DAYS else rec
