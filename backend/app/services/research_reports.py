"""تقاريرُ الجهات المرخّصة لسوق «تاسي» — لتبويب «التوقعات» (D662).

قال المالك: «أريد تقاريرَ للجهات المعتمدة من بنوكٍ وغيرها لسوق تاسي — حالياً خالية، ولا أريد شيئاً خالياً».
وقِيس قبل البناء (`research_sources_door.py` ثمّ `research_shape_door.py`) خمسَ عشرةَ جهة:

  • الجزيرة كابيتال — صفحةُ «أبحاث وتقارير» جداولُ في HTML نفسِه (سوق · اسم البحث · تاريخ التقرير · ملفّ)،
    ‏1072 ملفّاً: مذكّراتُ نتائج الشركات، والقطاعات، والاقتصاد، والتحليلُ الفنيّ، واليوميُّ والشهريّ.
    والتاريخُ في الجدول شهرٌ-يومٌ-سنة (‏«03-07-2024» لملفّ daily-07-03-2024 = ‏7 مارس).
  • جدوى للاستثمار — «التقارير الاقتصادية» بطاقاتٌ: عنوانٌ · `<time datetime>` · نوعٌ · ملفّ.
  • الراجحي المالية — قائمةُ البحوث من نداء GraphQL ‏«SearchAndReports» الذي تطلبه صفحةُ «البحوث» نفسُها (‏D733).
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

# الصنفُ من اسم الملفّ والعنوان — والأخصُّ أوّلاً
_KINDS = (
    ("توقعات النتائج", re.compile(r"earnings-forecast|توقعات النتائج", re.I)),
    ("تحليل فنيّ", re.compile(r"technical|فني", re.I)),
    ("تقرير قطاعيّ", re.compile(r"sector|banking-report|قطاع|المصارف|البنوك", re.I)),
    ("تقرير اقتصاديّ", re.compile(r"econom|macro|gdp|budget|inflation|chartbook|اقتصاد|الميزانية|التضخم|الناتج", re.I)),
    ("تقرير شركة", re.compile(r"flash-note|earnings|initiat|result|company|نتائج|مذكرة|تغطية", re.I)),
    ("تقرير يوميّ", re.compile(r"daily|يومي", re.I)),
    ("تقرير دوريّ", re.compile(r"monthly|weekly|quarter|review|msci|شهري|أسبوعي|ربع", re.I)),
)


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
            sym = next((v for kk, v in row.items() if "رمز" in kk and re.fullmatch(r"\d{4}", v or "")), None)
            k = by_head if (by_head and (sym or by_head != "تقرير شركة")) else kind_of(href.rsplit("/", 1)[-1], title)
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




# ══ الراجحي المالية بعد تغيّر موقعها (‏D733 · المالك 2026-11-14) ══
# قِيس (arc_site_door · arc_graph_door): الصفحةُ صارت Next.js على Sitecore JSS؛ لا ‏data-parentId ولا ‏ListingAPI. والقائمةُ
# نداءٌ واحد: ‎POST /sitecore/api/graph/edge?sc_apikey=…‎ باستعلام GraphQL ‏«SearchAndReports» — ولكلّ بندٍ حقلان بروابط وسائط:
# ‏«DownloadLink» ملفُّ التقرير، و«icon» صورةُ «اشترك/حمّل» (‏arb-subscribe-report-download.png). وكان القارئُ القديمُ يأخذ أوّلَ
# رابطٍ ‎/-/media/‎ في شجرة البند فيلتقط الأيقونة — وهو ما رآه المالك: «تخرج صورةُ أيقونة المشاركة». فالرابطُ هنا حقلُ
# التحميل وحده، ويُقبل ملفَّ PDF وحده.
ARC_GRAPH = ARC + "/sitecore/api/graph/edge"
_GUID = r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
# جذرُ البحوث وقالبُ بندها كما قِيسا في استعلام الصفحة (2026-11-14) — احتياطٌ إن لم يُقرآ من سكربتها
ARC_ROOT_MEASURED = "{E771FC1D-B3C8-4BCD-B6E8-E57A753FC6B9}"
ARC_TEMPLATE_MEASURED = "{8B6A8870-0EA1-4C6E-9174-94A1FC91D1B0}"


def arc_discover(texts: list[str]) -> dict:
    """من الصفحة وسكربتاتها: مفتاحُ الواجهة العامّ (يُرسَل من متصفّح كلّ زائر — لا يُحفظ في الشيفرة)، وجذرُ البحوث وقالبُها."""
    out: dict = {}
    for t in texts:
        t = t or ""
        if "key" not in out:
            m = (re.search(r"sc_apikey=(" + _GUID + r")", t)
                 or re.search(r"(?:sc_apikey|apiKey|sitecoreApiKey|SITECORE_API_KEY)[\"'\s:=,]{1,6}\{?(" + _GUID + r")", t, re.I)
                 # قِيس (arc_key_door): ‏`o.sitecoreApiKey=n.env.SITECORE_API_KEY||"…"` في سكربت التطبيق
                 or re.search(r"sitecoreApiKey\s*=\s*[\w.]*SITECORE_API_KEY\s*\|\|\s*[\"'](" + _GUID + r")", t))
            if m:
                out["key"] = m.group(1)
        if "root" not in out:
            m = (re.search(r"_path\\?[\"']?\s*,\s*value\s*:\s*\\?[\"']?(\{" + _GUID + r"\})", t)
                 # قِيس: الاستعلامُ يأخذ الجذرَ من مصدر مكوّن «ResearchAndReports» في بيانات الصفحة
                 or re.search(r"\"componentName\"\s*:\s*\"ResearchAndReports\"[^{}]{0,200}?\"dataSource\"\s*:\s*\"(\{" + _GUID + r"\})", t))
            if m:
                out["root"] = m.group(1)
        if "template" not in out:
            m = re.search(r"_templates\\?[\"']?\s*,\s*value\s*:\s*\\?[\"']?(\{" + _GUID + r"\})", t)
            if m:
                out["template"] = m.group(1)
    return out


def arc_query(root: str, template: str, first: int = 50, after: str | None = None, lang: str = "ar") -> str:
    """استعلامُ الصفحة نفسُه (‏SearchAndReports) بحقول البند التي تُقرأ — والترتيبُ بالتاريخ تنازلياً."""
    aft = f' after:"{after}"' if after else ""
    return ("query SearchAndReports { search( where: { AND: [ { name: \"_language\", value:\"" + lang + "\" } "
            "{ name: \"_path\", value: \"" + root + "\", operator: CONTAINS }, "
            "{name: \"_templates\", value: \"" + template + "\",operator: EQ} ] } "
            f"first: {int(first)}{aft} orderBy: {{ name: \"Date\", direction: DESC }} ) "
            "{ total pageInfo { endCursor hasNext } results { id name "
            "title: field(name: \"title\") { ... on TextField { value } } "
            "Categories: field(name: \"Categories\") { ... on MultilistField{ targetItems{ fields{name,value} } } } "
            "Companies: field(name: \"Companies\") { ... on MultilistField{ targetItems{ fields{name,value} } } } "
            "Sectors: field(name: \"Sectors\") { ... on MultilistField{ targetItems{ fields{name,value} } } } "
            "Date: field(name: \"Date\") { ... on DateField { value: formattedDateValue(format: \"g\", offset: -180) } } "
            "DownloadPDFLink: field(name: \"DownloadLink\") { ... on LinkField { jsonValue } } } } }")


def _names(field) -> list[str]:
    out = []
    for ti in ((field or {}).get("targetItems") or []):
        v = next((f.get("value") for f in (ti.get("fields") or []) if str(f.get("value") or "").strip()), None)
        if v:
            out.append(str(v).strip())
    return out


def arc_graph_items(raw: str) -> tuple[list[dict], dict]:
    """ردُّ ‏SearchAndReports: لكلّ بندٍ عنوانُه وتاريخُه وصنفُه وشركتُه — ورابطُه **حقلُ التحميل** ملفَّ PDF، وإلّا يُترك البند."""
    try:
        data = json.loads(raw or "null")
        srch = data["data"]["search"]
    except Exception:                                             # noqa: BLE001
        return [], {}
    out: list[dict] = []
    for r in srch.get("results") or []:
        title = _txt(((r.get("title") or {}).get("value")) or "")
        link = (((((r.get("DownloadPDFLink") or {}).get("jsonValue") or {}).get("value")) or {}).get("href")) or ""
        link = _html.unescape(str(link)).strip()
        if not re.search(r"\.pdf$", link.split("?")[0], re.I):
            continue                                              # بلا ملفٍّ لا رابط — ولا أيقونةٌ مكانه
        day = _mdy((r.get("Date") or {}).get("value") or "")
        if not (title and day):
            continue
        cats, comps, secs = _names(r.get("Categories")), _names(r.get("Companies")), _names(r.get("Sectors"))
        cat = " ".join(cats)
        k = ("تقرير يوميّ" if re.search(r"daily", cat, re.I) else
             "تقرير شركة" if comps else
             "تقرير قطاعيّ" if secs else kind_of(cat, link, title))
        sym = None
        if k == "تقرير شركة":
            sym = next((x for x in (_company(c) for c in comps) if x), None) or _company(title)
        url = link if link.startswith("http") else ARC + "/" + link.lstrip("/")
        shown = title if not comps or any(c in title for c in comps) else f"{comps[0]} — {title}"
        out.append({"title": shown, "kind": k, "url": url, "date": day, "company": sym, "source": "الراجحي المالية"})
    return out, (srch.get("pageInfo") or {})


async def _arc() -> list[dict]:
    """قائمةُ بحوث الراجحي المالية من نداء صفحتها (‏D733): المفتاحُ والجذرُ من الصفحة وسكربتاتها، ثمّ صفحاتُ القائمة
    خمسين خمسين حتى تجاوز السنة."""
    from datetime import date as _d, timedelta as _td
    from app.services.tadawul_http import smart_flow
    floor = (_d.today() - _td(days=WINDOW_DAYS)).isoformat()

    def plan():
        st, page = yield {"url": ARC_PAGE, "timeout": 40}
        if st != 200:
            return []
        texts = [page]
        disc = arc_discover(texts)
        srcs = re.findall(r"<script[^>]+src=[\"'](/_next/static/[^\"']+\.js)[\"']", page or "")
        # سكربتاتُ الصفحة الخاصّةُ أوّلاً (التطبيقُ وصفحةُ المسار) — ثمّ البقيّة حتى يُعرف المفتاحُ والاستعلام
        srcs.sort(key=lambda u: 0 if re.search(r"_app|path|pages/", u) else 1)
        for src in srcs[:16]:
            if {"key", "root", "template"} <= disc.keys():
                break
            st2, js = yield {"url": ARC + src, "referer": ARC_PAGE, "timeout": 30}
            if st2 == 200:
                disc = {**arc_discover([js]), **disc}
        key = disc.get("key")
        if not key:
            logger.warning("الراجحي المالية: مفتاحُ واجهة البحوث لم يُقرأ من الصفحة ولا سكربتاتها")
            return []
        root, tpl = disc.get("root") or ARC_ROOT_MEASURED, disc.get("template") or ARC_TEMPLATE_MEASURED
        out: list[dict] = []
        after = None
        for _ in range(12):
            st3, raw = yield {"url": ARC_GRAPH, "method": "POST", "params": {"sc_apikey": key}, "referer": ARC_PAGE,
                              "data": json.dumps({"query": arc_query(root, tpl, 50, after)}),
                              "headers": {"Content-Type": "application/json", "Accept": "application/json"}}
            if st3 != 200:
                break
            got, info = arc_graph_items(raw)
            out += got
            after = info.get("endCursor")
            oldest = min((x["date"] for x in got), default="")
            if not info.get("hasNext") or not after or (oldest and oldest < floor):
                break
        return out
    return await smart_flow(plan, warm=ARC + "/ar", timeout=40) or []


WINDOW_DAYS = 365      # ‏D664: «جميعُ التوقعات الممكنة» — كلُّ ما نشرته الجهاتُ في سنة، لا سقفٌ لكلّ صنف
DAILY_KEEP = 5         # واليوميُّ آخرُ خمسةٍ لكلّ جهة: تقريرُ كلِّ يومٍ يُغرق ما سواه ولا يزيد معنًى


def select(items: list[dict], today: str | None = None) -> list[dict]:
    """الأحدثُ أوّلاً بلا تكرارٍ للملفّ نفسِه — كلُّ ما في السنة، واليوميُّ آخرُ خمسةٍ لكلّ جهة."""
    from datetime import date as _d, timedelta as _td
    floor = ((_d.fromisoformat(today) if today else _d.today()) - _td(days=WINDOW_DAYS)).isoformat()
    seen, daily, out = set(), {}, []
    for it in sorted(items, key=lambda x: x.get("date") or "", reverse=True):
        key = it.get("id") or it.get("url") or it.get("title")
        if key in seen or (it.get("date") or "") < floor:
            continue
        seen.add(key)
        if it.get("kind") == "تقرير يوميّ":
            src = it.get("source")
            if daily.get(src, 0) >= DAILY_KEEP:
                continue
            daily[src] = daily.get(src, 0) + 1
        out.append(it)
    return out


def link_opinions(opinions: list[dict], reports: list[dict], days: int = 7) -> list[dict]:
    """رأيُ الجهة بلا ملفٍّ («أرقام» لا تنشر ملفَّ الراجحي المالية) يُربط بتقرير **الجهة نفسِها** عن **الشركة نفسِها** المنشور
    في موقعها خلال أسبوعٍ من تاريخ الرأي — الأقربُ تاريخاً (‏D733). وما لا تقريرَ له يبقى بلا رابط: لا يُختلق رابط."""
    from datetime import date as _d
    norm = lambda x: re.sub(r"\.SR$", "", str(x or "").strip())
    by: dict = {}
    for r in reports:
        if r.get("kind") == "تقرير شركة" and r.get("company") and r.get("url"):
            by.setdefault((str(r.get("source") or "").strip(), norm(r["company"])), []).append(r)
    for o in opinions:
        if o.get("url") or not o.get("company") or not o.get("date"):
            continue
        cands = by.get((str(o.get("source") or "").strip(), norm(o["company"])), [])
        try:
            od = _d.fromisoformat(o["date"])
            best = min(((abs((_d.fromisoformat(r["date"]) - od).days), r) for r in cands), key=lambda x: x[0], default=None)
        except ValueError:
            best = None
        if best and best[0] <= days:
            o["url"], o["report_title"] = best[1]["url"], best[1]["title"]
    return opinions


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
