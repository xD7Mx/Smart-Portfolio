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
                    timeout: int) -> tuple[int, str]:
    from curl_cffi import requests as cr
    with cr.Session(impersonate=_IMPERSONATE) as s:
        # التسخينُ يجمع كوكيزَ الحماية قبل طلب البيانات — يُحاوَل ويُتجاوَز.
        try:
            s.get(HOME, timeout=timeout)
        except Exception:                                         # noqa: BLE001
            pass
        headers = {"Referer": referer} if referer else None
        r = s.get(url, params=params, headers=headers, timeout=timeout)
        return r.status_code, r.text or ""


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
