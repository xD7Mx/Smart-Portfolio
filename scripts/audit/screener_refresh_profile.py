#!/usr/bin/env python3
"""أين تذهب ثواني إنعاش جدول السوق (D434).

    docker exec sp_backend python /app/scripts/audit/screener_refresh_profile.py

قِيس بكاشف `endpoint_timing.py`: `/market/screener` باردةً **285.8 ثانية**
ودافئةً 0.23. والنقطةُ لا تبني الجدول في الطلب — تُعيد اللقطةَ المحفوظة
بعد `refresh_derived` على ‎270 صفّاً. أي نحو ثانيةٍ للصفّ: نداءٌ ينتظر
شيئاً في كلّ صفّ. فيُشغَّل الإنعاشُ مرّةً تحت المُحلِّل ويُطبع أثقلُ
الدوالّ زمناً تراكمياً — فيُعرف ما ينتظر قبل أيّ تعديل. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import cProfile
import io
import pathlib
import pstats
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


def main() -> int:
    try:
        from app.services.market_screener import get_cached_screener, refresh_derived
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    rows = get_cached_screener() or []
    print(f"صفوفُ اللقطة: {len(rows)}")
    if not rows:
        return 0
    rows = rows[:40]                       # عيّنةٌ تكفي لتسمية ما ينتظر
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    asyncio.run(refresh_derived([dict(r) for r in rows]))
    pr.disable()
    dt = time.perf_counter() - t0
    print(f"إنعاشُ {len(rows)} صفّاً: {dt:.1f} ثانية ({dt / len(rows):.2f} للصفّ)\n")
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(28)
    for ln in s.getvalue().splitlines():
        if "/app/app/" in ln or "site-packages/httpx" in ln or "socket" in ln \
                or "time.sleep" in ln or "ncalls" in ln or "select" in ln:
            print(ln[:170])
    return 0


if __name__ == "__main__":
    sys.exit(main())
