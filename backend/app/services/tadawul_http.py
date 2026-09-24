"""جلبٌ يعبر حمايةَ «تداول» بنفسه — استقلالُ المصدر (D250).

## لماذا

قال المالك: «أريد التطبيق أن يكون ذاتياً بلا حاجةٍ للمستخدم للاستدامة
الاستثمارية الموثوقة». وكان الحدُّ المكتوبُ في ثلاثة ملفّاتٍ أن «تداول»
تردّ ‎403 على بياناتِ السوق — فبُني بديلٌ من «أرقام» للدليل، وبقي
المعدَّلُ الخالي من المخاطر بلا مصدرٍ أصلاً، وكُتب في المسبار أنه «يُملأ
يدوياً»: أي أن الاستدامةَ كانت معلَّقةً على يدِ المالك.

## ما تبيّن بالقياس

الحجبُ لم يكن بالرؤوس — رؤوسُنا كاملةٌ منذ البداية والجلسةُ مسخَّنة —
بل **ببصمة TLS**: حمايةُ Akamai تُميّز مُصافحةَ مكتبةٍ برمجيةٍ من مصافحة
كروم. فبانتحال بصمة كروم (`curl_cffi`) ردّت الصفحاتُ الأربعُ المحجوبةُ
‎200 كاملةً: مراقبةُ السوق الرئيسة، ودليلُ المُصدرين، وسوقُ الصكوك.

## القاعدة هنا

هذا الملفُّ **مَعبرٌ واحد**: من أراد صفحةَ «تداول» يطلبها منه، فلا تتعدّد
الجلساتُ ولا تُكرَّر رؤوسٌ في كلّ ملفّ. ويسقط إلى `httpx` إن غابت المكتبةُ
(بيئةٌ قديمة) — فلا ينهار شيءٌ بغيابها، بل يعود الحجبُ وحدَه.
"""
from __future__ import annotations

import asyncio

from loguru import logger

ORIGIN = "https://www.saudiexchange.sa"
HOME = ORIGIN + "/wps/portal/saudiexchange/home"
_IMPERSONATE = "chrome"

_missing_logged = False


def _have_curl() -> bool:
    global _missing_logged
    try:
        import curl_cffi  # noqa: F401
        return True
    except Exception:                                             # noqa: BLE001
        if not _missing_logged:
            logger.warning("curl_cffi غائبة — جلبُ «تداول» يعود إلى httpx "
                           "(الحمايةُ ستردّ 403 على بيانات السوق)")
            _missing_logged = True
        return False


def _blocking_fetch(url: str, params: dict | None, referer: str | None,
                    timeout: int, warm: str | None = None,
                    method: str = "GET", data: dict | None = None,
                    headers: dict | None = None) -> tuple[int, str]:
    from curl_cffi import requests as cr
    with cr.Session(impersonate=_IMPERSONATE) as s:
        # التسخينُ يجمع كوكيزَ الحماية قبل طلب البيانات — يُحاوَل ويُتجاوَز.
        try:
            s.get(warm or HOME, timeout=timeout)
        except Exception:                                         # noqa: BLE001
            pass
        h = dict(headers or {})
        if referer:
            h["Referer"] = referer
        if method.upper() == "POST":
            r = s.post(url, params=params, data=data, headers=h or None,
                       timeout=timeout)
        else:
            r = s.get(url, params=params, headers=h or None, timeout=timeout)
        return r.status_code, r.text or ""


def _blocking_bytes(url: str, referer: str | None, timeout: int) -> tuple[int, bytes]:
    from curl_cffi import requests as cr
    with cr.Session(impersonate=_IMPERSONATE) as s:
        try:
            s.get(HOME, timeout=timeout)
        except Exception:                                         # noqa: BLE001
            pass
        r = s.get(url, headers={"Referer": referer} if referer else None, timeout=timeout)
        return r.status_code, r.content or b""


