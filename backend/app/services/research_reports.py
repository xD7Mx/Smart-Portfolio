"""تقاريرُ الجهات المرخّصة لسوق «تاسي» — لتبويب «التوقعات» (D662).

قال المالك: «أريد تقاريرَ للجهات المعتمدة من بنوكٍ وغيرها لسوق تاسي — حالياً خالية، ولا أريد شيئاً خالياً».
وقِيس قبل البناء (`research_sources_door.py` ثمّ `research_shape_door.py`) خمسَ عشرةَ جهة:

  • الجزيرة كابيتال — صفحةُ «أبحاث وتقارير» جداولُ في HTML نفسِه (سوق · اسم البحث · تاريخ التقرير · ملفّ)،
    ‏1072 ملفّاً: مذكّراتُ نتائج الشركات، والقطاعات، والاقتصاد، والتحليلُ الفنيّ، واليوميُّ والشهريّ.
    والتاريخُ في الجدول شهرٌ-يومٌ-سنة (‏«03-07-2024» لملفّ daily-07-03-2024 = ‏7 مارس).
  • جدوى للاستثمار — «التقارير الاقتصادية» بطاقاتٌ: عنوانٌ · `<time datetime>` · نوعٌ · ملفّ.
  • الراجحي المالية — قائمةُ البحوث من نداء `ListingAPI/GetResearchListing` المذكور في صفحة «البحوث» نفسِها.
  • الأهلي كابيتال: بوّابةُ أبحاثٍ بتسجيل دخول، والرياض المالية تُرسم بسكربت — فلا تُقرأ ولا يُدّعى أنها قُرئت.

كلُّ بندٍ بجهته وتاريخه ورابط ملفّه الأصليّ. لا يُلخَّص ما لم يُقرأ، ولا يُختلق عنوانٌ ولا تاريخ.
"""
from __future__ import annotations

import asyncio
import html as _html
import json
import re
from datetime import date

from loguru import logger

AJC = "https://www.aljaziracapital.com.sa"
AJC_PAGE = AJC + "/ar/insights/research-reports/"
JADWA = "https://www.jadwa.com"
JADWA_PAGES = (JADWA + "/ar/economic-reports", JADWA + "/ar/special-reports")
ARC = "https://www.alrajhi-capital.sa"
ARC_PAGE = ARC + "/research"
ARC_API = ARC + "/sitecore/api/ListingAPI/GetResearchListing"

# الصنفُ من اسم الملفّ والعنوان — والأخصُّ أوّلاً
_KINDS = (
    ("تحليل فنيّ", re.compile(r"technical|فني", re.I)),
    ("تقرير قطاعيّ", re.compile(r"sector|banking-report|قطاع|المصارف|البنوك", re.I)),
    ("تقرير اقتصاديّ", re.compile(r"econom|macro|gdp|budget|inflation|chartbook|اقتصاد|الميزانية|التضخم|الناتج", re.I)),
    ("تقرير شركة", re.compile(r"flash-note|earnings|initiat|result|company|نتائج|مذكرة|تغطية", re.I)),
    ("تقرير يوميّ", re.compile(r"daily|يومي", re.I)),
    ("تقرير دوريّ", re.compile(r"monthly|weekly|quarter|review|msci|شهري|أسبوعي|ربع", re.I)),
)
# سقفُ كلّ صنفٍ في التبويب: الأحدثُ أوّلاً، واليوميُّ لا يُغرق ما سواه
CAP = {"تقرير شركة": 30, "تقرير قطاعيّ": 10, "تقرير اقتصاديّ": 10, "تحليل فنيّ": 3,
       "تقرير دوريّ": 4, "تقرير يوميّ": 2, "تقرير": 6}


def _txt(h) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())


def kind_of(*parts: str) -> str:
    """الصنفُ من أوّل جزءٍ يدلّ: اسمُ الملفّ قبل العنوان — «التقرير اليوميّ والنظرةُ الفنية» ملفُّه daily فهو يوميّ."""
    for p in parts:
        for k, rx in _KINDS:
            if p and rx.search(p):
                return k
    return "تقرير"


def _mdy(s: str) -> str | None:
    """«03-07-2024» (شهرٌ-يومٌ-سنة كما ينشرها الجدول) ← 2024-03-07؛ وإن جاوز الأوّلُ اثني عشر فهو اليوم."""
    m = re.match(r"\s*(\d{1,2})[-/](\d{1,2})[-/](20\d\d)", s or "")
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    mo, d = (a, b) if a <= 12 else (b, a)
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def _company(title: str) -> str | None:
    """رمزُ الشركة من العنوان بمطابقةٍ واحدةٍ فقط — وإلا لا شيء (D296)."""
    try:
        from app.services.special_deals import _by_name
        head = re.split(r"\s[-–—:|]\s", title or "")[0]
        return _by_name([head, title])
    except Exception:                                             # noqa: BLE001
        return None


