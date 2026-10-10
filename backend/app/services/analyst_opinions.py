"""آراءُ بيوت الخبرة في شركات «تاسي»: التوصيةُ والسعرُ المستهدف وتقريرُ الجهة (D664).

قال المالك: «أريد جلبَ جميع التوقعات الممكنة من الجهات المعتبرة». وقِيس (`forecast_sources2_door.py` ·
`argaam_brokers_door.py` · `opinions_debug_door.py`):

  • «أرقام» تنشر لكلّ بيت خبرةٍ جدولاً عامّاً بآخر مئة رأيٍ له (`brokeropinions/3/{معرّف الجهة}`): التاريخ · الشركة
    (برابطها ومعرّفها) · التوصية السابقة · التوصية · السعر وقت التوصية · السعر المستهدف · التغيّر · ملفُّ التقرير حين
    يُنشر. قِيس 18 جهةً بـ856 رأياً في سنة: الرياض المالية · الراجحي المالية · الجزيرة كابيتال · الأهلي كابيتال ·
    بي إس إف كابيتال · جي آي بي كابيتال · المتحدة للأوراق المالية · الأول كابيتال · جي بي مورغان · سيكو ·
    غولدمان ساكس · أوبار كابيتال · أبوظبي الأول للأوراق المالية · الفامينا · سي أي كابيتال · يو بي إس · جيفريز · سديف.
  • ومعرّفاتُ الجهات لا تُحفظ في الشيفرة: تُكتشف من صفحات الشركات نفسِها (روابطُ `?brokerID=`) — عيّنةٌ تدور كلَّ
    ليلة والسوقُ كلُّه في أوّل جمع، وتُحفظ فتكبر القائمةُ ولا تنقص.
  • وصفحةُ «آراء الشركة» بلا جدولٍ في HTML، ومراقبُ «آراء المحللين» المجمَّع للمشتركين — فلا يُقرآن.

ويُجمع مجدولاً لا في طلب مستخدم، ويُحفظ. والجهةُ تُسمّى باسمها، و«أرقام» ناقلٌ يُذكر. ولا يُحسب رقمٌ: ما في
الصفّ يُنقل كما هو، والشركةُ من معرّفها في الرابط لا من مطابقة اسمها.
"""
from __future__ import annotations

import asyncio
import html as _html
import re
import time

from loguru import logger

A = "https://www.argaam.com"
BROKER = "/ar/analystestimates/brokeropinions/3/{bid}"
COMPANY = "/ar/company/companyoverview/marketid/3/companyid/{cid}"
STORE_KEY = "analyst_opinions:v1"
BROKERS_KEY = "analyst_opinions:brokers"
FLOWS = 4
SCAN = 60          # صفحاتُ شركاتٍ تُفحص كلَّ ليلةٍ لاكتشاف جهاتٍ جديدة (تدور على السوق في أسبوع)


def _txt(h) -> str:
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())


def _num(v) -> float | None:
    m = re.fullmatch(r"\s*\(?\s*(-?\d{1,6}(?:[.,]\d{1,4})?)\s*%?\s*\)?\s*", str(v or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _day(v) -> str | None:
    m = re.search(r"(20\d\d)[/-](\d{1,2})[/-](\d{1,2})", v or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def rows_of(page: str) -> list[dict]:
    """جدولُ آراء بيوت الخبرة: رؤوسُه تُسمّي أعمدتَه (لا ترتيبٌ مفترَض)، وصفٌّ بلا جهةٍ أو تاريخٍ أو توصيةٍ يُترك.
    ومعرّفُ الشركة من رابطها في الصفّ — هو ما يربطها برمزها في «تداول»."""
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
            cid = re.search(r"analystrecomendationopinionbycompany/3/(\d+)", tr)
            out.append({"date": day, "house": house, "rating": rating,
                        "prev": at(cells, "التوصية السابقة") or None,
                        "price": _num(at(cells, "السعر الحالي", "السعر وقت التوصية")),
                        "target": _num(at(cells, "السعر المستهدف")),
                        "pdf": pdf.group(1) if pdf else None,
                        "cid": cid.group(1) if cid else None,
                        "company_label": at(cells, "الشركة")})
    return out


def _scan_plan(cids: list[str], found: set):
    def gen():
        for cid in cids:
            st, body = yield {"url": A + COMPANY.format(cid=cid), "referer": A + "/ar", "timeout": 30}
            if st == 200:
                found.update(re.findall(r"brokerID=(\d+)", body or ""))
        return None
    return gen


def _broker_plan(bids: list[str], got: dict):
    def gen():
        for bid in bids:
            st, body = yield {"url": A + BROKER.format(bid=bid), "referer": A + "/ar", "timeout": 30}
            rs = rows_of(body) if st == 200 else []
            for r in rs:
                r["page"] = A + BROKER.format(bid=bid)
            got[bid] = rs
        return None
    return gen


async def refresh() -> dict:
    """تُكتشف الجهاتُ من صفحات الشركات، ثمّ يُقرأ جدولُ كلّ جهة، ويُوزَّع على الشركات برموزها — ويُحفظ."""
    from app.services import lastgood
    from app.services.argaam_ids import build, snapshot
    from app.services.tadawul_http import smart_flow
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    await build()
    ids = {str(k): str(v) for k, v in ((snapshot() or {}).get("ids") or {}).items()}
    main = sorted(str(s).replace(".SR", "") for s in main_market(MARKET_UNIVERSE))
    rev = {ids[s]: s for s in main if ids.get(s)}
    known = {k: v for k, v in (lastgood.load(BROKERS_KEY) or {}).items() if k.isdigit()}
    cids = [ids[s] for s in main if ids.get(s)]
    if known:                                                      # عيّنةٌ تدور: السوقُ كلُّه في أسبوع
        k = int(time.time() // 86400) % max(1, -(-len(cids) // SCAN))
        cids = cids[k * SCAN:(k + 1) * SCAN]
    t0 = time.time()
    found: set = set(known)
    await asyncio.gather(*(smart_flow(_scan_plan(cids[i::FLOWS], found), warm=A + "/ar", timeout=30)
                           for i in range(FLOWS) if cids[i::FLOWS]), return_exceptions=True)
    bids = sorted(found, key=int)
    got: dict = {}
    await asyncio.gather(*(smart_flow(_broker_plan(bids[i::FLOWS], got), warm=A + "/ar", timeout=30)
                           for i in range(FLOWS) if bids[i::FLOWS]), return_exceptions=True)
    by_sym: dict = {}
    names = dict(known)
    for bid, rs in got.items():
        for r in rs:
            names[bid] = r["house"]
            sym = rev.get(r.get("cid") or "")
            if sym:
                by_sym.setdefault(sym, []).append(r)
    n = sum(len(v) for v in by_sym.values())
    logger.info(f"آراءُ بيوت الخبرة: {len(bids)} جهةً · {len(by_sym)} شركةً · {n} رأياً · {time.time() - t0:.0f}ث")
    if names:
        lastgood.save(BROKERS_KEY, names)
    if by_sym:
        lastgood.save(STORE_KEY, {"rows": by_sym, "built_at": time.time()})
    return by_sym


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
                        "rating": r["rating"], "prev": r.get("prev"), "target": r.get("target"), "price": r.get("price"),
                        "has_pdf": bool(r.get("pdf"))})
    return out
