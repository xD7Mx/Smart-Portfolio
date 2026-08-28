"""
Usage-based TTL cache for market data.

Data is fetched from providers ONLY when its cached copy has actually expired —
never on every page load. Each data type has a lifetime that matches how often it
really changes, so provider quotas (e.g. Sahmak 100/day) are spent by genuine need,
not by how many times the site is opened or refreshed.
"""

import time
from threading import Lock

_lock = Lock()
_store: dict[str, tuple[float, object]] = {}

# ── Lifetimes per data type (seconds) ─────────────────────────
PRICE_TTL        = 15 * 60            # 15 minutes  — intraday prices
FUNDAMENTALS_TTL = 30 * 24 * 60 * 60  # 30 days     — revenue/earnings/ratios
COMPANY_INFO_TTL = 7 * 24 * 60 * 60   # 7 days      — name/sector/logo
HISTORY_TTL      = 24 * 60 * 60       # 1 day       — daily price history
LIBRARY_TTL      = 30 * 24 * 60 * 60  # 30 days     — Sahmak company library / sharia


def get(key: str):
    """Return cached value if still fresh, else None."""
    with _lock:
        item = _store.get(key)
        if item and item[0] > time.time():
            return item[1]
        return None


def set(key: str, value, ttl: int) -> None:
    with _lock:
        _store[key] = (time.time() + ttl, value)


def age(key: str):
    """Seconds since the value was cached, or None if absent."""
    with _lock:
        item = _store.get(key)
        if not item:
            return None
        return max(0, int(time.time() - (item[0] - _ttl_hint(key))))


def _ttl_hint(key: str) -> int:
    if key.startswith("price:"):
        return PRICE_TTL
    if key.startswith("fund:"):
        return FUNDAMENTALS_TTL
    return COMPANY_INFO_TTL


def clear() -> None:
    with _lock:
        _store.clear()


def purge_expired() -> int:
    """يزيل المفاتيح المنتهية فقط (بلا مسح جماعي) — تنظيف يومي خفيف يمنع تراكم
    المفاتيح المؤرّخة الميتة (رأي/تقييم/نبذة الأمس) في الذاكرة. لا يمسّ أي مفتاح
    ما زال حيًّا فلا يُبطِل كاشًا نافعًا ولا يستهلك حصّة المزوّد. يعيد عدد المُزال."""
    now = time.time()
    with _lock:
        dead = [k for k, (exp, _) in _store.items() if exp <= now]
        for k in dead:
            del _store[k]
    return len(dead)
