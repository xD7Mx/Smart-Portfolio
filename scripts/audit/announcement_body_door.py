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
            H = html or ""
            for pat in (r"<title>(.*?)</title>", r'property="og:title" content="([^"]*)"', r'property="og:description" content="([^"]*)"',
                        r'"articleBody"\s*:\s*"(.{0,200})', r"(اشترك|الاشتراك|مشتركين|subscribe|premium|paywall)", r"(__NEXT_DATA__|window\.__INITIAL|ng-app|data-reactroot)",
                        r"(captcha|cf-chl|Just a moment|Access Denied)"):
                m = re.search(pat, H, re.S | re.I)
                print(f"  [{pat[:28]}] → {(m.group(1)[:200] if m else '—')!r}")
            import html as _h
            lds = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', H, re.S)
            body = ""
            for blk in lds:
                try:
                    j = json.loads(blk)
                except Exception:
                    continue
                for o in (j if isinstance(j, list) else [j]):
                    if isinstance(o, dict) and o.get("articleBody"):
                        body = o["articleBody"]
                        print(f"  ld+json: @type={o.get('@type')} · isAccessibleForFree={o.get('isAccessibleForFree')} · hasPart={str(o.get('hasPart'))[:120]}")
            plain = re.sub(r"<[^>]+>", " ", _h.unescape(body))
            plain = re.sub(r"\s+", " ", plain).strip()
            print(f"  طولُ المتن المنشور: {len(plain)} حرف · أوّله: {plain[:300]}")
            outside = re.sub(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', "", H, flags=re.S)
            probe = plain[40:90]
            print(f"  المتنُ ظاهرٌ خارج البيانات المنظّمة: {bool(probe and probe in re.sub(r'<[^>]+>', ' ', _h.unescape(outside)).replace(chr(10),' '))}")
            for mk in ("argaamplus", "Argaam Plus", "أرقام بلس", "للمشتركين", "premium", "paywall", "lock", "subscriber"):
                print(f"  علامة «{mk}»: {len(re.findall(re.escape(mk), outside, re.I))}")
            m = re.search(r'"articleBody"\s*:\s*"(.*?)"\s*,\s*"', H, re.S)
            raw = _h.unescape(m.group(1)) if m else ""
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()
            print(f"  articleBody (بالتعبير): {len(txt)} حرف · أوّله: {txt[:240]}")
            print(f"  آخرُه: {txt[-200:]}")
            try:
                from app.services.browser_fetch import render
                R = await render([u], settle_ms=6000)
                page = R.get(u) or ""
                vis = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)))
                snip = txt[60:110]
                print(f"  المتصفّح: {len(page)} حرف · مقطعٌ من المتن ظاهرٌ للزائر: {bool(snip and snip in vis)} · مقطعُ آخره ظاهر: {bool(txt[-60:-10] in vis) if txt else False}")
                for mk in ("اشترك", "سجّل الدخول", "سجل الدخول", "للمشتركين", "أرقام بلس", "Argaam Plus", "لقراءة المقال"):
                    if mk in vis:
                        i = vis.find(mk); print(f"  «{mk}» ظاهرٌ: …{vis[max(0,i-80):i+80]}…")
            except Exception as e:
                print(f"  المتصفّح: {type(e).__name__}: {str(e)[:120]}")
            ids = re.findall(r"1936139", H)
            print(f"  ذِكرُ رقم المقال في الصفحة: {len(ids)} مرّة")
            i = H.find("1936139")
            print(f"  حولَ أوّل ذِكر: {H[max(0,i-200):i+300]!r}" if i >= 0 else "")
    return 0

sys.exit(asyncio.run(main()))
