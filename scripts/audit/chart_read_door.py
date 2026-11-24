#!/usr/bin/env python3
"""كاشفُ «تحليل الرسم» على الخادم (لا يكتب في القاعدة؛ نداءان للنموذج).

قال المالك (2026-11-24): «تحليلُ الرسم لا يستجيب — أعتقد أنه توقّف بعد تقسيم الشاشة». فيُقاس الطريقُ حلقةً حلقة:
  ١ النموذج: اسمُه، وأحاضرٌ مفتاحُه (نعم/لا — لا يُطبع)، وحصّتُه اليومية، ونداءٌ نصّيٌّ قصيرٌ مباشر: حالتُه وزمنُه ورسالةُ خطئه.
  ٢ القراءةُ نفسُها (‏chart_read.read) على لقطةٍ من شموع الخادم لإطارين بلا صورة: أنجحت، وكم استغرقت.

    docker exec sp_backend python /app/scripts/audit/chart_read_door.py
"""
import asyncio
import os
import sys
import time

os.environ["TZ"] = "Asia/Riyadh"
if hasattr(time, "tzset"):
    time.tzset()
sys.path.insert(0, "/app")


async def main():
    import httpx
    from app.core.config import settings
    from app.services.usage_tracker import can_call

    print("══ ١ النموذج:")
    has_key = bool(settings.AI_API_KEY)
    print(f"  الاسم: {settings.AI_MODEL} · مفتاحٌ مضبوط: {has_key} · الحصّةُ تسمح: {can_call('gemini')}")
    if settings.AI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
        body = {"contents": [{"parts": [{"text": "أجب بكلمة واحدة: نعم"}]}], "generationConfig": {"maxOutputTokens": 8}}
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(url, params={"key": settings.AI_API_KEY}, json=body)
            ms = (time.perf_counter() - t0) * 1000
            err = ""
            if r.status_code != 200:
                try:
                    e = r.json().get("error") or {}
                    err = f" · الخطأ: {e.get('status')} — {str(e.get('message') or '')[:200]}"
                except Exception:                                  # noqa: BLE001
                    err = " · جسمُ الخطأ غيرُ مقروء"
            print(f"  نداءٌ قصير: HTTP {r.status_code} · {ms:.0f}ms{err}")
        except Exception as e:                                     # noqa: BLE001
            print(f"  نداءٌ قصير: تعذّر — {type(e).__name__}")

    print("══ ٢ القراءة على شموع الخادم (إطاران بلا صورة):")
    from app.services.market_data import market_service
    from app.services.chart_read import read
    frames = []
    for tf, rng, iv in (("1d", "6mo", "1d"), ("1h", "1mo", "1h")):
        try:
            pts = await market_service._yahoo()._fetch_chart_points("2222.SR", rng, iv)
        except Exception:                                          # noqa: BLE001
            pts = []
        bars = [[int(p.get("time") or p.get("t") or 0), p.get("open"), p.get("high"), p.get("low"), p.get("close"), int(p.get("volume") or 0)]
                for p in (pts or [])[-120:] if isinstance(p, dict)]
        if bars:
            frames.append({"tf": tf, "tf_ar": tf, "price": bars[-1][4], "chg_pct": None, "bars": bars, "ind": {}, "levels": [], "shown": []})
        print(f"  {tf}: شموع {len(bars)}")
    if not frames:
        print("  لا شموع — لا قراءة")
        return
    t0 = time.perf_counter()
    try:
        out = await asyncio.wait_for(read({"symbol": "2222.SR", "name": "أرامكو", "market": "sa", "frames": frames, "probe": time.time()}), 300)
        ms = (time.perf_counter() - t0) * 1000
        rd = out.get("reading") or {}
        print(f"  النتيجة: ok={out.get('ok')} · {ms / 1000:.1f} ثانية · مخزَّنة={bool(out.get('cached'))}"
              f" · الاتّجاه={rd.get('bias')} · مستويات={len(rd.get('levels') or [])}")
    except asyncio.TimeoutError:
        print("  النتيجة: تجاوزت 300 ثانية")


asyncio.run(main())