async def fetch_bytes(url: str, *, referer: str | None = None,
                      timeout: int = 90) -> tuple[int, bytes]:
    """ملفٌّ ثنائيٌّ من «تداول» (قوائمُ PDF) بالبصمة نفسِها — (الحالة، البايتات)."""
    return await asyncio.to_thread(_blocking_bytes, url, referer, timeout)


async def fetch(url: str, *, params: dict | None = None,
                referer: str | None = None, timeout: int = 45) -> tuple[int, str]:
    """صفحةُ «تداول» أو نقطةُ بياناتها — (الحالة، النصّ).

    يُشغَّل الجلبُ المتزامنُ في خيطٍ منفصل: `curl_cffi` تنتحل بصمةَ كروم
    على مستوى المصافحة، وذلك متزامنٌ بطبعه — فلا يُحبَس حلقةُ الحدث.
    """
    if _have_curl():
        try:
            return await asyncio.to_thread(_blocking_fetch, url, params, referer, timeout)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("انتحالُ الجلب تعذّر ({}: {}) — يُجرَّب httpx",
                           type(e).__name__, e)
    # ── السقوطُ إلى العميل القديم: يعمل على ما لا يُحجَب ──
    import httpx
    from app.services.tadawul_announcements import _HEADERS
    async with httpx.AsyncClient(timeout=timeout, headers=_HEADERS,
                                 follow_redirects=True) as c:
        try:
            await c.get(HOME)
        except Exception:                                         # noqa: BLE001
            pass
        r = await c.get(url, params=params,
                        headers={"Referer": referer} if referer else None)
        return r.status_code, r.text or ""

def _blocking_flow(plan, warm: str | None, timeout: int, client: str):
    """يُشغّل خطّةً متسلسلةً في **جلسةٍ واحدة** — كما يفعل المتصفّح.

    الخطّةُ مولِّدٌ متزامن: يُنتج مواصفةَ طلبٍ ويستقبل (الحالة، النصّ)،
    فيقرّر الطلبَ التالي من جواب السابق. والكوكيزُ والرمزُ المضادُّ للتحيّل
    تبقى بين الطلبات — وهذا هو الفرقُ بين قراءةِ صفحةٍ وقراءةِ موقع.
    """
    if client == "curl":
        from curl_cffi import requests as cr
        sess = cr.Session(impersonate=_IMPERSONATE)
    else:
        import httpx
        sess = httpx.Client(timeout=timeout, follow_redirects=True,
                            headers={"User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0.0.0 Safari/537.36"),
                                "Accept-Language": "ar,en;q=0.8"})
    with sess as s:
        if warm:
            try:
                s.get(warm, timeout=timeout) if client == "curl" else s.get(warm)
            except Exception:                                     # noqa: BLE001
                pass
        gen = plan()
        reply = None
        while True:
            try:
                spec = gen.send(reply)
            except StopIteration as stop:
                return stop.value
            h = dict(spec.get("headers") or {})
            if spec.get("referer"):
                h["Referer"] = spec["referer"]
            kw = {"params": spec.get("params"), "headers": h or None}
            if client == "curl":
                kw["timeout"] = spec.get("timeout", timeout)
            try:
                if str(spec.get("method", "GET")).upper() == "POST":
                    r = s.post(spec["url"], data=spec.get("data"), **kw)
                else:
                    r = s.get(spec["url"], **kw)
                reply = (r.status_code, r.text or "")
            except Exception as e:                                # noqa: BLE001
                # حالةُ صفرٍ تعني «لا جواب» — والخطّةُ تقرّر، ولا تُخفى.
                logger.debug("خطّةُ الجلب: {} على {}: {}",
                             type(e).__name__, spec.get("url"), e)
                reply = (0, "")


