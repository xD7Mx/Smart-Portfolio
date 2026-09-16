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

import asyncio

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
MAX_AGE_SECONDS = 300     # لقطةٌ أقدمُ من خمس دقائقَ ليست سعراً لحظياً


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
            # ══ عمقُ السوق: ما يُنشَر فعلاً ══ (D262)
            # طلب المالك عمقَ السوق «حتى 20x». وهذه التغذيةُ تحمل
            # **مستوًى واحداً** فقط (أفضلَ طلبٍ وعرضٍ بكمّيتيهما) — وهو
            # ما تنشره «تداول» مجّاناً؛ وعشرون مستوًى تغذيةٌ أخرى تُقاس
            # قبل أن تُوعَد. فيُؤخذ الموجودُ بلا نداءٍ زائد، ويُسمّى بما
            # هو: مستوًى واحد.
            "bid": _pos(r.get("bidPrice")),
            "bid_qty": _pos(r.get("bidQuantity")),
            "ask": _pos(r.get("askPrice")),
            "ask_qty": _pos(r.get("askQuantity")),
            "trades": _pos(r.get("nuOfTrades")),
            "day_high": _pos(r.get("highPrice")),
            "day_low": _pos(r.get("lowPrice")),
            "day_open": _pos(r.get("todayOpen")),
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


CLOSE_MAX_DAYS = 5          # أطولُ عطلةٍ معقولة: عيدٌ متّصلٌ بنهاية أسبوع


def _age_of(rec) -> float | None:
    """عمرُ سجلٍّ بزمنه المُعلَن (`at`) — أو None إن لم يُفصح عنه.

    ══ زمنُ الحفظ ليس زمنَ القراءة ══ (D298)
    كان العمرُ يُقاس بزمن **حفظ** الملفّ، فسجلٌّ زمنُه المُعلَن قديمٌ
    وحُفظ الآن يُقرأ «حيّاً». وهما يتّفقان عندنا اليومَ لأن المنتِجَ يختم
    بساعتنا، لكنّ القاعدةَ تُكتب على الزمن المُعلَن لا على واقعةِ الكتابة.
    """
    at = (rec or {}).get("at") if isinstance(rec, dict) else None
    if not at:
        return None
    try:
        from datetime import datetime, timezone
        t = datetime.fromisoformat(str(at))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:                                             # noqa: BLE001
        return None


def reading() -> dict | None:
    """السجلُّ الحيُّ بكامله (صفوفٌ وزمن) — أو None إن غاب أو شاخ.

    منتِجٌ واحدٌ للحيّ: `snapshot()` تأخذ صفوفَه، و`usable_rows()` تأخذ
    زمنَه معها — فلا يُدفَع رقمٌ «حيٌّ» بلا زمنٍ كما كان يحدث بعد كلّ
    إقلاعٍ (الذاكرةُ فارغةٌ فيُقرأ المحفوظ، والزمنُ كان يُقرأ من الذاكرة).
    """
    from app.services import cache, lastgood
    rec = cache.get(STORE_KEY)
    if not isinstance(rec, dict):
        rec = lastgood.load(STORE_KEY, max_age_seconds=MAX_AGE_SECONDS)
    if not isinstance(rec, dict) or not isinstance(rec.get("rows"), dict):
        return None
    age = _age_of(rec)
    if age is not None and age > MAX_AGE_SECONDS:
        return None
    return rec


def snapshot() -> dict[str, dict]:
    """اللقطةُ **الحيّة** — أو فارغةٌ إن غابت أو شاخت.

    تبقى صارمةً: ما يُعرض على أنه لحظيٌّ يجب أن يكون لحظياً، وسعرٌ عمرُه
    ساعتان داخلَ الجلسة كذبٌ لا تأخّر.
    """
    rec = reading()
    return rec["rows"] if rec else {}


