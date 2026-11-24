#!/usr/bin/env python3
"""حارسُ D797 — «تحليلُ الرسم» لا يبدو ميّتاً حين يزدحم النموذج.

قال المالك (2026-11-24): «تحليلُ الرسم لا يستجيب — أعتقد أنه توقّف بعد تقسيم الشاشة». وقِيس على الخادم: النموذجُ يجيب البرومبتَ نفسَه في 8–10 ثوانٍ
(‏chart_read_speed_door.py) لكنه يردّ «503 high demand» مرّاتٍ في الدقيقة، وكان الانتظارُ بين المحاولات 15 ثمّ 30 ثانية (قراءةُ إطارين 68.8 ثانية
— ‏chart_read_door.py)؛ وفي الشاشات المتعدّدة أربعةُ أطرٍ بصورها تتجاوز مهلةَ الواجهة (120 ثانية). والنماذجُ الاحتياطيةُ قِيست (‏ai_models_door.py).

  ١ مزدحمٌ مرّتين ثمّ يجيب: القراءةُ تعود، والانتظارُ بين المحاولات ثوانٍ (≤ 6 مجموعاً) لا 45.
  ٢ الأساسيُّ مزدحمٌ ثلاثاً: يُنتقل إلى الاحتياطيّ الأوّل فيجيب.
  ٣ نموذجٌ «غيرُ موجود» (404): يُنتقل إلى التالي بلا انتظار.
  ٤ الكلُّ مزدحم: ‏ok=False بسببٍ مسمّى «busy» — لا قراءةَ مختلَقة؛ والكلُّ ينقطع: «timeout».
  ٥ المهلةُ الكلّية دون مهلة الواجهة، ومهلةُ كلّ نداءٍ لا تتجاوز ما بقي منها.
  ٦ الاحتياطيّان المقيسان مضبوطان، والواجهةُ تعدّ الثواني وتسمّي السبب.

    python3 scripts/audit/chart_d797.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d797_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


import httpx  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services import chart_read as CR  # noqa: E402

GOOD = {"candidates": [{"content": {"parts": [{"text": '{"bias": "صاعد", "headline": "اتجاهٌ صاعد", "frames": [], "levels": [], "indicators": []}'}]}}]}
settings.AI_API_KEY = "test-key"
settings.AI_MODEL = "primary-model"
settings.AI_MODEL_FALLBACKS = "backup-one,backup-two"
slept: list[float] = []
calls: list[tuple[str, float]] = []


async def fake_sleep(s, *a, **k):
    slept.append(float(s))


def run(script):
    """script: قائمةُ ردودٍ بالترتيب — (حالة) أو "timeout"."""
    slept.clear()
    calls.clear()
    seq = list(script)

    async def fake_post(url, key, body, timeout):
        calls.append((url.split("/models/")[1].split(":")[0], timeout))
        r = seq.pop(0) if seq else 503
        if r == "timeout":
            raise httpx.ReadTimeout("slow")
        return (r, GOOD if r == 200 else {})
    CR._post = fake_post
    s0 = asyncio.sleep
    asyncio.sleep = fake_sleep
    try:
        return asyncio.run(CR._ask([{"text": "x"}]))
    finally:
        asyncio.sleep = s0


obj, why = run([503, 503, 200])
check(isinstance(obj, dict) and why == "ok" and [m for m, _ in calls] == ["primary-model"] * 3 and sum(slept) <= 6,
      "١ مزدحمٌ مرّتين ثمّ يجيب: القراءةُ تعود، والانتظارُ بين المحاولات ثوانٍ لا 15 ثمّ 30", f"{why} · {calls} · {slept}")
obj, why = run([503, 503, 503, 200])
check(isinstance(obj, dict) and [m for m, _ in calls] == ["primary-model"] * 3 + ["backup-one"],
      "٢ الأساسيُّ مزدحمٌ ثلاثاً ⇒ الاحتياطيُّ الأوّل يجيب", str([m for m, _ in calls]))
obj, why = run([404, 200])
check(isinstance(obj, dict) and [m for m, _ in calls] == ["primary-model", "backup-one"] and not slept,
      "٣ نموذجٌ غيرُ موجود (404) ⇒ التالي فوراً بلا انتظار", f"{calls} · {slept}")
obj, why = run([503] * 9)
o2, why2 = run(["timeout"] * 3)
check(obj is None and why == "busy" and o2 is None and why2 == "timeout" and len(calls) == 3,
      "٤ الكلُّ مزدحم ⇒ ‏busy، والكلُّ ينقطع ⇒ ‏timeout — بلا قراءةٍ مختلَقة", f"{why} · {why2}")
run([200])
check(CR.DEADLINE < 120 and calls and all(t <= CR.DEADLINE for _, t in calls),
      "٥ المهلةُ الكلّية دون مهلة الواجهة (120 ثانية)، ومهلةُ كلّ نداءٍ لا تتجاوزها", f"{CR.DEADLINE} · {calls}")

cfg = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
cr_ui = (ROOT / "frontend/src/components/chart/ChartRead.tsx").read_text(encoding="utf-8")
check('AI_MODEL_FALLBACKS: str = "gemini-3-flash-preview,gemini-flash-lite-latest"' in cfg and 'data-role="chart-read-sec"' in cr_ui
      and 'd?.reason === "busy"' in cr_ui and 'data-role="chart-read-why"' in cr_ui and "RD._gemini" not in (ROOT / "backend/app/services/chart_read.py").read_text(encoding="utf-8"),
      "٦ الاحتياطيّان المقيسان مضبوطان، والواجهةُ تعدّ الثواني أثناء القراءة وتسمّي سببَ التعذّر")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
