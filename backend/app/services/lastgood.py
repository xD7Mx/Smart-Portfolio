"""
Last-known-good store — the market screens' reliability floor.

Live market data comes from free, unofficial sources that occasionally
fail (rate limits, IP blocks, outages). An in-memory cache dies with the
process, so a restart during an outage used to leave sections EMPTY.
This store persists every successful payload to disk (/app/data is a
compose volume, so it survives restarts and rebuilds); when a live fetch
fails, the endpoint serves the last good copy, stamped with when it was
captured — real data with an honest timestamp, never a blank screen and
never an invented number.
"""

import json
import os
import time
from threading import Lock

_lock = Lock()
_PATH = os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if os.path.isdir("/app/data") else
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lastgood.json")
)
_mem: dict | None = None  # write-through memory copy — disk read only once


def _load() -> dict:
    global _mem
    if _mem is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _mem = json.load(f)
        except Exception:
            _mem = {}
    return _mem


def save(key: str, data) -> None:
    """Persist a successful payload (no-op on falsy data)."""
    if not data:
        return
    with _lock:
        store = _load()
        store[key] = {"data": data, "saved_at": time.time()}
        try:
            tmp = _PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False)
            os.replace(tmp, _PATH)
        except Exception:
            pass  # memory copy still serves this process's lifetime


def load(key: str, max_age_seconds: int | None = None):
    """Return the last good payload, or None if absent/too old.
    The payload gets `_stale_since` (ISO) injected when it's a dict, so the
    UI can badge it as "آخر بيانات متاحة"."""
    with _lock:
        item = _load().get(key)
    if not item:
        return None
    if max_age_seconds is not None and time.time() - item["saved_at"] > max_age_seconds:
        return None
    data = item["data"]
    if isinstance(data, dict):
        from datetime import datetime, timezone
        data = {**data, "_stale_since": datetime.fromtimestamp(item["saved_at"], tz=timezone.utc).isoformat()}
    return data
