"""لقطةُ السوق من «تداول» — المصدرُ يتقدّم المزوّد (D251).

## لماذا

بعد أن عُبرت الحمايةُ (‏D250) صار السوقُ مقروءاً من مُصدِره: نداءٌ واحدٌ
يعيد **كلَّ شركاتِ السوق الرئيسة** ومعها — منشورةً لا مشتقّةً — السعرُ
وحدّا العام والكمّيةُ المتداولة والإغلاقُ السابق والقطاعُ ورابطُ صفحة
الشركة. (وقِيس بعد أوّل جلبٍ حقيقيّ: المكرّرُ والمضاعفُ والقيمةُ السوقية
والعائدُ **صفرٌ في ‎272 من ‎272** — فلا يُبنى عليها وعدٌ وإن قُرئت.)

وهذه بعينها الحقولُ التي أتعبتنا: D239 و D244 و D246 و D247 كلُّها
خلافاتُ **اشتقاقٍ** — من ياهو، بسعرٍ غيرِ سعرِ اللحظة، وبمدًى اجتهدنا
فيه. والمصدرُ لا يُشتقّ منه: يُقرأ.

## القاعدة

  · **تداول أوّلاً، وياهو يملأ الفراغَ ولا يستبدل.** ترتيبٌ واحدٌ معلَن
    في مُنتِجٍ واحد (‏`valuation_fields`) لا في كلّ مسارٍ بيده.
  · **لقطةٌ لها زمن**: ما شاخ عن `MAX_AGE_SECONDS` لا يُقرأ سعراً
    حاضراً — لقطةُ أمسِ بجانب سعر اليوم رقمان لا يجتمعان.
  · **قائمةٌ قصيرةٌ تُرفَض**: دون `MIN_ROWS` جلبٌ فشل لا سوقٌ تقلّص —
    القاعدةُ نفسُها التي تحمي الدليل (‏D242).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from loguru import logger

STORE_KEY = "market:tadawul_snapshot"
PAGE = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
        "main-market-watch")
_BASE_RE = re.compile(r"<base[^>]+href=[\"']([^\"']+)", re.I)
_EP_RE = re.compile(r"p0/[A-Za-z0-9_=]*=NJgetMainNomucMarketDetails=/")

MIN_ROWS = 200            # دون ذلك: جلبٌ فشل لا سوقٌ تقلّص
MAX_AGE_SECONDS = 900     # لقطةٌ أقدمُ من ربع ساعةٍ ليست سعراً حاضراً


def _num(x) -> float | None:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d+(?:\.\d+)?", str(x or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _pos(x) -> float | None:
    v = _num(x)
    return v if v is not None and v > 0 else None


def normalize(rows: list) -> dict[str, dict]:
    """صفوفُ «تداول» ← رمزٌ ← حقولٌ بأسمائنا. وما لم يُفهم يُترك."""
    out: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        sym = re.search(r"\b(\d{4})\b", str(r.get("companyRef") or r.get("symbol") or ""))
        if not sym:
            continue
        px = _pos(r.get("lastTradePrice"))
        row = {
            "price": px,
            # ══ ما يعطيه المصدرُ فعلاً ══ (قِيس بعد أوّل جلبٍ حقيقيّ)
            # ادّعيتُ أن «تداول» تنشر المكرّرَ والمضاعفَ والقيمةَ السوقية
            # والعائد — والقياسُ على ‎272 شركةً: **صفرٌ من ‎272** في
            # أربعتها. وحارسي مرَّ لأنه أثبت قاعدةَ التقدّم على صفوفٍ
            # مصطنعةٍ لا وجودَ الرقم. والذي يعطيه فعلاً: السعرُ وحدّا
            # العام (‏272/272) والكمّيةُ (‏270/272) والإغلاقُ السابق.
            # فتبقى المفاتيحُ الأربعةُ مقروءةً (إن مُلئت يوماً استُعملت)
            # ولا يُبنى عليها وعد.
            "volume": _pos(r.get("volumeTraded")),
            "turnover": _pos(r.get("turnover")),
            "company_url": (str(r.get("companyUrl")).strip()
                            if r.get("companyUrl") else None),
            "name_en": (str(r.get("companyFullName") or r.get("companyName")).strip()
                        if (r.get("companyFullName") or r.get("companyName")) else None),
            "pe_ratio": _pos(r.get("PER")),
            "price_to_book": _pos(r.get("PBR")),
            "market_cap": _pos(r.get("marketCap")),
            "week52_high": _pos(r.get("high52WeekPrice")),
            "week52_low": _pos(r.get("low52WeekPrice")),
            "prev_close": _pos(r.get("previousClosePrice")),
            "change_pct": _num(r.get("precentChange")),
            "sector_en": (str(r.get("sectorName")).strip()
                          if r.get("sectorName") else None),
        }
        out[sym.group(1)] = {k: v for k, v in row.items() if v is not None}
    return out


async def fetch_rows() -> tuple[list, str | None]:
    """صفوفُ مراقبة السوق — أو (فارغ، سببُ التعذّر).

    العنوانُ يُشتقّ من الصفحة كما في قارئ الصكوك: «تداول» بوّابةٌ تُولّد
    معرِّفاتٍ في المسار، فتثبيتُها يجعلها تشيخ بلا إنذار.
    """
    from app.services.tadawul_http import fetch
    status, body = await fetch(PAGE)
    if status != 200 or not body:
        return [], f"HTTP {status} من صفحة مراقبة السوق"
    mb, me = _BASE_RE.search(body), _EP_RE.search(body)
    if not (mb and me):
        return [], ("لم يُعثر على "
                    + ("أساسِ الصفحة" if not mb else "نداءِ جدول السوق")
                    + " — تغيّرت بنيةُ الصفحة")
    status, body = await fetch(mb.group(1).rstrip("/") + "/" + me.group(0),
                               params={"sectorParameter": "All",
                                       "iswatchListSelected": "NO",
                                       "requestLocale": "en"}, referer=PAGE)
    if status != 200:
        return [], f"HTTP {status} من نقطة بيانات السوق"
    try:
        data = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return [], "مخرَجٌ غيرُ JSON من نقطة البيانات"
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return [], "لا صفوفَ في مخرَج نقطة البيانات"
    return rows, None


async def refresh() -> dict:
    """يجلب ويُطبّع ويحفظ — أو يعيد سببَ التعذّر بلا كتابة."""
    rows, why = await fetch_rows()
    if why:
        logger.warning("لقطةُ «تداول» لم تُقرأ: {}", why)
        return {"count": 0, "error": why}
    table = normalize(rows)
    if len(table) < MIN_ROWS:
        why = f"فُهم {len(table)} رمزاً من {len(rows)} صفّاً (الحدّ {MIN_ROWS})"
        logger.warning("لقطةُ «تداول» مرفوضة: {}", why)
        return {"count": 0, "error": why}
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "rows": table}
    from app.services import lastgood
    lastgood.save(STORE_KEY, rec)
    from app.services import cache
    cache.set(STORE_KEY, rec, MAX_AGE_SECONDS)
    logger.info("لقطةُ «تداول»: {} رمزاً", len(table))
    return {"count": len(table), "at": rec["at"]}


def snapshot() -> dict[str, dict]:
    """اللقطةُ الحاضرةُ — أو فارغةٌ إن غابت أو شاخت (لا رقمَ بزمنٍ مجهول)."""
    from app.services import cache
    rec = cache.get(STORE_KEY)
    if not isinstance(rec, dict):
        from app.services import lastgood
        rec = lastgood.load(STORE_KEY, max_age_seconds=MAX_AGE_SECONDS)
    if not isinstance(rec, dict):
        return {}
    rows = rec.get("rows")
    return rows if isinstance(rows, dict) else {}


INDEX_URL = ("https://www.saudiexchange.sa/tadawul.eportal.theme.helper/"
             "ThemeTASIUtilityServlet")
INDEX_KEY = "market:tasi:tadawul"
INDEX_TTL = 60                # اللسانُ مباشرٌ: دقيقةٌ واحدةٌ حدُّ التخزين


async def index_quote() -> dict | None:
    """رقمُ «تاسي» المباشرُ من خدمة المؤشّر في «تداول» (D252).

    كان اللسانُ يقرأ `^TASI.SR` من ياهو: متأخّرٌ عند المزوّد ومخزَّنٌ
    عندنا ربعَ ساعة — فيُعرض رقمٌ ليس رقمَ السوق الآن. والخدمةُ نفسُها
    تعطي القيمةَ والتغيّرَ والنسبةَ وحالةَ السوق ووقتَها.
    """
    from app.services.tadawul_http import fetch
    status, body = await fetch(INDEX_URL,
                               referer="https://www.saudiexchange.sa/wps/portal/"
                                       "saudiexchange/home")
    if status != 200 or not body:
        return None
    try:
        d = json.loads(body)
    except Exception:                                             # noqa: BLE001
        return None
    px = _pos(d.get("tasiValue"))
    if px is None:
        return None
    out = {
        "symbol": "^TASI",
        "price": px,
        "change": _num(d.get("tasiNetChange")),
        "change_pct": _num(d.get("tasiPercentageChange")),
        "source": "تداول",
        "as_of": str(d.get("currentTime") or "") or None,
        "market_status_code": d.get("marketStatusCode"),
        "mt30": _pos(d.get("mt30IndexValue")),
        "sukuk_index": _pos(d.get("sukukValue")),
    }
    from app.services import cache
    cache.set(INDEX_KEY, out, INDEX_TTL)
    return out


def row_for(symbol) -> dict:
    """صفُّ شركةٍ من اللقطة — أو فارغ."""
    sym = re.search(r"\b(\d{4})\b", str(symbol or ""))
    return (snapshot().get(sym.group(1)) or {}) if sym else {}
