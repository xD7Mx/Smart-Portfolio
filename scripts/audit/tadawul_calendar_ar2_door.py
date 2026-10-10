#!/usr/bin/env python3
"""أحداثُ «تداول» في المفكرة بالعربية (D670) — قياسٌ ثانٍ قبل أيّ تعديل، قارئٌ فقط.

قِيس أوّلاً: قائمةُ المفكرة الرسمية (`getNewsListData`) تعود خمسةَ أخبارٍ للسوق والهيئة بلا رمز (حدودُ التذبذب، «إيداع»،
موافقاتُ طرح) لا إفصاحاتِ شركات — وروابطُها `news-detail-wcm` لا `issuer-announcements`، فلم يُعرَّب منها شيء.
فيُقاس هنا: ما في المخزن من مصدر «تداول»، وهل تحمل صفحةُ الخبر عنوانَه العربيّ، وما تُعطيه خدمةُ إفصاحات الشركات
(`getAnnouncementListData`) للسوق كلّه بلا رمز — وكم منها ليس في المفكرة أصلاً.
"""
import asyncio, collections, html, json, re, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
AR = re.compile(r"[؀-ۿ]")


def cands(h: str) -> list[str]:
    out = []
    for pat in (r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', r"<title[^>]*>(.*?)</title>",
                r"<h1[^>]*>(.*?)</h1>", r"<h2[^>]*>(.*?)</h2>", r"<h3[^>]*>(.*?)</h3>",
                r'class="[^"]*(?:title|Title|heading)[^"]*"[^>]*>(.*?)</'):
        for m in re.finditer(pat, h or "", re.S):
            t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).split())
            if 8 <= len(t) <= 300 and t not in out:
                out.append(t)
    return out


async def main():
    from app.services.content_engine import _cal_load_store
    store = _cal_load_store()
    by = collections.Counter(e.get("source") for e in store.values())
    td = [e for e in store.values() if e.get("source") == "تداول"]
    print(f"═ المخزن: {len(store)} · بالمصدر {by.most_common(6)}")
    print(f"   «تداول»: {len(td)} · برمز {sum(1 for e in td if e.get('symbol'))} · بعنوانٍ عربيّ "
          f"{sum(1 for e in td if AR.search(e.get('title') or ''))} · أنماط "
          f"{collections.Counter(re.sub(r'[0-9]+', '#', (e.get('url') or '')[40:110]) for e in td).most_common(3)}")
    for e in sorted(td, key=lambda e: e.get("date") or "", reverse=True)[:6]:
        print(f"     {e.get('date')} {e.get('symbol')} {e.get('type')} · {(e.get('title') or '')[:70]}")

    from app.services.tadawul_announcements import fetch_tadawul_announcements
    from app.services.tadawul_http import fetch, smart_fetch
    items = await fetch_tadawul_announcements(force=True)
    print(f"\n═ أخبارُ السوق ({len(items)}) — هل تحمل صفحةُ الخبر عنوانَه العربيّ؟")
    for it in items[:3]:
        u = it.get("url") or ""
        print(f"   رابط: {u[len('https://www.saudiexchange.sa'):][:160]}")
        for lab, uu in (("كما هو", u), ("بالعربية", re.sub(r"locale=[a-z]+", "locale=ar", u))):
            try:
                st, h = await fetch(uu)
            except Exception as e:                                 # noqa: BLE001
                print(f"     {lab}: تعذّر {type(e).__name__}")
                continue
            c = cands(h)
            ar = [x for x in c if AR.search(x)]
            print(f"     {lab}: {st} · {len(h or '')} حرفاً · مرشّحاتٌ عربية {len(ar)}: {[x[:80] for x in ar[:4]]}")
            if lab == "بالعربية" and not ar:
                print(f"       إنجليزية: {[x[:80] for x in c[:4]]}")

    from app.services.tadawul_disclosure import _endpoint, PAGE, _date
    ep = await _endpoint() or await _endpoint()
    print(f"\n═ إفصاحاتُ الشركات للسوق كلّه (getAnnouncementListData · رمزٌ فارغ) · النقطة {'وُجدت' if ep else 'تعذّرت'}")
    if not ep:
        return
    form = {"annoucmentType": "1_-1", "symbol": "", "sectorDpId": "", "searchType": "", "fromDate": "",
            "toDate": "", "datePeriod": "", "productType": "", "advisorsList": "", "textSearch": "",
            "pageNumberDb": "1", "pageSize": "60"}
    rows = []
    for lab, kw in (("دافئة", dict(warm=PAGE)), ("باردة", {}), ("دافئة+ar", dict(warm=PAGE, params={"locale": "ar"}))):
        try:
            st, raw = await smart_fetch(ep, method="POST", data=form, referer=PAGE,
                                        headers={"X-Requested-With": "XMLHttpRequest"}, **kw)
            rs = (json.loads(raw) or {}).get("announcementList") or [] if st == 200 else []
        except Exception as e:                                     # noqa: BLE001
            print(f"   {lab}: تعذّر {type(e).__name__}: {str(e)[:80]}")
            continue
        t = [str(r.get("SHORT_DESC") or r.get("TITLE") or "") for r in rs]
        print(f"   {lab}: {st} · {len(rs)} صفّاً · بعنوانٍ عربيّ {sum(1 for x in t if AR.search(x))} · برمز "
              f"{sum(1 for r in rs if str(r.get('SYMBOL') or '').isdigit())}")
        if rs and not rows:
            rows = rs
        if rs and sum(1 for x in t if AR.search(x)) * 2 > len(rs):
            rows = rs
    if not rows:
        return
    print(f"   مفاتيحُ الصفّ: {sorted(rows[0].keys())}")
    for k in sorted(rows[0].keys()):
        v = rows[0].get(k)
        if isinstance(v, str) and AR.search(v):
            print(f"     حقلٌ عربيّ: {k} = {v[:70]}")
    ds = sorted(d for d in (_date(r.get("PR_DATE")) for r in rows) if d)
    print(f"   المدى: {ds[0] if ds else '—'} … {ds[-1] if ds else '—'}")
    have = {(e.get("symbol"), e.get("date")) for e in store.values()}
    miss = [r for r in rows if (str(r.get("SYMBOL")), _date(r.get("PR_DATE"))) not in have]
    print(f"   ليس لها حدثٌ في المفكرة بالرمز واليوم نفسيهما: {len(miss)} من {len(rows)}")
    for r in rows[:14]:
        d = _date(r.get("PR_DATE"))
        inn = "في المفكرة" if (str(r.get("SYMBOL")), d) in have else "غائب"
        print(f"     {d} {r.get('SYMBOL')} [{inn}] · {str(r.get('SHORT_DESC') or r.get('TITLE') or '')[:80]}")


asyncio.run(main())
