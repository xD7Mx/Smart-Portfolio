#!/usr/bin/env python3
"""كاشفُ مصدرِ شموع تاسي الكاملة (‏D739) — قارئٌ فقط: أيُّ رسمٍ في «تداول» يسلّم فتحاً وأعلى وأدنى وإغلاقاً لكلّ يومٍ منذ بدايته؟
يقرأ أسماءَ أنواع الرسم من سكربتات صفحة المؤشّرات نفسِها، ويجرّب كلَّ نوعٍ على «tasi»، ويطبع عددَ النقاط وأسماءَ حقولها وأوّلَها وآخرَها."""
import asyncio, json, re, sys
sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_http import fetch
    base = "https://www.saudiexchange.sa"
    names = set(["SQL_T_IC_ALL_COM", "SQL_MI_MSPV"])
    for page in ("/wps/portal/saudiexchange/ourmarkets/main-market-watch/indices-performance",
                 "/wps/portal/saudiexchange/newsandreports/reports-publications/historical-reports",
                 "/wps/portal/saudiexchange/hidden/indices-graph"):
        try:
            st, body = await fetch(base + page)
            print("صفحة", page, st, len(body or ""))
            for js in set(re.findall(r'src="([^"]+\.js[^"]*)"', body or "")):
                if "chart" in js.lower() or "indice" in js.lower() or "graph" in js.lower():
                    st2, b2 = await fetch(js if js.startswith("http") else base + js)
                    found = set(re.findall(r"SQL_[A-Z0-9_]+", b2 or ""))
                    print("  سكربت", js[-60:], st2, sorted(found)[:40])
                    names |= found
            names |= set(re.findall(r"SQL_[A-Z0-9_]+", body or ""))
        except Exception as e:                                    # noqa: BLE001
            print("صفحة", page, "✘", type(e).__name__)
    print("الأنواع:", sorted(names))
    for n in sorted(names):
        url = f"{base}/tadawul.eportal.charts.v2/ChartGenerator?methodType=parsingMethod&chart-type={n}&chart-parameter=tasi&format=json"
        try:
            st, body = await fetch(url)
            data = json.loads(body) if st == 200 and body else None
        except Exception as e:                                    # noqa: BLE001
            print(f"{n}: ✘ {type(e).__name__}")
            continue
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), data)
        if not isinstance(data, list) or not data:
            print(f"{n}: {st} · لا قائمة · {str(body)[:120]!r}")
            continue
        first, last = data[0], data[-1]
        keys = sorted(first.keys()) if isinstance(first, dict) else type(first).__name__
        print(f"{n}: {len(data)} نقطة · حقول {keys}\n   أوّل {json.dumps(first, ensure_ascii=False)[:220]}\n   آخر {json.dumps(last, ensure_ascii=False)[:220]}")


asyncio.run(main())
