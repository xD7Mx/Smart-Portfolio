#!/usr/bin/env python3
"""كاشفُ نماذج الذكاء المتاحة للمفتاح (لا يكتب في القاعدة؛ نداءاتٌ قصيرة).

قِيس (2026-11-24 · chart_read_speed_door.py): ‏gemini-3.1-flash-lite يجيب في 8–10 ثوانٍ لكنه يردّ «503 UNAVAILABLE — high demand» مرّتين في دقيقة،
وانتظارُ إعادة المحاولة 15 ثمّ 30 ثانية — فتطول القراءةُ إلى ما فوق مهلة الواجهة. فقبل اختيار نموذجٍ احتياطيٍّ يُقاس ولا يُخمَّن:
  ١ النماذجُ التي يملكها المفتاحُ ويقبل فيها ‏generateContent (الأسماءُ وحدها).
  ٢ لكلّ مرشَّحٍ موجود: نداءان قصيران — حالتُهما وزمنُهما.

    docker exec sp_backend python /app/scripts/audit/ai_models_door.py
"""
import asyncio
import os
import sys
import time

os.environ["TZ"] = "Asia/Riyadh"
if hasattr(time, "tzset"):
    time.tzset()
sys.path.insert(0, "/app")

CANDIDATES = ("gemini-3.1-flash-lite", "gemini-3-flash", "gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.5-flash-lite",
              "gemini-flash-latest", "gemini-flash-lite-latest")


async def main():
    import httpx
    from app.core.config import settings
    if not settings.AI_API_KEY:
        print("لا مفتاح — لا قياس")
        return
    base = "https://generativelanguage.googleapis.com/v1beta"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"{base}/models", params={"key": settings.AI_API_KEY, "pageSize": 200})
        names = []
        if r.status_code == 200:
            for m in r.json().get("models") or []:
                if "generateContent" in (m.get("supportedGenerationMethods") or []):
                    names.append(str(m.get("name", "")).replace("models/", ""))
        print(f"══ ١ النماذجُ المتاحة ({r.status_code}): {len(names)}")
        print("  " + " · ".join(sorted(n for n in names if "gemini" in n)))
        print("══ ٢ المرشَّحون (نداءان قصيران لكلّ):")
        body = {"contents": [{"parts": [{"text": "أجب بكلمة واحدة: نعم"}]}], "generationConfig": {"maxOutputTokens": 8}}
        for m in CANDIDATES:
            if names and m not in names:
                print(f"  {m}: غيرُ متاحٍ للمفتاح")
                continue
            out = []
            for _ in range(2):
                t0 = time.perf_counter()
                try:
                    q = await c.post(f"{base}/models/{m}:generateContent", params={"key": settings.AI_API_KEY}, json=body)
                    out.append(f"{q.status_code}/{time.perf_counter() - t0:.1f}ث")
                except Exception as e:                             # noqa: BLE001
                    out.append(f"{type(e).__name__}/{time.perf_counter() - t0:.1f}ث")
            print(f"  {m}: " + " · ".join(out))


asyncio.run(main())
