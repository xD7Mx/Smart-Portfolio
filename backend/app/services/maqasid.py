"""
Sharia ratings — layered, authoritative, offline.

Layer 1 — Al-Maqasid (app/data/maqasid_ratings.json): 340 non-financial Saudi
          companies, COMPLIANT + a purification amount per share.
Layer 2 — Argaam (app/data/argaam_ratings.json): 268 companies across ALL
          sectors (incl. banks/insurance) screened by the Al-Rajhi Capital and
          Albilad committees. A ✓ from any committee ⇒ COMPLIANT (with the
          committee named as the source); no ✓ ⇒ NON_COMPLIANT. No purification.
Anything in neither layer returns None and falls through to the honest AI
lookup. Zero API calls, zero quota, works 24/7.
"""

import json
import os
from functools import lru_cache
from loguru import logger

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_MAQASID_PATH = os.path.join(_DATA_DIR, "maqasid_ratings.json")
_ARGAAM_PATH = os.path.join(_DATA_DIR, "argaam_ratings.json")


def _read(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Sharia data not loaded ({os.path.basename(path)}): {e}")
        return {"meta": {}, "ratings": {}}


@lru_cache(maxsize=1)
def _maqasid() -> dict:
    return _read(_MAQASID_PATH)


@lru_cache(maxsize=1)
def _argaam() -> dict:
    return _read(_ARGAAM_PATH)


def meta() -> dict:
    return {"maqasid": _maqasid().get("meta", {}), "argaam": _argaam().get("meta", {})}


def rating(symbol: str) -> dict | None:
    """Returns {status, purification?, source} for a Saudi symbol, applying the
    layer priority (Maqasid → Argaam → None). None means neither source covers
    it, so the caller uses the honest AI lookup."""
    base = str(symbol or "").replace(".SR", "").strip()

    r = _maqasid().get("ratings", {}).get(base)
    if r:
        return {"status": r.get("status"), "purification": r.get("purification"),
                "source": r.get("source", "المقاصد"), "note": r.get("note")}

    a = _argaam().get("ratings", {}).get(base)
    if a:
        srcs = a.get("sources", [])
        if a.get("status") == "COMPLIANT":
            source = " و".join(srcs) if srcs else "أرقام"
        else:
            source = "أرقام"
        return {"status": a.get("status"), "purification": None, "source": source}

    return None
