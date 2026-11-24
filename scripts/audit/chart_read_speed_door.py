#!/usr/bin/env python3
"""كاشفُ سرعة «تحليل الرسم» (لا يكتب في القاعدة؛ نداءاتٌ للنموذج بإعداداتٍ مختلفة).

قِيس (2026-11-24 · chart_read_door.py): النموذجُ حيٌّ (نداءٌ قصير 200 في 4.8 ثانية) لكنّ قراءةَ إطارين بلا صورة 68.8 ثانية — وفي
الشاشات المتعدّدة أربعةُ أطرٍ بصورها، ومهلةُ الواجهة 120 ثانية. فيُقاس هنا: البرومبتُ نفسُه بإعدادات تفكيرٍ مختلفة — زمنُها،
وحالتُها، وأأعادت JSON يُقرأ، وكم رمزاً كتبت وكم «فكّرت» (‏usageMetadata) — لا يُطبع المفتاحُ ولا الرابط.

    docker exec sp_backend python /app/scripts/audit/chart_read_speed_door.py
"""
import asyncio
import json
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
    from app.services import chart_read as CR
    from app.services.ai_content import _extract_json_obj
    from app.services.market_data import market_service

    frames = []
    for tf, rng, iv in (("1d", "6mo", "1d"), ("1h", "1mo", "1h")):
        pts = await market_service._yahoo()._fetch_chart_points("2222.SR", rng, iv)
        bars = [[int(p["time"]), p.get("open"), p.get("high"), p.get("low"), p.get("close"), int(p.get("volume") or 0)]
                for p in (pts or [])[-120:] if isinstance(p, dict) and p.get("time")]
        if bars:
            frames.append({"tf": tf, "tf_ar": tf, "price": bars[-1][4], "chg_pct": None, "bars": bars, "ind": {}, "levels": [], "shown": []})
    snap = {"symbol": "2222.SR", "name": "أرامكو", "market": "sa", "frames": frames}
    lean = {"symbol": "2222.SR", "name": "أرامكو", "market": "sa",
            "frames": [{**fr, "key_prices": CR.key_prices(fr)} for fr in frames]}
    text = CR.PROMPT.format(what=f"رسمَ سهمٍ واحدٍ على {len(frames)} أطر") + json.dumps(lean, ensure_ascii=False, separators=(",", ":"))
    print(f"══ البرومبت: {len(text)} حرفاً · أطر {len(frames)} · النموذج {settings.AI_MODEL}")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.AI_MODEL}:generateContent"
    variants = [
        ("كما هو اليوم", {}),
        ("thinkingLevel=minimal", {"thinkingConfig": {"thinkingLevel": "minimal"}}),
        ("thinkingLevel=low", {"thinkingConfig": {"thinkingLevel": "low"}}),
        ("thinkingBudget=0", {"thinkingConfig": {"thinkingBudget": 0}}),
        ("JSON مباشر + minimal", {"thinkingConfig": {"thinkingLevel": "minimal"}, "responseMimeType": "application/json"}),
    ]
    for name, extra in variants:
        body = {"contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 3000, **extra}}
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=200) as c:
                r = await c.post(url, params={"key": settings.AI_API_KEY}, json=body)
            s = time.perf_counter() - t0
            if r.status_code != 200:
                e = (r.json().get("error") or {}) if r.headers.get("content-type", "").startswith("application/json") else {}
                print(f"  {name}: HTTP {r.status_code} · {s:.1f}ث · {e.get('status')} — {str(e.get('message') or '')[:160]}")
                continue
            j = r.json()
            u = j.get("usageMetadata") or {}
            txt = ((j.get("candidates") or [{}])[0].get("content") or {}).get("parts", [{}])[0].get("text", "")
            obj = _extract_json_obj(txt)
            ok = isinstance(obj, dict)
            v = CR.validate(obj, snap) if ok else None
            n_out, n_think = u.get("candidatesTokenCount"), u.get("thoughtsTokenCount")
            print(f"  {name}: HTTP 200 · {s:.1f}ث · JSON {ok} · مخرَج {n_out} · تفكير {n_think}"
                  f" · اتّجاه {(v or {}).get('bias')} · مستويات {len((v or {}).get('levels') or [])} · مؤشّرات {len((v or {}).get('indicators') or [])}")
        except Exception as e:                                     # noqa: BLE001
            print(f"  {name}: تعذّر — {type(e).__name__} بعد {time.perf_counter() - t0:.1f}ث")


asyncio.run(main())
