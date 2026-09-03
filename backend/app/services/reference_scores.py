"""مراجعُ خارجية للمعايرة — درجةُ سلامةٍ وقيمةٌ عادلة يكتبهما المالك.

## ما هي وما ليست

أرقامٌ يقرؤها المالكُ من اشتراكه في InvestingPro ويكتبها بيده لعيّنةٍ من
الشركات. غرضُها **معايرةُ محرّكنا ومقارنتُه**، لا أن تحلّ محلَّه:

  · لا تدخل درجةَ الحوكمة ولا تغيّرها.
  · لا تُعرض للمستخدم منتَجاً، فهي بياناتُ جهةٍ أخرى مرخَّصةٌ لاطّلاعه.
  · تُقرأ من القرص بلا شبكةٍ ولا حصّة.

فإن تتبّعت درجتُنا درجتَهم على ثلاثين شركة، وثِقنا بمحرّكنا على السوق
كلِّها بلا إدخالٍ يدويٍّ دائم.

    storage/reference_scores.json
"""

from __future__ import annotations

import json
import os
from threading import Lock

_lock = Lock()
_cache: dict | None = None


def path() -> str:
    d = os.environ.get("SP_STATE_DIR", "/app/storage")
    return os.path.join(d, "reference_scores.json")


def _load() -> dict:
    global _cache
    with _lock:
        if _cache is not None:
            return _cache
        try:
            with open(path(), encoding="utf-8") as fh:
                raw = json.load(fh)
            _cache = raw.get("companies") if isinstance(raw, dict) else None
            if not isinstance(_cache, dict):
                _cache = {}
        except (OSError, ValueError):
            _cache = {}
        return _cache


def reload() -> int:
    global _cache
    with _lock:
        _cache = None
    return len(_load())


def get(symbol: str) -> dict | None:
    base = (symbol or "").split(".")[0].strip()
    v = _load().get(base)
    return v if isinstance(v, dict) else None


def all_symbols() -> list[str]:
    return sorted(_load())


def save(rows: dict, source: str = "InvestingPro (قراءةُ المالك)") -> str:
    """كتابةٌ ذرّية. `rows` = {"2222": {"health": .., "fair_value": ..}}"""
    import tempfile
    from datetime import datetime, timezone
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    payload = {"source": source,
               "entered_at": datetime.now(timezone.utc).isoformat(),
               "note": "مرجعٌ للمعايرة — لا يدخل درجةَ الحوكمة ولا يُعرض",
               "companies": rows}
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    reload()
    return p
