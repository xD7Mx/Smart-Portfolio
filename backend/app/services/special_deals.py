"""الصفقاتُ الخاصة — من «تداول»، باكتشافِ النداء لا بتثبيته (D273).

## لماذا

طلبها المالكُ صراحةً ولم تُبنَ — سهوٌ منّي، لا قرارٌ. وهي معنًى لا يُقاس
من شريط الأسعار: صفقةٌ متفاوَضٌ عليها خارج دفتر الأوامر، بحجمٍ كبيرٍ وسعرٍ
قد يخالف سعرَ السوق، وكثيراً ما تسبق تغيّرَ ملكيةٍ مؤثّرة.

## كيف تُقرأ

«تداول» بوّابةٌ تُولّد معرِّفاتٍ في المسار، وتثبيتُ المسار يجعله يشيخ بلا
إنذار. فتُقرأ النقطةُ من الصفحة نفسِها: `<base href>` ثمّ نداءُ الجدول
بالاسم — وهي الطريقةُ التي فتحت الصكوكَ ومراقبةَ السوق (‏D249 · D251).

وأسماءُ الحقول **لم تُقَس بعد**: «تداول» محجوبةٌ عن حاويتي اليوم. فالقارئُ
يقبل عدّةَ أسماءٍ محتملةٍ لكلّ حقل، ولا يخترع حقلاً غائباً — وصفٌّ بلا
رمزٍ أو سعرٍ أو كمّيةٍ **يُترك**، ولا يُعرض نصفُ صفقة. والقياسُ بالمسبار
على الخادم، وحتى يُقاس يقول التطبيقُ «غير متوفّر».
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from loguru import logger

STORE_KEY = "market:special_deals"
MAX_AGE_SECONDS = 15 * 60
MAX_ROWS = 200

PAGE = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/trading/"
        "participants-and-deals/special-deals")
_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
# اسمُ النداء يُلتقط بنمطه لا بمعرِّفٍ محفوظ: البوّابةُ تُدير المعرِّف،
# ويبقى اسمُ الخدمة. وعدّةُ تسمياتٍ محتملةٍ لأن الاسمَ لم يُقَس بعد.
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJ(get[A-Za-z]*(?:Special|Negotiat)[A-Za-z]*)=/")

# مرشّحاتُ الأسماء لكلّ حقل، بالترتيب. وما لم يوجد يغيب.
FIELDS = {
    "symbol": ("symbol", "companySymbol", "tradingName", "companyCode"),
    "name": ("companyName", "companyFullName", "issuerName"),
    "price": ("price", "dealPrice", "executionPrice", "tradePrice"),
    "quantity": ("quantity", "volume", "dealVolume", "numberOfShares"),
    "value": ("value", "turnover", "dealValue", "totalValue"),
    "at": ("date", "dealDate", "tradeDate", "executionDate", "dateTime"),
}


def _num(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = re.sub(r"[,\s]", "", str(x or ""))
    try:
        return float(s)
    except ValueError:
        return None


def _pick(row: dict, names: tuple[str, ...]):
    for n in names:
        for k, v in row.items():
            if str(k).lower() == n.lower() and v not in (None, "", "-"):
                return v
    return None


def normalize(rows: list) -> list[dict]:
    """صفوفُ المصدر ← صفقاتٌ مفهومة. وناقصُ الأركان يُترك لا يُرمَّم."""
    out: list[dict] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        sym = _pick(r, FIELDS["symbol"])
        m = re.search(r"\b(\d{4})\b", str(sym or ""))
        price = _num(_pick(r, FIELDS["price"]))
        qty = _num(_pick(r, FIELDS["quantity"]))
        # الأركانُ الثلاثة: رمزٌ وسعرٌ وكمّية. وبلا أحدها ليست صفقةً تُعرض.
        if not m or price is None or price <= 0 or qty is None or qty <= 0:
            continue
        val = _num(_pick(r, FIELDS["value"]))
        deal = {"symbol": m.group(1), "price": price, "quantity": qty,
                "value": val if val is not None else round(price * qty, 2)}
        name = _pick(r, FIELDS["name"])
        if name:
            deal["name"] = str(name).strip()
        at = _pick(r, FIELDS["at"])
        if at:
            deal["at"] = str(at).strip()
        out.append(deal)
        if len(out) >= MAX_ROWS:
            break
    return out


async def fetch_rows() -> tuple[list, str | None]:
    """صفوفُ الصفقات الخاصة — أو (فارغ، سببُ التعذّر) بنصِّه."""
    from app.services.tadawul_http import fetch
    status, body = await fetch(PAGE)
    if status != 200 or not body:
        return [], f"HTTP {status} من صفحة الصفقات الخاصة"
    mb, me = _BASE_RE.search(body), _EP_RE.search(body)
    if not (mb and me):
        return [], ("لم يُعثر على "
                    + ("أساسِ الصفحة" if not mb else "نداءِ جدول الصفقات")
                    + " — تُقاس البنيةُ بالمسبار على الخادم")
    status, body = await fetch(mb.group(1).rstrip("/") + "/" + me.group(0),
                               params={"requestLocale": "en"}, referer=PAGE)
    if status != 200:
        return [], f"HTTP {status} من نقطة الصفقات الخاصة"
    try:
        data = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return [], "مخرَجٌ غيرُ JSON من نقطة الصفقات"
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return [], "لا صفوفَ في مخرَج نقطة الصفقات"
    return rows, None


async def refresh() -> dict:
    """يجلب ويُطبّع ويحفظ. ولا يُكتب فراغٌ فوق قراءةٍ سابقةٍ صالحة."""
    rows, why = await fetch_rows()
    if why:
        logger.warning("الصفقاتُ الخاصة لم تُقرأ: {}", why)
        return {"count": 0, "error": why}
    deals = normalize(rows)
    if not deals:
        # يومٌ بلا صفقاتٍ خاصّةٍ **وارد** — لكنّه لا يُميَّز هنا عن أسماءِ
        # حقولٍ لم تُطابَق. فلا يُمحى المحفوظُ، ويُقال العددُ الخام.
        why = f"لم تُفهَم صفقةٌ من {len(rows)} صفّاً"
        logger.warning("الصفقاتُ الخاصة: {}", why)
        return {"count": 0, "error": why, "raw_rows": len(rows)}
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "deals": deals}
    from app.services import cache, lastgood
    lastgood.save(STORE_KEY, rec)
    cache.set(STORE_KEY, rec, MAX_AGE_SECONDS)
    logger.info("الصفقاتُ الخاصة: {} صفقة", len(deals))
    return {"count": len(deals), "at": rec["at"]}


def reading() -> dict | None:
    """المحفوظُ — أو None إن غاب أو شاخ."""
    from app.services import cache, lastgood
    rec = cache.get(STORE_KEY)
    if not isinstance(rec, dict):
        rec = lastgood.load(STORE_KEY, max_age_seconds=MAX_AGE_SECONDS)
    return rec if isinstance(rec, dict) and rec.get("deals") else None


def for_symbol(symbol) -> list[dict]:
    """صفقاتُ شركةٍ بعينها — أو قائمةٌ فارغة."""
    m = re.search(r"\b(\d{4})\b", str(symbol or ""))
    if not m:
        return []
    return [d for d in ((reading() or {}).get("deals") or [])
            if d.get("symbol") == m.group(1)]
