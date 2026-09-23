#!/usr/bin/env python3
"""زمنُ كلّ نقطةٍ تقرؤها صفحةُ السهم وبطاقاتُ السوق — مقيساً (D434).

    docker exec sp_backend python /app/scripts/audit/endpoint_timing.py

قال المالك: «التطبيقُ بطيءٌ في ظهور البيانات داخل صفحة السهم، وبطيءٌ في
ملء بطاقات قسم السوق — أريده سلساً سريعاً بلا تأخير». ولا يُعالَج بطءٌ
قبل أن يُعرف موضعُه: يُحمَّل التطبيقُ نفسُه داخل الحاوية (بياناتُ الخادم
ومخازنُه الحقيقية)، وتُتجاوَز المصادقةُ **في هذه النسخة داخل الذاكرة
وحدَها** فلا يُكتب مفتاحٌ في أمرٍ ولا مخرَج، وتُنادى كلُّ نقطةٍ مرّتين:
الأولى باردةً كما بعد إقلاع، والثانية دافئة. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

SYM = "4071"
MARKET = ("/market/overview", "/market/summary", "/market/movers",
          "/market/sectors", "/market/screener", "/market/news",
          "/market/events-market", "/market/directory")
STOCK = (f"/market/company/{SYM}", f"/market/history/{SYM}?range=1y",
         f"/market/financials/{SYM}?period=annual", f"/market/dividends/{SYM}",
         f"/market/events/{SYM}", f"/market/ownership/{SYM}",
         f"/market/recommendations/{SYM}", f"/market/depth/{SYM}")


async def main() -> int:
    try:
        import httpx
        from app.main import app
        from app.core import security as _sec
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    # تجاوزُ المصادقة في هذه النسخة داخل الذاكرة وحدَها
    for name in ("require_auth", "scope_portfolio", "require_owner"):
        for mod in list(sys.modules.values()):
            dep = getattr(mod, name, None) if mod else None
            if callable(dep):
                app.dependency_overrides[dep] = lambda: None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport,
                                 base_url="http://t/api/v1", timeout=120) as c:
        for title, paths in (("بطاقاتُ السوق", MARKET), (f"صفحةُ السهم {SYM}", STOCK)):
            print(f"═ {title} ═")
            print(f"  {'النقطة':42s} {'باردة':>8s} {'دافئة':>8s}  حالة · حجم")
            tot_c = tot_w = 0.0
            for p in paths:
                row = []
                st = size = None
                for _ in range(2):
                    t0 = time.perf_counter()
                    try:
                        r = await c.get(p)
                        st, size = r.status_code, len(r.content)
                    except Exception as e:                        # noqa: BLE001
                        st, size = type(e).__name__, 0
                    row.append(time.perf_counter() - t0)
                tot_c += row[0]
                tot_w += row[1]
                flag = " ←" if row[0] > 2 else ""
                print(f"  {p:42s} {row[0]:>7.2f}s {row[1]:>7.2f}s  {st} · {size // 1024}KB{flag}")
            print(f"  {'المجموع (تسلسلاً)':42s} {tot_c:>7.2f}s {tot_w:>7.2f}s\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
