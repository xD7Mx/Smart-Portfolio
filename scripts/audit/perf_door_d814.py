#!/usr/bin/env python3
"""كاشفُ D814 على الخادم — «التطبيقُ يأخذ وقتاً: عند التحميل أو البحث أو المسح أو تشغيل الإطارات أو الرسم — خلِّه سريعاً» (المالك 2026-11-24).
قياسٌ لا يكتب شيئاً ولا يطبع رمزاً ولا سعراً:

  ١ التحميل: الصفحةُ الأولى وملفّاتُها كما يقدّمها الخادمُ للمتصفّح (من الوسيط نفسِه ‏nginx): حجمُ كلّ ملفٍّ مضغوطاً وخاماً،
    وهل يُضغط، ورأسُ التخزين، وزمنُه — وأكبرُ الملفّات.
  ٢ الطلبات: ما تطلبه غرفةُ التداول عند الفتح والبحث وتبديل الإطار — كلُّ طلبٍ مرّتين (باردٌ ثمّ دافئ) بزمنه وحجمه، داخل عملية الكاشف
    (التطبيقُ نفسُه بلا فحص الرمز، فلا تُسجَّل جلسةٌ ولا «آخرُ استعمال»).
  ٣ المسح: زمنُ آخر مسحٍ للسوق كما سُجّل.

    docker exec sp_backend python /app/scripts/audit/perf_door_d814.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import asyncio  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/app")


async def static_part():
    import httpx
    print("══ ١ التحميل — الصفحةُ وملفّاتُها من الوسيط")
    base = None
    for b in ("http://nginx", "http://sp_nginx", "http://frontend:3000"):
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(b + "/")
            if r.status_code == 200 and "<html" in r.text.lower():
                base = b
                break
        except Exception:                                        # noqa: BLE001
            continue
    if not base:
        print("   تعذّر الوصولُ إلى الوسيط من الحاوية")
        return
    async with httpx.AsyncClient(timeout=30, headers={"Accept-Encoding": "gzip, br"}) as c:
        t0 = time.monotonic()
        r = await c.get(base + "/")
        html = r.text
        print(f"   الصفحة {base}: {len(r.content)}B · {(time.monotonic() - t0) * 1000:.0f}ms · تخزين={r.headers.get('cache-control', '—')}")
        refs = re.findall(r'(?:src|href)="(/[^"]+\.(?:js|css))"', html)
        print(f"   ملفّاتٌ في الصفحة: {len(refs)} · preload={len(re.findall(r'modulepreload', html))}")
        tot_wire = tot_raw = 0
        rows = []
        for ref in refs:
            t1 = time.monotonic()
            a = await c.get(base + ref)
            ms = (time.monotonic() - t1) * 1000
            wire = int(a.headers.get("content-length") or 0) or len(a.content)
            raw = len(a.content)
            tot_wire += wire
            tot_raw += raw
            rows.append((raw, ref, wire, a.headers.get("content-encoding", "—"), a.headers.get("cache-control", "—"), ms))
        for raw, ref, wire, enc, cc, ms in sorted(rows, reverse=True)[:8]:
            print(f"   {ref[-48:]:48} · خام {raw / 1024:7.0f}KB · على السلك {wire / 1024:6.0f}KB · ضغط={enc} · تخزين={cc} · {ms:.0f}ms")
        print(f"   المجموع: خام {tot_raw / 1024:.0f}KB · على السلك {tot_wire / 1024:.0f}KB")
        # ضغطُ الملفّ الأكبر بمعزلٍ عن الوسيط: هل يضغطه ‏serve نفسُه؟
        if rows:
            big = max(rows)[1]
            for b in ("http://frontend:3000",):
                try:
                    d = await c.get(b + big)
                    print(f"   من ‏serve مباشرةً: ضغط={d.headers.get('content-encoding', '—')} · نوع={d.headers.get('content-type', '—')}")
                except Exception as e:                           # noqa: BLE001
                    print("   من ‏serve مباشرةً: تعذّر", type(e).__name__)


async def api_part():
    import httpx
    from main import app
    from app.core.auth import require_auth
    print("══ ٢ الطلبات — باردٌ ثمّ دافئ (داخل عملية الكاشف)")

    async def ok():
        return None
    app.dependency_overrides[require_auth] = ok
    calls = [
        ("فتحُ الغرفة", "/market/watchlist/groups"), ("فتحُ الغرفة", "/market/watchlist"), ("فتحُ الغرفة", "/market/sessions"),
        ("فتحُ الغرفة", "/market/live/2222.SR"), ("فتحُ الغرفة", "/market/drawings/2222.SR"),
        ("الإطار يوم", "/market/history/2222.SR?tf=1d"), ("الإطار ساعة", "/market/history/2222.SR?tf=1h"),
        ("الإطار 4 ساعات", "/market/history/2222.SR?tf=4h"), ("الإطار 15د", "/market/history/2222.SR?tf=15m"),
        ("الإطار أسبوع", "/market/history/2222.SR?tf=1wk"), ("تاسي يوم", "/market/history/%5ETASI.SR?tf=1d"),
        ("تاسي ساعة", "/market/history/%5ETASI.SR?tf=1h"), ("أبل يوم", "/market/history/AAPL?tf=1d"), ("أبل 5د", "/market/history/AAPL?tf=5m"),
        ("الذهب ساعة", "/market/history/GC%3DF?tf=1h"), ("حيّ أبل", "/market/live/AAPL"),
        ("البحث", "/market/symbol-search?q=AAPL"), ("البحث", "/market/symbol-search?q=nvd"), ("البحث", "/market/saudi-directory"),
    ]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=120) as c:
        for label, path in calls:
            out = []
            for _ in range(2):
                t0 = time.monotonic()
                try:
                    r = await c.get(path)
                    out.append((r.status_code, len(r.content), (time.monotonic() - t0) * 1000))
                except Exception as e:                           # noqa: BLE001
                    out.append((type(e).__name__, 0, (time.monotonic() - t0) * 1000))
            (s1, b1, m1), (s2, b2, m2) = out
            flag = " ⚠" if m1 > 1500 else ""
            print(f"   {label:14} {path[:46]:46} · {s1} · {b1 / 1024:6.0f}KB · باردٌ {m1:6.0f}ms · دافئٌ {m2:5.0f}ms{flag}")
    app.dependency_overrides.clear()


def scan_part():
    print("══ ٣ المسح — آخرُ مسحٍ مسجَّلٍ لكلّ سوق")
    try:
        from app.services import chart_scan as CS
        for mk in ("sa", "us"):
            d = CS.load(mk) or {}
            print(f"   {mk}: في {d.get('at') or '—'} · استغرق {d.get('secs', '—')}ث · الكون {d.get('universe', '—')} · الفُحص {d.get('screened', '—')}")
    except Exception as e:                                       # noqa: BLE001
        print("   تعذّرت القراءة:", type(e).__name__)


async def main():
    await static_part()
    await api_part()
    scan_part()
    print("══ انتهى")


asyncio.run(main())
