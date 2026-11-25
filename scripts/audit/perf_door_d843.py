#!/usr/bin/env python3
"""كاشفُ D843 على الخادم — «لاحظتُ بطئاً عند تحميل التطبيق للمحتوى والصفحات» (المالك 2026-11-25).
قياسٌ لا يكتب شيئاً ولا يطبع رمزاً ولا سرّاً: طلباتُ كلّ صفحةٍ كما يرسلها المتصفّحُ معاً (من سجلّ المتصفّح المحليّ)، عبر الوسيط نفسِه ‏nginx
وبجلسة المالك (رمزٌ يُصنع داخل الحاوية ولا يُطبع)، مرّتين: الأولى كما يجدها المالكُ الآن والثانيةُ بعدها مباشرة — زمنُ كلّ طلبٍ وحجمُه وزمنُ الصفحة كلّها.

    docker exec sp_backend python /app/scripts/audit/perf_door_d843.py
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, "/app")

SHELL = ["/market/official-names", "/settings/server-time", "/market/overview", "/market/news?lang=ar", "/market/movers", "/notifications",
         "/settings/layout"]
PAGES = {
    "المحفظة": ["/holdings", "/holdings/closed", "/companies", "/settings/profile", "/portfolios", "/transactions/pending-splits", "/portfolio/summary",
                "/cash", "/goals/income-timeline", "/goals/progress", "/goals/builtin", "/goals/builtin-config", "/portfolio/history?days=365",
                "/portfolio/metrics"],
    "صقر": ["/market/saqr?market=us", "/market/sessions", "/market/saqr/opportunities?market=us"],
    "الرسم": ["/market/logo/%5ETASI", "/market/econ-events?market=sa&name=x", "/market/history/%5ETASI.SR?tf=1wk", "/market/live/%5ETASI.SR",
              "/market/drawings/%5ETASI.SR", "/market/sessions", "/holdings", "/market/watchlist/groups", "/market/watchlist"],
    "السوق": ["/market/history/%5ETASI.SR?range=6mo", "/market/history/BZ%3DF?range=6mo", "/portfolio/sector-map", "/market/screener",
              "/market/events-market", "/market/summary"],
    "التقارير": ["/portfolios", "/reports"],
}


async def main():
    import httpx
    from app.core.auth import create_access_token
    tok = create_access_token()
    base = None
    for b in ("http://nginx", "http://sp_nginx", "http://localhost:8000"):
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(b + "/api/v1/settings/server-time", headers={"Authorization": f"Bearer {tok}"})
            if r.status_code < 500:
                base = b
                break
        except Exception:                                        # noqa: BLE001
            continue
    print("المدخل:", base or "تعذّر")
    if not base:
        return
    H = {"Authorization": f"Bearer {tok}", "Accept-Encoding": "gzip"}
    async with httpx.AsyncClient(base_url=base + "/api/v1", headers=H, timeout=60) as c:
        async def one(p):
            t0 = time.monotonic()
            try:
                r = await c.get(p)
                return p, r.status_code, len(r.content), r.headers.get("content-encoding", "—"), (time.monotonic() - t0) * 1000
            except Exception as e:                               # noqa: BLE001
                return p, type(e).__name__, 0, "—", (time.monotonic() - t0) * 1000
        for name, reqs in PAGES.items():
            for rnd in ("أوّلاً", "ثانياً"):
                t0 = time.monotonic()
                res = await asyncio.gather(*(one(p) for p in SHELL + reqs))
                wall = (time.monotonic() - t0) * 1000
                kb = sum(x[2] for x in res) / 1024
                print(f"\n══ {name} ({rnd}): الصفحةُ كلّها {wall:.0f}ms · {len(res)} طلباً · {kb:.0f}KB")
                for p, st, n, enc, ms in sorted(res, key=lambda x: -x[4])[:8 if rnd == "أوّلاً" else 4]:
                    print(f"   {ms:7.0f}ms · {st} · {n / 1024:7.1f}KB · ضغط={enc} · {p[:60]}")
    # حملُ الخادم
    try:
        la = os.getloadavg()
        print(f"\nحملُ الخادم: {la[0]:.2f} {la[1]:.2f} {la[2]:.2f} · معالجات {os.cpu_count()}")
        with open("/proc/meminfo") as f:
            m = {l.split(":")[0]: l.split(":")[1].strip() for l in f}
        print("الذاكرة: كلّية", m.get("MemTotal"), "· متاحة", m.get("MemAvailable"))
    except Exception:                                            # noqa: BLE001
        pass

asyncio.run(main())
