#!/usr/bin/env python3
"""أنواعُ رسم «تداول» للمؤشّر بمُدَدٍ أطول — من ملفّ الرسم نفسِه (D461). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/tasi_ranges_door.py

قال المالك: «شارت تاسي لا يتغيّر حسب الإطار أو المدّة». ومولّدُ الرسم الذي
نقرؤه (`SQL_MI_MSPV`) جلسةُ اليوم وحدَها. فيُقرأ `indicesGraph.js` وملفّاتُ
الرسم في صفحة المؤشّرات، وتُطبع كلُّ قيم `chart-type` وأسماءُ المُدد، ثمّ
يُنادى كلُّ نوعٍ مكتشَف لتاسي ويُطبع عددُ نقاطه ومداه الزمنيّ.
"""
import asyncio, json, re, sys
sys.path.insert(0, "/app")
PAGES = ("https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch/indices-performance",
         "https://www.saudiexchange.sa/wps/portal/saudiexchange/home")
GEN = "https://www.saudiexchange.sa/tadawul.eportal.charts.v2/ChartGenerator"


async def main():
    try:
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    types, js_urls = set(), set()
    for u in PAGES:
        st, body = await fetch(u)
        body = body or ""
        types |= set(re.findall(r"chart-type=([A-Z0-9_]+)", body))
        types |= set(re.findall(r"['\"](SQL_[A-Z0-9_]+)['\"]", body))
        js_urls |= set(re.findall(r"[\"'](/[^\"']*(?:[Gg]raph|[Cc]hart)[^\"']*\.js)[\"']", body))
    for j in sorted(js_urls)[:8]:
        st, js = await fetch("https://www.saudiexchange.sa" + j)
        js = js or ""
        t2 = set(re.findall(r"['\"](SQL_[A-Z0-9_]+)['\"]", js)) | set(re.findall(r"chart-type=([A-Z0-9_]+)", js))
        print(f"═ {j} — HTTP {st} · {len(js)} · أنواع={sorted(t2)}")
        for m in re.finditer(r"(1M|3M|6M|1Y|YTD|5Y|period|Period|duration)", js):
            print("   ↳", re.sub(r"\s+", " ", js[max(0, m.start()-120):m.end()+160])[:260]); break
        types |= t2
    print("كلُّ الأنواع المكتشفة:", sorted(types))
    for t in sorted(types):
        for extra in ("", "&period=1Y", "&duration=1Y"):
            url = f"{GEN}?methodType=parsingMethod&chart-type={t}&chart-parameter=tasi&format=json{extra}"
            st, body = await fetch(url)
            try:
                rows = json.loads(body or "null")
            except Exception:                                     # noqa: BLE001
                rows = None
            if isinstance(rows, list) and rows:
                d0 = rows[0].get("dateTime") if isinstance(rows[0], dict) else rows[0]
                d1 = rows[-1].get("dateTime") if isinstance(rows[-1], dict) else rows[-1]
                print(f"   ✦ {t}{extra} — {len(rows)} نقطة · {d0} → {d1} · مفاتيح {list(rows[0])[:6] if isinstance(rows[0], dict) else ''}")
            else:
                print(f"   · {t}{extra} — HTTP {st} · {(body or '')[:80]!r}")
    return 0

sys.exit(asyncio.run(main()))
