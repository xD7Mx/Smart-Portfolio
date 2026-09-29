"""D530 — نفادُ حصّة ياهو لا يُفرغ الرسمَ ولا التحليلَ الفنيّ: آخرُ تاريخٍ صالحٍ يُقدَّم.

    python3 scripts/audit/history_stale_d530.py
"""
import asyncio
import os
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.services import cache, usage_tracker  # noqa: E402
from app.services.market_data import market_service  # noqa: E402

pts = [{"date": f"2026-09-{d:02d}", "close": 10 + d} for d in range(1, 21)]
svc = market_service._yahoo() if hasattr(market_service, "_yahoo") else market_service
cache.set("hist:stale:1120.SR:1y", pts, 14 * 24 * 3600)
usage_tracker.can_call = lambda *_a, **_k: False
import app.services.market_data as MD  # noqa: E402
got = None
for obj in {svc, market_service}:
    try:
        got = asyncio.run(obj.get_history("1120.SR", "1y"))
    except Exception as e:                                        # noqa: BLE001
        got = f"{type(e).__name__}: {e}"
    if got:
        break
ok = got == pts
print(("PASS" if ok else "FAIL"), "D530 نفدت الحصّة ⇒ آخرُ تاريخٍ صالح لا None —", str(got)[:80])
sys.exit(0 if ok else 1)