# ══ اللحظيةُ الحقيقيةُ في المصدر لا في الشاشة ══ (D289)
# قال المالك: «لا أقبل بتأخير 15 ثانية، أريد أسعاراً لحظيةً فورية».
# والحدُّ لم يكن في الشاشة: النبضُ كان ‎15 ثانيةً، لكنّ **اللقطةَ نفسَها
# مجدوَلةٌ كلَّ دقيقة** — فالتأخيرُ الحقيقيُّ دقيقةٌ كاملةٌ في أسوأ الحال،
# والشاشةُ تسأل أربعَ مرّاتٍ عن الرقم نفسِه.
#
# والجدولةُ وحدَها لا تحلّها: دقيقةٌ سقفُها الطبيعيّ. فتُضاف **طزاجةٌ عند
# الطلب**: كلُّ نداءٍ يخصّ السعر يوقظ تجديداً إن شاخت اللقطةُ أكثرَ من
# `LIVE_TTL`، ثمّ **يعود فوراً بما عنده** — لا يحبس الشاشةَ في انتظار
# الشبكة. فالمُشاهدُ يرى الرقمَ الحاضرَ الآن، والذي بعده أحدثُ منه.
#
# وثلاثةُ قيودٍ تمنع ضغطاً على المصدر:
#   ١· **نداءٌ واحدٌ في الطريق** (‏single-flight): مئةُ طلبٍ متوازٍ توقظ
#      تجديداً واحداً لا مئة — وهذا هو الفرقُ بين لحظيةٍ وإغراقٍ.
#   ٢· **في الجلسة فقط**: السوقُ مغلقٌ ⇒ لا تجديدَ عند الطلب أصلاً.
#   ٣· **حدٌّ أدنى بين تجديدين** حتى لو تدفّقت الطلبات.
LIVE_TTL = 5                 # ثوانٍ: أقصى شيخوخةٍ مقبولةٍ داخل الجلسة
_inflight: "asyncio.Task | None" = None
_last_kick = 0.0


def age_seconds() -> float | None:
    """عمرُ اللقطة بالثواني — أو None إن غابت. وقارئُ الزمن **واحد**."""
    from app.services import cache, lastgood
    rec = cache.get(STORE_KEY)
    if not isinstance(rec, dict):
        rec = lastgood.load(STORE_KEY, max_age_seconds=CLOSE_MAX_DAYS * 86400)
    return _age_of(rec) if isinstance(rec, dict) else None


def ensure_fresh(max_age: float = LIVE_TTL) -> bool:
    """يوقظ تجديداً إن شاخت اللقطة — ولا ينتظره. (أأُوقظ؟)"""
    global _inflight, _last_kick
    import time

    from app.services.market_phase import market_phase

    now = datetime.now()
    if market_phase((now.weekday() + 1) % 7,
                    now.hour * 60 + now.minute) == "closed":
        return False                      # مغلقٌ: لا شيءَ يتجدّد
    if _inflight is not None and not _inflight.done():
        return False                      # نداءٌ واحدٌ في الطريق
    age = age_seconds()
    if age is not None and age < max_age:
        return False
    if time.monotonic() - _last_kick < max_age:
        return False                      # حدٌّ أدنى بين تجديدين
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    _last_kick = time.monotonic()
    _inflight = loop.create_task(_kick())
    return True


async def _kick() -> None:
    try:
        rec = await refresh()
        if not rec.get("count"):
            logger.debug("تجديدٌ لحظيٌّ لم يُقرأ: {}", rec.get("error"))
    except Exception as e:                                        # noqa: BLE001
        logger.debug("تجديدٌ لحظيٌّ تعذّر: {}: {}", type(e).__name__, e)


