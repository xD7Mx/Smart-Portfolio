#!/usr/bin/env python3
"""هل يُجلب نصُّ الإعلان كاملاً داخل التطبيق؟ (قياسٌ قبل التنفيذ) — قارئٌ فقط.

طلب المالك: إلغاءُ زرّ «المصدر» وعرضُ محتواه كاملاً في نافذة الإعلان.
فيُقاس: من أين تأتي روابطُ الإعلانات، وهل تُقرأ صفحاتُها بالطريقة الذكية،
وهل يُستخرج منها المتنُ لا القوائمُ والتذييل.

    docker exec sp_backend python /app/scripts/audit/announcement_body_door.py
"""
import asyncio, collections, json, re, sys
from urllib.parse import urlparse
sys.path.insert(0, "/app")


def body_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)[:0]
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        t.decompose()
    best = ""
    for sel in ("article", "[itemprop=articleBody]", ".article-body", ".articleDetails", ".news-detail",
                "#articledetails", ".article-content", ".text-content", "main"):
        for el in s.select(sel):
            t = " ".join(p.get_text(" ", strip=True) for p in el.find_all(["p", "li", "td"])) or el.get_text(" ", strip=True)
            if len(t) > len(best):
                best = t
    return best


async def main():
    try:
        from app.api.v1.endpoints.market import get_company_events, get_market_events
    except Exception as e:
        try:
            from app.api.v1.endpoints.market import get_company_events
            get_market_events = None
        except Exception:
            print(f"⚠ بيئةٌ ناقصة ({e}) — لم يُقَس"); return 0
    from app.services.tadawul_http import smart_fetch
    items = []
    for sym in ("4001", "2080", "2222", "1120"):
        r = await get_company_events(sym, "")
        body = r if isinstance(r, dict) else json.loads(getattr(r, "body", b"{}"))
        d = body.get("data") or []
        if isinstance(d, dict):
            d = d.get("events") or d.get("items") or []
        items += [x for x in d if isinstance(x, dict)]
    hosts = collections.Counter(urlparse(x.get("url") or "").hostname or "—" for x in items)
    print(f"إعلانات: {len(items)} · بمعرّف تفاصيل: {sum(1 for x in items if x.get('detail_id'))} · المضيفات: {dict(hosts)}")
    seen = set()
    for x in items:
        u = x.get("url")
        if not u or x.get("detail_id"):
            continue
        h = urlparse(u).hostname
        if h in seen:
            continue
        seen.add(h)
        print(f"\n— {h}: {(x.get('title') or x.get('headline') or '')[:70]}\n  {u[:140]}")
        for label, warm in (("ذكيّ", f"https://{h}/"),):
            try:
                st, html = await smart_fetch(u, warm=warm, timeout=25)
            except Exception as e:
                print(f"  {label}: خطأ {type(e).__name__}"); continue
            t = body_text(html or "")
            title = (x.get("title") or "")[:25]
            print(f"  {label}: HTTP {st} · {len(html or '')} حرف · متن {len(t)} حرف · العنوانُ في الصفحة: {bool(title and title[:15] in (html or ''))}")
            print(f"  أوّل المتن: {t[:260]}")
    return 0

sys.exit(asyncio.run(main()))