async def smart_flow(plan, *, warm: str | None = None, timeout: int = 45):
    """خطّةُ طلباتٍ في جلسةٍ واحدةٍ منتحِلة — وتُرجع ما تُرجعه الخطّة.

    ══ لماذا لا تكفي `smart_fetch` ══
    كلُّ نداءٍ بها جلسةٌ جديدة: تُجمَع كوكيزُ الحماية ثمّ تُرمى. فقراءةُ
    موقعٍ ينشر بياناته على مرحلتين (صفحةٌ تُقرأ منها النقطةُ ثمّ نداءٌ
    ثانٍ يحمل كوكيزَ الصفحة ورمزَها) كانت تفقد المرحلةَ الأولى قبل
    الثانية. والمصدرُ لا يُلام: هكذا يعمل المتصفّح، وهكذا يجب أن نعمل.
    """
    if _have_curl():
        try:
            return await asyncio.to_thread(_blocking_flow, plan, warm, timeout, "curl")
        except Exception as e:                                    # noqa: BLE001
            logger.warning("خطّةُ الجلب المنتحِلة تعذّرت ({}: {}) — تُجرَّب httpx",
                           type(e).__name__, e)
    return await asyncio.to_thread(_blocking_flow, plan, warm, timeout, "httpx")


async def smart_fetch(url: str, *, params: dict | None = None,
                      referer: str | None = None, warm: str | None = None,
                      timeout: int = 45, method: str = "GET",
                      data: dict | None = None,
                      headers: dict | None = None) -> tuple[int, str]:
    """الطريقةُ الذكيةُ لأيّ مضيفٍ لا لـ«تداول» وحدَها (D292).

    ══ الطريقةُ ملكُ التطبيق لا ملكُ مصدرٍ واحد ══
    قال المالك: «استخدم طريقةَ الجلب الذكية لأرقام». وكان انتحالُ البصمة
    محصوراً بـ«تداول»: `fetch()` تُسخّن صفحةَ تداول وتنتحل لها. وقارئُ
    «أرقام» كان يستعمل `httpx` عادياً — فيُحجَب أو يُردّ ناقصاً بلا سبب
    ظاهر، والطريقةُ التي تفتح البابَ موجودةٌ في البيت.

    فصارت عامّةً: يُمرَّر **مضيفُ التسخين** (`warm`) فتُجمَع كوكيزُ ذاك
    الموقع، ويبقى `fetch()` غلافاً لـ«تداول» كما هو — منتِجٌ واحدٌ
    للانتحال، لا نسخةٌ لكلّ مصدر.

    وتقبل `method` و`data` و`headers` لأن مصادرَ كثيرةً لا تُعطي صفوفَها
    لطلبٍ عاديّ: قِيس أن صفحةَ صفقات «أرقام» تعود ‎494 ألفَ حرفٍ **بصفرِ
    صفوف**، وأن المسارَ نفسَه يظهر في سكربتها نداءً — أي أن الصفوفَ تُطلب
    بطلبٍ ثانٍ (‏XHR) بمعاملاتٍ وترويسةٍ تقول إنه نداءُ جافاسكربت (D294).
    """
    if _have_curl():
        try:
            return await asyncio.to_thread(_blocking_fetch, url, params,
                                            referer, timeout, warm, method,
                                            data, headers)
        except Exception as e:                                    # noqa: BLE001
            logger.warning("الجلبُ الذكيُّ تعذّر ({}: {}) — يُجرَّب httpx",
                           type(e).__name__, e)
    import httpx
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                 headers={"User-Agent": (
                                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/124.0.0.0 Safari/537.36"),
                                     "Accept-Language": "ar,en;q=0.8"}) as c:
        if warm:
            try:
                await c.get(warm)
            except Exception:                                     # noqa: BLE001
                pass
        h = dict(headers or {})
        if referer:
            h["Referer"] = referer
        if method.upper() == "POST":
            r = await c.post(url, params=params, data=data, headers=h or None)
        else:
            r = await c.get(url, params=params, headers=h or None)
        return r.status_code, r.text or ""
