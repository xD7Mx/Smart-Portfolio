"""
Saudi market directory — the SINGLE self-injected source of truth for every
Tadawul symbol's identity: Arabic name + canonical sector + logo.

Loaded from saudi_directory.json (symbol -> {name, sector, logo}), which was
built by merging the curated name/sector directory with the previously
injected TradingView logos into one authoritative file. This unifies the
whole app: sector (for governance archetypes), name (display), and logo all
resolve from here — never from Yahoo, which only ever provides FINANCIAL
data (prices/statements). No Yahoo-vs-directory conflict is possible because
their responsibilities don't overlap.

The sector names here are the official Arabic (GICS-style) sector labels;
governance_rules.yaml's `sector_archetype` maps every one of them to a
structural archetype, so no sector falls through to a generic default.
"""

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "saudi_directory.json")

try:
    with open(_PATH, encoding="utf-8") as _fh:
        SAUDI_DIRECTORY: dict[str, dict] = json.load(_fh)
except (OSError, ValueError):
    SAUDI_DIRECTORY = {}


# ══ طبقةُ المزامنة فوق الملفّ ══ (D242)
# «تداول» هي مصدرُ الهوية، والمزامنةُ الأسبوعية تكتب ما استجدّ في مخزن
# الحالة لا في هذا الملفّ: فتعبر الحزمَ ولا تُلوّث ملفّاً متتبَّعاً.
# وتُقرأ **هنا** لأن هذا هو المصدرُ الواحد الذي تقرؤه الشاشاتُ كلُّها —
# فلو قُرئت في مكانٍ آخر لصار للهوية مصدران.
_OVERLAY: dict[str, dict] = {}
try:
    from app.services import lastgood as _lg

    _ov = _lg.load("market:directory_overlay")
    if isinstance(_ov, dict):
        _OVERLAY = {k: v for k, v in _ov.items()
                    if isinstance(v, dict) and not k.startswith("_")}
except Exception:                                                 # noqa: BLE001
    _OVERLAY = {}

for _s, _v in _OVERLAY.items():
    _row = dict(SAUDI_DIRECTORY.get(_s) or {})
    for _k in ("name", "sector", "logo", "suspended", "since", "added"):
        if _v.get(_k) is not None:
            _row[_k] = _v[_k]
    SAUDI_DIRECTORY[_s] = _row


def _base(symbol: str) -> str:
    """Normalize '1120.SR' / 'TADAWUL:1120' → '1120'."""
    return str(symbol).replace(".SR", "").replace("TADAWUL:", "").strip()


# Backward-compatible derived lookups (same shape callers already expect).
SYMBOL_TO_SECTOR_AR: dict[str, str] = {
    s: v["sector"] for s, v in SAUDI_DIRECTORY.items() if v.get("sector")
}
SYMBOL_TO_NAME: dict[str, str] = {
    s: v["name"] for s, v in SAUDI_DIRECTORY.items() if v.get("name")
}
SYMBOL_TO_LOGO: dict[str, str] = {
    s: v["logo"] for s, v in SAUDI_DIRECTORY.items() if v.get("logo")
}


def sector_of(symbol: str) -> str | None:
    return SYMBOL_TO_SECTOR_AR.get(_base(symbol))


def name_of(symbol: str) -> str | None:
    return SYMBOL_TO_NAME.get(_base(symbol))


def logo_of(symbol: str) -> str | None:
    return SYMBOL_TO_LOGO.get(_base(symbol))


SUSPENDED: dict[str, str] = {
    s: (v.get("since") or "")
    for s, v in SAUDI_DIRECTORY.items() if v.get("suspended")
}


def is_suspended(symbol: str) -> bool:
    """أموقوفةٌ عن التداول؟ — سعرُها الأخيرُ ليس سعراً حالياً."""
    return _base(symbol) in SUSPENDED


def suspended_since(symbol: str) -> str | None:
    return SUSPENDED.get(_base(symbol)) or None