def _num(v) -> float | None:
    m = re.fullmatch(r"\s*(\d{1,6}(?:[.,]\d{1,3})?)\s*", str(v or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def ajc_items(page: str) -> list[dict]:
    """جداولُ «أبحاث وتقارير» الجزيرة كابيتال: لكلّ صفٍّ عنوانُه وتاريخُه وملفُّه.

    قِيس (research_reader_door): تسعةُ جداولَ رؤوسُها تدلّ على صنفها — «رمز الشركة» (ومعه «السعر العادل» في
    جدول التغطية) للشركات، و«قطاع» للقطاعات، و«دولة» للاقتصاد، و«سوق» للدوريّ واليوميّ. فالرمزُ من الجدول نفسِه
    لا من مطابقة الاسم، والسعرُ العادلُ ما كتبته الجهةُ في صفّها — لا يُحسب ولا يُقدَّر."""
    out: list[dict] = []
    for t in re.finditer(r"<table\b.*?</table>", page or "", re.S | re.I):
        tb = t.group(0)
        heads = [_txt(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", tb, re.S | re.I)]
        if not any("البحث" in h for h in heads):
            continue
        by_head = ("تقرير شركة" if any("رمز" in h for h in heads) else
                   "تقرير قطاعيّ" if any(h == "قطاع" for h in heads) else
                   "تقرير اقتصاديّ" if any(h == "دولة" for h in heads) else None)
        for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tb, re.S | re.I):
            tds = re.findall(r"<td\b[^>]*>(.*?)</td>", tr, re.S | re.I)
            f = re.search(r'href=["\']([^"\']+\.pdf)["\']', tr, re.I)
            if not tds or not f:
                continue
            row = dict(zip(heads, (_txt(x) for x in tds)))
            title = next((v for k, v in row.items() if "البحث" in k), "")
            day = next((_mdy(v) for k, v in row.items() if "تاريخ" in k), None)
            href = f.group(1)
            url = href if href.startswith("http") else AJC + href
            if not title or not day:
                continue
            k = by_head or kind_of(href.rsplit("/", 1)[-1], title)
            sym = next((v for kk, v in row.items() if "رمز" in kk and re.fullmatch(r"\d{4}", v or "")), None)
            fair = next((_num(v) for kk, v in row.items() if "العادل" in kk or "مستهدف" in kk), None)
            it = {"title": title, "kind": k, "url": url, "date": day,
                  "company": sym or (_company(title) if k == "تقرير شركة" else None),
                  "source": "الجزيرة كابيتال"}
            if fair:
                it["fair_value"] = fair
            out.append(it)
    return out


def jadwa_items(page: str) -> list[dict]:
    """بطاقاتُ «التقارير الاقتصادية» لجدوى: عنوانٌ وتاريخٌ ونوعٌ وملفّ."""
    out: list[dict] = []
    for m in re.finditer(r'<div class="report-item">(.*?)(?=<div class="report-item">|$)', page or "", re.S):
        blk = m.group(1)
        t = re.search(r"<h2[^>]*>(.*?)</h2>", blk, re.S)
        d = re.search(r'<time datetime="(20\d\d-\d\d-\d\d)', blk)
        f = re.search(r'href="([^"]+\.pdf)"', blk, re.I)
        if not (t and d and f):
            continue
        spans = [_txt(x) for x in re.findall(r'<span class="date">(.*?)</span>', blk, re.S)]
        typ = next((x for x in spans if x and not re.match(r"20\d\d-", x)), "")
        href = f.group(1)
        out.append({"title": _txt(t.group(1)), "kind": "تقرير اقتصاديّ", "type": typ or None,
                    "url": href if href.startswith("http") else JADWA + href, "date": d.group(1),
                    "company": None, "source": "جدوى للاستثمار"})
    return out


def arc_params(page: str) -> list[dict]:
    """معاملاتُ نداء قائمة البحوث من صفحة «البحوث» نفسِها — لا تُحفظ في الشيفرة (FETCH_METHOD §٢).

    قِيس: المعرِّفُ في `data-parentId` واللغةُ في `data-lang` على نموذج البحث. والمرشِّحاتُ الفارغةُ تُجرَّب
    بصورتيها (فارغةً ثمّ «0» كما يكتب سكربتُ الصفحة للتاريخ) — والردُّ يحكم أيُّهما يُقبل."""
    pid = re.search(r"data-parentId=[\"']([^\"']{6,80})[\"']", page or "", re.I) or \
        re.search(r"parentId\s*[=:]\s*['\"]([^'\"]{6,80})['\"]", page or "")
    if not pid:
        return []
    lang = re.search(r"data-lang=[\"']([a-zA-Z-]{2,8})[\"']", page or "")
    size = re.search(r'data-pagesize=["\']?(\d{1,3})', page or "", re.I)
    base = {"pageNo": 1, "pageSize": int(size.group(1)) if size else 12, "date": "0", "keyword": "",
            "culture": lang.group(1) if lang else "ar", "parentId": pid.group(1)}
    return [{**base, "category": "", "sector": "", "company": ""},
            {**base, "category": "0", "sector": "0", "company": "0"}]


def arc_items(raw: str) -> list[dict]:
    """ردُّ قائمة البحوث: كلُّ كائنٍ فيه عنوانٌ وتاريخٌ ورابطُ ملفّ — والمفاتيحُ تُقرأ بمعناها لا بأسمائها المفترَضة."""
    try:
        data = json.loads(raw or "null")
    except Exception:                                             # noqa: BLE001
        return []
    out: list[dict] = []

    def walk(x):
        if isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            low = {str(k).lower(): v for k, v in x.items()}
            title = next((v for k, v in low.items() if k in ("title", "name", "displayname", "researchtitle") and isinstance(v, str)), None)
            link = next((v for k, v in low.items() if isinstance(v, str) and re.search(r"\.pdf|/ResearchListing/|/-/media/", v, re.I)), None)
            when = next((v for k, v in low.items() if "date" in k and isinstance(v, str) and re.search(r"20\d\d", v)), None)
            if title and link and when:
                d = re.search(r"(20\d\d)-(\d\d)-(\d\d)", when)
                day = f"{d.group(1)}-{d.group(2)}-{d.group(3)}" if d else _mdy(when)
                if day:
                    cat = next((v for k, v in low.items() if k in ("category", "categoryname", "type") and isinstance(v, str)), "")
                    out.append({"title": _txt(title), "kind": kind_of(cat, link, title),
                                "url": link if link.startswith("http") else ARC + link, "date": day,
                                "company": None, "source": "الراجحي المالية"})
                    return
            for v in x.values():
                walk(v)
    walk(data)
    for it in out:
        if it["kind"] == "تقرير شركة":
            it["company"] = _company(it["title"])
    return out


async def _ajc() -> list[dict]:
    from app.services.tadawul_http import smart_fetch
    st, body = await smart_fetch(AJC_PAGE, warm=AJC + "/ar", referer=AJC + "/ar", timeout=45)
    return ajc_items(body) if st == 200 else []


async def _jadwa() -> list[dict]:
    from app.services.tadawul_http import smart_fetch
    out: list[dict] = []
    for u in JADWA_PAGES:
        st, body = await smart_fetch(u, warm=JADWA + "/ar", referer=JADWA + "/ar", timeout=40)
        if st == 200:
            out += jadwa_items(body)
    return out


async def _arc() -> list[dict]:
    from app.services.tadawul_http import smart_flow

    def plan():
        st, page = yield {"url": ARC_PAGE, "timeout": 40}
        for p in (arc_params(page) if st == 200 else []):
            st2, raw = yield {"url": ARC_API, "params": p, "referer": ARC_PAGE,
                              "headers": {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*"}}
            got = arc_items(raw) if st2 == 200 else []
            if got:
                return got
        return []
    return await smart_flow(plan, warm=ARC + "/ar", timeout=40) or []


def select(items: list[dict]) -> list[dict]:
    """الأحدثُ أوّلاً بلا تكرارٍ للملفّ نفسِه، ولكلّ صنفٍ سقفُه."""
    seen, per, out = set(), {}, []
    for it in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        key = it.get("url") or it.get("title")
        if key in seen:
            continue
        seen.add(key)
        k = it.get("kind") or "تقرير"
        if per.get(k, 0) >= CAP.get(k, 6):
            continue
        per[k] = per.get(k, 0) + 1
        out.append(it)
    return out


async def collect() -> list[dict]:
    """كلُّ الجهات معاً — وتعذُّرُ جهةٍ لا يُسقط غيرَها، ويُقال في السجلّ."""
    res = await asyncio.gather(_ajc(), _jadwa(), _arc(), return_exceptions=True)
    items: list[dict] = []
    for name, r in zip(("الجزيرة كابيتال", "جدوى", "الراجحي المالية"), res):
        if isinstance(r, Exception):
            logger.warning(f"تقاريرُ الجهات/{name}: {type(r).__name__}: {r}")
            continue
        logger.info(f"تقاريرُ الجهات/{name}: {len(r)}")
        items += r
    return select(items)
