"""«التوقعات» — التبويبُ الثالث في مفكرة السوق (بأمر المالك · D507).

قال المالك: «توقعاتُ البنوك وتقاريرُ السوق… معلوماتٌ ذهبيةٌ للمستثمر من مصادر
موثوقةٍ ورسمية». وقِيس على الخادم (forecasts_door.py) قبل البناء:

  • صفحتا «أرقام» لتقديرات المحللين ومقالات الأبحاث (/ar/monitors/…) تنادي
    `subscription-page-lowest-package` — محتوًى للمشتركين، فلا تُقرأ ولا
    يُدّعى أنها قُرئت.
  • تقاريرُ «أرقام» القطاعية (/ar/sector/sector-report) عامّةٌ في HTML.
  • أخبارُ «أرقام» العامّة تنشر توقعاتِ بيوت الخبرة والبنوك: رفعُ سعرٍ مستهدف،
    توصية، توقعاتُ أرباح ربع — فتُلتقط بمعناها من عناوينها.

فالتبويبُ من هذين العامَّين، كلُّ بندٍ بمصدره ورابطه وتاريخه. ولا يُختلق شيء:
إن عادا فارغين قالت الواجهةُ «غير متوفّرة».
"""
from __future__ import annotations

import re

import httpx
from loguru import logger

from app.services import cache
from app.services.argaam_calendar import BASE, UA, _N_DATE, _N_ITEM, _news_dt, _txt, fetch_argaam_news

CACHE_KEY = "forecasts:v1"
TTL = 60 * 60
SECTOR_URL = BASE + "/ar/sector/sector-report"

# معنى «توقّع» في عنوان خبر: بيتُ خبرةٍ أو بنكٌ يقدّر، أو سعرٌ مستهدف، أو توصية.
_FORECAST = re.compile(
    r"توقع|تتوقع|يتوقع|توقعات|تقديرات|السعر المستهدف|سعر مستهدف|مستهدف|توصية|توصي|"
    r"ترفع|تخفض|تقرير|تقارير|نظرة مستقبلية|آفاق|المحللين|المحللون|بيوت الخبرة")
# ما يُستبعد: أخبارٌ عن «تقرير» إداريّ لا تحليليّ.
_NOT = re.compile(r"تقرير مجلس الإدارة|التقرير السنوي|تقرير الحوكمة|تقرير الاستدامة")


def _d(v) -> str | None:
    """تاريخٌ كنصّ YYYY-MM-DD — الخبرُ يحمله كائنَ datetime أو نصّاً."""
    if v is None:
        return None
    s = v.isoformat() if hasattr(v, "isoformat") else str(v)
    return s[:10] or None


def _kind(title: str) -> str:
    if re.search(r"مستهدف", title):
        return "سعرٌ مستهدف"
    if re.search(r"توصية|توصي", title):
        return "توصية"
    if re.search(r"توقع|تقديرات|المحللين|المحللون", title):
        return "توقعات"
    return "تقرير"


def pick_forecasts(news: list[dict]) -> list[dict]:
    """ينتقي من الأخبار ما معناه توقّعٌ أو تقريرٌ تحليليّ."""
    out = []
    for n in news or []:
        t = n.get("headline") or ""
        if not _FORECAST.search(t) or _NOT.search(t):
            continue
        out.append({"title": t, "kind": _kind(t), "url": n.get("url"),
                    "date": _d(n.get("published")),
                    "company": n.get("company"), "source": "أرقام"})
    return out


async def _sector_reports() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(SECTOR_URL)
        if r.status_code != 200:
            return []
        page = r.text
    except Exception as e:                                        # noqa: BLE001
        logger.warning(f"التوقعات/تقارير قطاعية: {e}")
        return []
    out, seen = [], set()
    for m in _N_ITEM.finditer(page):
        t = _txt(m.group(2))
        if not t or len(t) < 16 or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        dm = _N_DATE.search(page[max(0, m.start() - 400): m.end() + 400])
        out.append({"title": t, "kind": "تقرير قطاعيّ", "url": BASE + m.group(1),
                    "date": _d(_news_dt(dm)), "company": None,
                    "source": "أرقام · تقارير قطاعية"})
    return out[:15]


async def build() -> list[dict]:
    news = await fetch_argaam_news()
    items = pick_forecasts(news) + await _sector_reports()
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    if items:
        cache.set(CACHE_KEY, items, TTL)
    logger.info(f"🔭 التوقعات: {len(items)} بنداً.")
    return items


async def get() -> list[dict]:
    hit = cache.get(CACHE_KEY)
    if isinstance(hit, list):
        return hit
    return await build()
