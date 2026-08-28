"""
Lightweight in-memory daily usage tracker + rate guard for market-data providers.
Counts real API calls per provider, resets automatically each day, and lets the
caller check `can_call()` BEFORE hitting a provider so the app never exceeds a
free-tier quota — it degrades gracefully (uses cached/last data) instead of
erroring or stopping. This keeps the site running 24/7.
"""

from datetime import date
from threading import Lock
from app.core.config import settings as cfg

_lock = Lock()
_counts: dict[str, int] = {}
_day = date.today()


def _limits() -> dict:
    """Daily limits, overridable from settings/.env."""
    return {
        "yahoo":  getattr(cfg, "YAHOO_DAILY_LIMIT", 500),
        "sahmak": getattr(cfg, "SAHMAK_DAILY_LIMIT", 100),
        "gemini": getattr(cfg, "GEMINI_DAILY_LIMIT", 1500),
    }


def _reset_if_new_day() -> None:
    global _day, _counts
    today = date.today()
    if today != _day:
        _day = today
        _counts = {}


def limit_for(provider: str) -> int:
    return _limits().get(provider, 0)


def can_call(provider: str) -> bool:
    """True if the provider still has quota left today. Call BEFORE a request."""
    with _lock:
        _reset_if_new_day()
        limit = _limits().get(provider, 0)
        if limit <= 0:
            return True  # no cap configured
        return _counts.get(provider, 0) < limit


def record(provider: str) -> None:
    """Increment the call counter for a provider (call on every real request)."""
    with _lock:
        _reset_if_new_day()
        _counts[provider] = _counts.get(provider, 0) + 1


def usage(provider: str) -> dict:
    """Return {daily_used, daily_limit} for a provider."""
    with _lock:
        _reset_if_new_day()
        return {
            "daily_used": _counts.get(provider, 0),
            "daily_limit": _limits().get(provider, 0),
        }


def remaining_fraction(provider: str) -> float:
    """Fraction of today's quota still available (1.0 = untouched, 0.0 = spent).
    Providers without a cap report 1.0."""
    with _lock:
        _reset_if_new_day()
        limit = _limits().get(provider, 0)
        if limit <= 0:
            return 1.0
        return max(0.0, (limit - _counts.get(provider, 0)) / limit)