def usable_rows() -> tuple[dict[str, dict], bool, str | None]:
    """(الصفوف، أحيّةٌ هي؟، زمنُها) — للاستعمال لا للعرض اللحظيّ (D285).

    ══ اللقطةُ كانت ترفض نفسَها في العطلة ══
    قِيس على الخادم: «بلا سعرٍ في اللقطة: ‎40 من ‎40» — والسوقُ مغلقٌ منذ
    الخميس. فقاعدةُ الطزاجة (‏300 ثانية) صُمّمت لمنع سعرٍ قديمٍ يُعرض
    لحظياً، وهي صوابٌ **داخل الجلسة**؛ لكنّها خارجَها تمحو آخرَ إغلاقٍ
    مسجَّل — وهو الرقمُ الصحيحُ الوحيدُ في ذلك الوقت. فيفقد التطبيقُ
    السعرَ والعمقَ والسعرَ العادلَ يومين في الأسبوع بلا سبب.
    والجهلُ ليس حكماً: عندنا الرقمُ، ونرفض قراءتَه.

    فالسؤالان يُفصَلان: `snapshot()` للحيّ، وهذه للاستعمال — تقبل آخرَ
    إغلاقٍ **حين يكون السوقُ مغلقاً فعلاً** (بالحاكم الواحد لا بالساعة)
    وبعمرٍ لا يتجاوز أطولَ عطلةٍ معقولة، وتقول دائماً **أحيّةٌ هي**
    فيُعلن المستعمِلُ ذلك ولا يُوهِم أنه لحظيّ.
    """
    from datetime import datetime

    from app.services import cache, lastgood
    from app.services.market_phase import market_phase

    rec = reading()
    if rec:
        # الزمنُ من السجلِّ الذي أعطى الصفوفَ نفسِه — لا من مخزنٍ آخرَ قد
        # يكون فارغاً فيُدفَع «حيٌّ» بزمنٍ معدوم (D298).
        return rec["rows"], True, rec.get("at")

    now = datetime.now()
    if market_phase((now.weekday() + 1) % 7, now.hour * 60 + now.minute) != "closed":
        return {}, False, None          # داخلَ الجلسة: لا بديلَ عن الحيّ
    rec = lastgood.load(STORE_KEY, max_age_seconds=CLOSE_MAX_DAYS * 86400)
    if not isinstance(rec, dict) or not isinstance(rec.get("rows"), dict):
        return {}, False, None
    return rec["rows"], False, rec.get("at")


# ══ بابُ المؤشّر: المقيسُ لا الموروث ══ (D327)
# قِيس على خادم المالك والسوقُ مفتوح: `RefreshTradeDetailsServlet` يقول
# `max-age=60`، وقيمةُ تاسي فيه تغيّرت ثلاثَ مرّاتٍ في ١٤٠ ثانيةً
# (فواصلُ ٧ · ٤٨ · ٦١) — أي إيقاعُ دقيقة. و`TickerServlet` لم يتغيّر في
# ١٤٠ ثانية. وكان قارئُ المؤشّر عندي ينادي باباً ثالثاً
# (`ThemeTASIUtilityServlet`) **لم أقِس إيقاعَه قطّ** — فنُقل إلى المقيس،
# وبقي الموروثُ بديلاً إن تعذّر الأوّل.
INDEX_URL = ("https://www.saudiexchange.sa/tadawul.eportal.theme.helper/"
             "RefreshTradeDetailsServlet")
INDEX_URL_ALT = ("https://www.saudiexchange.sa/tadawul.eportal.theme.helper/"
                 "ThemeTASIUtilityServlet")
