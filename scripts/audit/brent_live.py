#!/usr/bin/env python3
"""برنت مباشرٌ من مصدرٍ مقيس، وطبقاتُه مرتَّبة، والغيابُ يُقال (D435).

    python3 scripts/audit/brent_live.py

قال المالك: «حالةُ السوق لنفط برنت تعمل في حين أنّ الرقم لا يظهر… أشعر
أنّنا لم نذهب للمدى الذي نستطيع الوصولَ إليه لإيجاد مصدرٍ مباشرٍ لسعر برنت».

وقِيس بكاشف `brent_sources.py` على خادمه:
  · «TradingView» ‏`FX:UKOIL` — **مباشر** (`update_mode = streaming`) · 103.44
  · ‏`ICEEUR:BRN1!` — مؤجَّلٌ عشر دقائق · 103.08
  · ياهو ‏`BZ=F` — 98.4: **متأخّرٌ عن السوق نحو 5٪**، ومحكومٌ بحصّتنا
    الداخلية التي استنفدتها المسحات، فخلت البطاقةُ وحالةُ السوق تُعرض.

فالترتيب: المباشرُ ← المؤجَّلُ مُعلَناً ← ياهو ← آخرُ رقمٍ معروفٍ بزمنه.
والفحصُ سلوكيّ على دالّة الجلب نفسِها بمصادرَ مُصطنَعة:
  ١· المباشرُ يُقدَّم ومصدرُه وطورُه معلَنان.
  ٢· يسقط المباشرُ ⇒ المؤجَّلُ، موسوماً «مؤجَّل».
  ٣· تسقط «TradingView» كلُّها ⇒ ياهو.
  ٤· يسقط الكلّ ⇒ آخرُ رقمٍ محفوظٍ **بزمنه** — لا فراغ ولا اختلاق.
  ٥· ولا شيءَ محفوظ ⇒ None صريحٌ لا رقمٌ مصنوع.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import commodity_quote as CQ
    from app.services import cache
except (ModuleNotFoundError, ImportError) as e:
    if "commodity_quote" in str(e):
        check(False, "٠ لبرنت دالّةُ جلبٍ بطبقاتٍ مرتَّبة", "لا وحدةَ commodity_quote")
        print("FAIL D435 — برنت مباشرٌ من مصدرٍ مقيس")
        sys.exit(1)
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)


def _tv_rows(rows):
    async def f(*_a, **_k):
        return rows
    return f


async def _none(*_a, **_k):
    return None


def _run(tv, yahoo):
    cache.clear()
    CQ._tv_scan = tv
    CQ._yahoo_brent = yahoo
    return asyncio.run(CQ.brent_quote())


LIVE = {"FX:UKOIL": {"close": 103.44, "change": 4.92, "change_abs": 4.85,
                     "update_mode": "streaming"},
        "ICEEUR:BRN1!": {"close": 103.08, "change": 3.86, "change_abs": 3.83,
                         "update_mode": "delayed_streaming_600"}}

q = _run(_tv_rows(LIVE), _none)
check((q or {}).get("price") == 103.44 and (q or {}).get("change_pct") == 4.92,
      "١ المباشرُ يُقدَّم", str(q)[:120])
check("TradingView" in str((q or {}).get("source")) and (q or {}).get("delayed") is False,
      "١ب ومصدرُه وطورُه معلَنان", f"{(q or {}).get('source')} · مؤجَّل={(q or {}).get('delayed')}")

q = _run(_tv_rows({"ICEEUR:BRN1!": LIVE["ICEEUR:BRN1!"]}), _none)
check((q or {}).get("price") == 103.08 and (q or {}).get("delayed") is True,
      "٢ يسقط المباشرُ ⇒ المؤجَّلُ موسوماً «مؤجَّل»", str(q)[:120])


async def _yh(*_a, **_k):
    return {"price": 98.4, "change_pct": 0.5, "change": 0.49}

q = _run(_tv_rows({}), _yh)
check((q or {}).get("price") == 98.4 and "ياهو" in str((q or {}).get("source")),
      "٣ تسقط «TradingView» ⇒ ياهو", str(q)[:120])

# ٤ · آخرُ رقمٍ محفوظ: يُحفظ من نجاحٍ سابق ثمّ يسقط الكلّ
_run(_tv_rows(LIVE), _none)
from app.services import lastgood as _lg                           # noqa: E402
_lg.flush()
q = _run(_tv_rows({}), _none)
check((q or {}).get("price") == 103.44 and bool((q or {}).get("stale_since")),
      "٤ يسقط الكلّ ⇒ آخرُ رقمٍ محفوظٍ بزمنه", str(q)[:140])

# ٥ · لا شيءَ محفوظ
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "empty.json")
import importlib                                                     # noqa: E402
importlib.reload(_lg)
importlib.reload(CQ)
q = _run(_tv_rows({}), _none)
check(q is None, "٥ ولا شيءَ محفوظ ⇒ None صريحٌ لا رقمٌ مصنوع", str(q))

print(("FAIL" if fail else "PASS") + " D435 — برنت مباشرٌ من مصدرٍ مقيس")
sys.exit(fail)
