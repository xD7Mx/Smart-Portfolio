#!/usr/bin/env python3
"""كاشفُ مصادر شموع «تاسي» اللحظية (المالك: «إطاراتُ الساعة والبقيّة ليست حقيقية») — قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tasi_intraday_door.py

قِيس بـ`bars_door.py` أنّ ساعةَ تاسي وأربعَ ساعاته شموعٌ يومية تحت اسمٍ آخر. فيُقاس هنا
كلُّ مصدرٍ ممكنٍ لشموعٍ دون اليوم: ياهو بفاصل 60د، وكلُّ أنواع مولّد رسم «تداول» المذكورة
في صفحاتها وملفّات رسمها — لكلٍّ عددُ نقاطه وأيّامُه المتمايزة وساعاتُه.
"""
import asyncio, json, re, sys
sys.path.insert(0, "/app")
GEN = "https://www.saudiexchange.sa/tadawul.eportal.charts.v2/ChartGenerator"
PAGES = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch/indices-performance",
         "https://www.saudiexchange.sa/wps/portal/saudiexchange/home",
         "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch")


def shape(rows):
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return "—"
    ds = [str(r.get("dateTime") or r.get("date") or "") for r in rows]
    days = sorted({d[:10] for d in ds if d})
    hrs = sorted({d[11:13] for d in ds if len(d) > 12})
    return f"{len(rows)} نقطة · {len(days)} يوماً ({days[0] if days else '—'} → {days[-1] if days else '—'}) · ساعات {hrs[:10]} · مفاتيح {list(rows[0])[:6]}"


async def yahoo():
    import httpx
    from datetime import datetime, timezone, timedelta
    riy = timezone(timedelta(hours=3))
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
        for sym in ("%5ETASI.SR", "%5ETASI"):
            for rng, iv in (("5d", "60m"), ("1mo", "60m"), ("3mo", "60m"), ("5d", "15m"), ("1mo", "1h")):
                try:
                    r = await c.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={iv}")
                    res = (r.json().get("chart", {}).get("result") or [None])[0] if r.status_code == 200 else None
                    ts = (res or {}).get("timestamp") or []
                    q = (((res or {}).get("indicators") or {}).get("quote") or [{}])[0]
                    cl = [x for x in (q.get("close") or []) if x is not None]
                    ds = [datetime.fromtimestamp(t, tz=riy).strftime("%Y-%m-%d %H:%M") for t in ts]
                    days = sorted({d[:10] for d in ds})
                    print(f"  ياهو {sym} {rng}/{iv}: HTTP {r.status_code} · {len(ts)} طابعاً · {len(cl)} إغلاقاً · {len(days)} يوماً"
                          f" · {ds[:1]} → {ds[-1:]} · ساعات {sorted({d[11:16] for d in ds})[:8]}"
                          f" · granularity={(res or {}).get('meta', {}).get('dataGranularity')}")
                except Exception as e:                             # noqa: BLE001
                    print(f"  ياهو {sym} {rng}/{iv}: ✘ {type(e).__name__}: {str(e)[:100]}")


async def tadawul():
    from app.services.tadawul_http import fetch
    types, pages, js_urls = set(), set(), set()
    for u in PAGES:
        try:
            st, body = await fetch(u)
        except Exception as e:                                     # noqa: BLE001
            print(f"  صفحة {u[-40:]}: ✘ {e}"); continue
        body = body or ""
        types |= set(re.findall(r"chart-type=([A-Za-z0-9_]+)", body)) | set(re.findall(r"['\"](SQL_[A-Z0-9_]+)['\"]", body))
        pages |= set(re.findall(r"pageName=([A-Za-z0-9_]+)", body))
        js_urls |= set(re.findall(r"[\"'](/[^\"']*\.js)[\"']", body))
        print(f"  صفحة …{u[-45:]}: HTTP {st} · {len(body)}")
    js_urls = [j for j in js_urls if re.search(r"graph|chart|index|tasi|market", j, re.I)]
    print(f"  ملفّاتُ سكربتٍ مرشّحة: {len(js_urls)}")
    for j in sorted(js_urls)[:14]:
        try:
            st, js = await fetch("https://www.saudiexchange.sa" + j)
        except Exception:                                          # noqa: BLE001
            continue
        js = js or ""
        t2 = set(re.findall(r"['\"](SQL_[A-Z0-9_]+)['\"]", js)) | set(re.findall(r"chart-type=([A-Za-z0-9_]+)", js))
        p2 = set(re.findall(r"pageName=([A-Za-z0-9_]+)", js))
        if t2 or p2:
            print(f"   ═ {j[-70:]} — أنواع {sorted(t2)} · صفحات {sorted(p2)}")
            for m in list(re.finditer(r"SQL_[A-Z0-9_]+", js))[:6]:
                print("      ↳", re.sub(r"\s+", " ", js[max(0, m.start() - 140):m.end() + 140])[:280])
        types |= t2
        pages |= p2
    print(f"  كلُّ الأنواع: {sorted(types)}")
    print(f"  كلُّ أسماء الصفحات: {sorted(pages)}")
    for t in sorted(types):
        for extra in ("",) + tuple(f"&pageName={p}" for p in sorted(pages)[:4]):
            url = f"{GEN}?methodType=parsingMethod&chart-type={t}&chart-parameter=tasi&format=json{extra}"
            try:
                st, body = await fetch(url)
                rows = json.loads(body or "null")
            except Exception:                                      # noqa: BLE001
                rows, st = None, "✘"
            print(f"   {t}{extra}: HTTP {st} · {shape(rows)}")


async def main():
    print("═ ياهو بفواصل دون اليوم لمؤشّر تاسي")
    await yahoo()
    print("\n═ مولّدُ رسم «تداول» — كلُّ الأنواع المذكورة في صفحاته")
    await tadawul()
    print("\n═ ما يحفظه التطبيقُ اليومَ من جلسات تاسي")
    from app.services import lastgood
    for k in ("market:tasi_daily", "market:tasi_intraday"):
        v = lastgood.load(k) or {}
        print(f"  {k}: {len(v) if isinstance(v, dict) else '—'} مفتاحاً · آخرُها {sorted(v)[-3:] if isinstance(v, dict) else ''}")


asyncio.run(main())