INDEX_KEY = "market:tasi:tadawul"
# ══ وذاكرتُه بإيقاع بابه لا بنبض شاشتنا ══ (D327)
# كانت ثانيةً واحدة: أي ستّون نداءً لكلّ نشرةٍ واحدةٍ من ستّين ثانية،
# تعود كلُّها بالجسم نفسِه بالحرف — وهو عطبُ D326 بعينه في المؤشّر.
# فصارت خمسَ عشرةَ ثانية: تأخيرُ الاكتشاف ≤ ١٥ث على إيقاعٍ من ٦٠ث،
# وأربعُ نداءاتٍ في الدقيقة بدل ستّين.
INDEX_TTL = 15
# (كانت ثلاثاً؛ وقد سأل المالك: «بثانيةٍ واحدةٍ أو صفر؟». والأسعارُ تُجدَّد
#  كلَّ ثانيةٍ في المضخّة، فذاكرةُ المؤشّر ثلاثُ ثوانٍ كانت تُبقيه أبطأَ من
#  جاره في الدفعة نفسِها. والنداءُ خفيفٌ وواحدٌ في الطريق ولا يُنتظَر.)
# (كانت خمسَ عشرةَ ثانيةً — وهي تُسقط ثلاثةَ أخماسِ تغيّرات المؤشّر حين
#  تسأل الشاشةُ كلَّ ثلاثِ ثوان. والخدمةُ نداءٌ صغيرٌ واحد · D289.)
# ══ اللحظيةُ زمنٌ لا لون ══ (بأمر المالك · D260)
# «أريد الأسعارَ لحظيةً للتطبيق بالكامل، ولسانُ تاسي يومض عند التغيّر».
# والوميضُ مبنيٌّ أصلاً — لكنه لا يشتعل إن لم يتغيّر الرقمُ الواصل.
# فالعلاجُ في زمن الوصول: خدمةُ المؤشّر نداءٌ واحدٌ خفيف، فتُقرأ كلَّ
# ربع دقيقة؛ ولقطةُ السوق نداءٌ واحدٌ لكلّ الشركات، فتُجدَّد كلَّ دقيقة.


async def index_quote() -> dict | None:
    """رقمُ «تاسي» المباشرُ من خدمة المؤشّر في «تداول» (D252).

    كان اللسانُ يقرأ `^TASI.SR` من ياهو: متأخّرٌ عند المزوّد ومخزَّنٌ
    عندنا ربعَ ساعة — فيُعرض رقمٌ ليس رقمَ السوق الآن. والخدمةُ نفسُها
    تعطي القيمةَ والتغيّرَ والنسبةَ وحالةَ السوق ووقتَها.
    """
    from app.services.tadawul_http import fetch
    HOME = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/home")
    d = None
    for url in (INDEX_URL, INDEX_URL_ALT):
        try:
            status, body = await fetch(url, referer=HOME)
        except Exception as e:                                    # noqa: BLE001
            logger.debug("المؤشّر: {} تعذّر {}", url[-34:], type(e).__name__)
            continue
        if status != 200 or not body:
            continue
        try:
            got = json.loads(body)
        except Exception:                                         # noqa: BLE001
            continue
        if isinstance(got, dict) and got.get("tasiValue") is not None:
            d = got
            break
    if d is None:
        return None
    # ══ الرقمُ الخامُ يُقدَّم على النصِّ المفصول ══ (D327)
    # في الجسم كما وصل: `"tasiValue": "10,787.98"` نصٌّ بفاصلة، وفي
    # `tasiBean.tasiTodaysSummaryBean` الرقمُ نفسُه خاماً
    # (`indexPrice: 10787.98 · percentChange: 0.06`). فيُقرأ الخامُ أوّلاً
    # — لا كسرَ رقمٍ بفاصلةٍ ولا تقريبَ نصٍّ — والنصُّ بديلٌ إن غاب.
    _sum = ((d.get("tasiBean") or {}).get("tasiTodaysSummaryBean") or {}) \
        if isinstance(d.get("tasiBean"), dict) else {}
    px = _pos(_sum.get("indexPrice")) or _pos(d.get("tasiValue"))
    if px is None:
        return None
    out = {
        "symbol": "^TASI",
        "price": px,
        "change": (_num(_sum.get("netChange"))
                   if _sum.get("netChange") is not None
                   else _num(d.get("tasiNetChange"))),
        "change_pct": (_num(_sum.get("percentChange"))
                       if _sum.get("percentChange") is not None
                       else _num(d.get("tasiPercentageChange"))),
        "prev_close": _pos(_sum.get("previouseIndexPrice")),
        "open": _pos(_sum.get("openPrice")),
        "high": _pos(_sum.get("highPrice")),
        "low": _pos(_sum.get("lowPrice")),
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
    """صفُّ شركةٍ للاستعمال — حيّاً في الجلسة، وآخرَ إغلاقٍ خارجَها."""
    sym = re.search(r"\b(\d{4})\b", str(symbol or ""))
    if not sym:
        return {}
    rows, _live, _at = usable_rows()
    return rows.get(sym.group(1)) or {}
