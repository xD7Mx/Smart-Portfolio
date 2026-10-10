"""آراءُ بيوت الخبرة في شركات «تاسي»: التوصيةُ والسعرُ المستهدف وتقريرُ الجهة (D664).

قال المالك: «أريد جلبَ جميع التوقعات الممكنة من الجهات المعتبرة». وقِيس (`forecast_sources2_door.py` ·
`argaam_brokers_door.py`):

  • «أرقام» تجمع آراءَ بيوت الخبرة في جدولٍ عامٍّ لكلّ شركة — التاريخ · شركة الأبحاث · التوصية السابقة · التوصية ·
    السعر · السعر المستهدف · التغيّر · ملفُّ التقرير (‏`argaamplus.s3…pdf` حين تنشره). قِيس لشركةٍ واحدة 94 صفّاً
    من الرياض المالية والجزيرة كابيتال وجي آي بي والمتحدة للأوراق المالية والأول كابيتال وغيرها، بلا قفل.
  • وصفحةُ مراقب «آراء المحللين» المجمَّعة للمشتركين — فلا تُقرأ.

فيُقرأ جدولُ كلّ شركةٍ من السوق الرئيسيّ برابطها في «أرقام» (`analystrecomendationopinionbycompany/3/{معرّف}`
— الرابطُ الذي تضعه «أرقام» نفسُها على اسم الشركة في جداول الوسطاء)، في جلساتٍ منتحِلةٍ قليلة، مجدولاً لا في
طلب مستخدم، ويُحفظ. والجهةُ تُسمّى باسمها، و«أرقام» ناقلٌ يُذكر. ولا يُحسب رقمٌ: ما في الصفّ يُنقل كما هو.
"""
from __future__ import annotations

import asyncio
import html as _html
import re
import time

from loguru import logger

A = "https://www.argaam.com"
PATH = "/ar/analystestimates/analystrecomendationopinionbycompany/3/{cid}"
STORE_KEY = "analyst_opinions:v1"
FLOWS = 4


def _txt(h) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())


def _num(v) -> float | None:
    m = re.fullmatch(r"\s*\(?\s*(-?\d{1,6}(?:[.,]\d{1,4})?)\s*%?\s*\)?\s*", str(v or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _day(v) -> str | None:
    m = re.search(r"(20\d\d)[/-](\d{1,2})[/-](\d{1,2})", v or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def rows_of(page: str) -> list[dict]:
    """جدولُ آراء بيوت الخبرة: رؤوسُه تُسمّي أعمدتَه (لا ترتيبٌ مفترَض)، وصفٌّ بلا جهةٍ أو تاريخٍ أو توصيةٍ يُترك."""
    out: list[dict] = []
    for t in re.finditer(r"<table\b.*?</table>", page or "", re.S | re.I):
        tb = t.group(0)
        heads = [_txt(h) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", tb, re.S | re.I)]
        if not (any("الأبحاث" in h for h in heads) and any("المستهدف" in h for h in heads)):
            continue
        col = {h: i for i, h in enumerate(heads)}

        def at(cells, *names):
            for n in names:
                for h, i in col.items():
                    if n == h or (n in h and not (n == "التوصية" and "السابقة" in h)):
                        return cells[i] if i < len(cells) else None
            return None
        for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tb, re.S | re.I):
            tds = re.findall(r"<td\b[^>]*>(.*?)</td>", tr, re.S | re.I)
            if len(tds) < 5:
                continue
            cells = [_txt(x) for x in tds]
            house = at(cells, "شركة الأبحاث")
            day = _day(at(cells, "التاريخ") or "")
            rating = at(cells, "التوصية")
            if not (house and day and rating):
                continue
            pdf = re.search(r'href="(https://argaamplus\.s3\.amazonaws\.com/[^"]+\.pdf)"', tr)
            out.append({"date": day, "house": house, "rating": rating,
                        "prev": at(cells, "التوصية السابقة") or None,
                        "price": _num(at(cells, "السعر الحالي", "السعر وقت التوصية")),
                        "target": _num(at(cells, "السعر المستهدف")),
                        "pdf": pdf.group(1) if pdf else None})
    return out


def _plan(pairs: list[tuple[str, str]], got: dict):
    def gen():
        for sym, cid in pairs:
            st, body = yield {"url": A + PATH.format(cid=cid), "referer": A + "/ar", "timeout": 30}
            rs = rows_of(body) if st == 200 else []
            if rs:
                for r in rs:
                    r["page"] = A + PATH.format(cid=cid)
                got[sym] = rs
        return None
    return gen


async def refresh() -> dict:
    """جداولُ السوق الرئيسيّ كلِّه في أربع جلساتٍ منتحِلة — وتُحفظ مع لحظة جمعها."""
    from app.services import lastgood
    from app.services.argaam_ids import build, snapshot
    from app.services.tadawul_http import smart_flow
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    await build()
    ids = (snapshot() or {}).get("ids") or {}
    syms = [str(s).replace(".SR", "") for s in main_market(MARKET_UNIVERSE)]
    pairs = [(s, str(ids[s])) for s in syms if ids.get(s)]
    got: dict = {}
    chunks = [pairs[i::FLOWS] for i in range(FLOWS)]
    t0 = time.time()
    await asyncio.gather(*(smart_flow(_plan(c, got), warm=A + "/ar", timeout=30) for c in chunks if c),
                         return_exceptions=True)
    n = sum(len(v) for v in got.values())
    logger.info(f"آراءُ بيوت الخبرة: {len(got)} شركةً · {n} رأياً من {len(pairs)} · {time.time() - t0:.0f}ث")
    if got:
        lastgood.save(STORE_KEY, {"rows": got, "built_at": time.time()})
    return got


def stored() -> dict:
    from app.services import lastgood
    return ((lastgood.load(STORE_KEY) or {}).get("rows")) or {}


def for_symbol(sym: str) -> list[dict]:
    return sorted(stored().get(str(sym), []), key=lambda r: r["date"], reverse=True)


def as_forecasts(store: dict | None = None) -> list[dict]:
    """كلُّ رأيٍ بندٌ في «التوقعات»: الجهةُ باسمها، والتوصيةُ والسعرُ المستهدفُ كما كتبتهما."""
    from app.data.market_universe import MARKET_UNIVERSE
    out: list[dict] = []
    for sym, rows in (store if store is not None else stored()).items():
        name = (MARKET_UNIVERSE.get(sym) or {}).get("name_ar") or sym
        for r in rows:
            moved = r.get("prev") and r["prev"] != r["rating"] and not re.search(r"بداية|إعادة", r["prev"] or "")
            title = f"{name}: {r['rating']}" + (f" (كانت {r['prev']})" if moved else "")
            out.append({"id": f"{sym}|{r['house']}|{r['date']}|{r['rating']}|{r.get('target')}",
                        "title": title, "kind": "توصية وسعرٌ مستهدف", "date": r["date"], "company": sym,
                        "url": r.get("pdf") or r.get("page"), "source": r["house"], "via": "أرقام",
                        "rating": r["rating"], "target": r.get("target"), "price": r.get("price"),
                        "has_pdf": bool(r.get("pdf"))})
    return out
