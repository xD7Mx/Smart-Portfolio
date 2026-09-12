"""متصفّحٌ لمهمّةٍ واحدة — آخرُ الوسائل لا أوّلُها (D265).

## لماذا

قِيس أن أربعةَ مصادرَ نحتاجها **مرسومةٌ بجافاسكربت** ولا يبلغها انتحالُ
بصمةِ TLS مهما بلغ (‏200 وصفرُ صفوف): كبارُ المساهمين، وصفقاتُهم،
والملكيةُ الأجنبية، وتقديراتُ المحلّلين. وانتحالُ البصمة يعبر الحمايةَ
ولا **ينفّذ سكربتاً** — هذا حدُّه الطبيعيّ، وقد بلغناه.

فالمتصفّحُ هو الوسيلةُ الباقية. وهو ثقيلٌ وخطِر، فيُقيَّد:

  ١· **لا يعمل إلا مجدولاً أو بطلبٍ صريح** — لا في مسار طلبِ مستخدم.
  ٢· **مهلةٌ قصوى** لكلّ صفحة، ويُغلَق بعد كلّ مهمّةٍ حتماً (‏finally).
  ٣· **صفحةٌ واحدةٌ في كلّ مرّة** — لا تصفّحٌ متوازٍ يلتهم الذاكرة.
  ٤· **غيابُه ليس عطباً**: إن لم يُركَّب المتصفّحُ تُعاد رسالةُ تعذُّرٍ
     صريحة، ويقول التطبيقُ «غير متوفّر» — ولا ينكسر شيء.

وهذه البياناتُ **بطيئةُ التغيّر** (أسبوعيةٌ أو شهرية)، فلا تُقرأ إلا
نادراً ولشركاتٍ محدودة — لا للسوق كلِّه كلَّ يوم.
"""
from __future__ import annotations

import asyncio

from loguru import logger

NAV_TIMEOUT_MS = 25_000
SETTLE_MS = 2_500
MAX_PAGES_PER_RUN = 40        # سقفٌ صلبٌ لكلّ تشغيلة


class BrowserUnavailable(RuntimeError):
    """المتصفّحُ غيرُ مركَّب — حالةٌ معلَنةٌ لا انهيار."""


def _launch_kwargs() -> dict:
    """كروميومُ الصورة نفسُه — لا نسخةٌ ثانيةٌ تُنزَّل (D269).

    الصورةُ تحمل `chromium` من apt أصلاً (يطبع تقريرَ صقر PDF). ولو تُركت
    بلاي‌رايت تُنزّل متصفّحَها لصار في الصورة **متصفّحان** لمعنًى واحد:
    زيادةٌ قرابةَ 400MB، ونسختان تشيخان على حِدَة، وعطبٌ يظهر في إحداهما
    دون الأخرى. فيُمرَّر مسارُ الموجود، ويبقى تنزيلُ بلاي‌رايت مطفأً.
    وإن غاب المسارُ تُترك بلاي‌رايت تختار — وغيابُهما معاً `BrowserUnavailable`.
    """
    kw: dict = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    try:
        from app.services.saqr_report import chrome_path
        p = chrome_path()
    except Exception:                                             # noqa: BLE001
        p = None
    if p:
        kw["executable_path"] = p
    return kw


async def render(urls: list[str], *, wait_selector: str | None = None,
                 settle_ms: int = SETTLE_MS) -> dict[str, str]:
    """يفتح الصفحاتِ واحدةً واحدةً ويعيد HTML بعد تنفيذ سكربتها.

    يرفع `BrowserUnavailable` إن لم تكن المكتبةُ/المتصفّحُ مركَّباً — ولا
    يُبتلع ذلك: الفرقُ بين «لا متصفّح» و«لا بيانات» فرقٌ جوهريّ في
    التشخيص، وقد كلّفنا خلطُه جولاتٍ قبلاً.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as e:                                        # noqa: BLE001
        raise BrowserUnavailable(f"playwright غير مركَّبة: {type(e).__name__}") from e

    urls = list(urls)[:MAX_PAGES_PER_RUN]
    out: dict[str, str] = {}
    pw = browser = None
    try:
        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.launch(**_launch_kwargs())
        except Exception as e:                                    # noqa: BLE001
            raise BrowserUnavailable(f"تعذّر تشغيل كروميوم: {e}") from e
        ctx = await browser.new_context(
            locale="ar-SA",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"))
        for u in urls:
            page = await ctx.new_page()
            try:
                await page.goto(u, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector,
                                                     timeout=NAV_TIMEOUT_MS)
                    except Exception:                             # noqa: BLE001
                        pass          # المهلةُ ليست فشلاً: تُقرأ الصفحةُ كما هي
                await page.wait_for_timeout(settle_ms)
                out[u] = await page.content()
            except Exception as e:                                # noqa: BLE001
                logger.debug("browser {}: {}: {}", u[:60], type(e).__name__, e)
            finally:
                try:
                    await page.close()
                except Exception:                                 # noqa: BLE001
                    pass
        return out
    finally:
        # الإغلاقُ حتميٌّ: عمليةُ كروميوم باقيةٌ تلتهم الذاكرةَ بصمت.
        for closer in (getattr(browser, "close", None), getattr(pw, "stop", None)):
            if closer:
                try:
                    await closer()
                except Exception:                                 # noqa: BLE001
                    pass


async def available() -> tuple[bool, str]:
    """(أمتاحٌ المتصفّح؟، السبب) — للمسبار وللتشخيص، بلا فتح صفحة."""
    try:
        from playwright.async_api import async_playwright
    except Exception as e:                                        # noqa: BLE001
        return False, f"playwright غير مركَّبة ({type(e).__name__})"
    pw = None
    try:
        pw = await async_playwright().start()
        b = await pw.chromium.launch(**_launch_kwargs())
        await b.close()
        return True, "متاح"
    except Exception as e:                                        # noqa: BLE001
        return False, f"كروميوم غير متاح: {str(e)[:90]}"
    finally:
        if pw:
            try:
                await pw.stop()
            except Exception:                                     # noqa: BLE001
                pass


def _sync_guard() -> None:
    """لا يُستدعى المتصفّحُ من مسار طلبٍ متزامن — قيدٌ يُذكَر ليُحترَم."""
    if asyncio.get_event_loop().is_running():
        return
