"""قوائمُ «إنفستنغ» المستورَدة — مخزنٌ محلّيٌّ لا نداءَ فيه.

## لماذا ملفٌّ يصدّره المالك بيده

بياناتُ الحساب المدفوع خلف تسجيل دخول، وقراءتُها آلياً تعني تخزينَ
كلمة المرور في التطبيق ومخالفةَ شروط الموقع — وأقربُ نتيجةٍ إيقافُ
الحساب. أمّا **تنزيلُ المالك ملفَّه بيده** فاستعمالٌ شخصيٌّ مسموح. فيُصدَّر
الملفُّ ويُستورَد مرّةً كلَّ ربع، ويُقرأ بعدها من القرص بلا شبكةٍ ولا حصّة.

## موضعُه من المصادر

**ياهو هو المزوّد.** وهذا مُكمِّلٌ يملأ ما تركه فارغاً ولا يستبدل رقماً
منه أبداً — وذلك بحكم `_merge_supplement` نفسِه الذي يستعمله «سهمك».
فإن تأخّر استيرادٌ أو نقص ملفٌّ، يعمل التطبيقُ كما هو اليوم بلا انقطاع.

    storage/investing_periods.json
"""

from __future__ import annotations

import json
import os
from threading import Lock

_lock = Lock()
_cache: dict | None = None


def path() -> str:
    d = os.environ.get("SP_STATE_DIR", "/app/storage")
    return os.path.join(d, "investing_periods.json")


def _load() -> dict:
    """{"رمز": [صفوفُ سنوات]} — وملفٌّ غائبٌ أو تالفٌ يعني «لا تكميل»."""
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
    """يُعيد القراءةَ بعد استيرادٍ جديد. يُعيد عددَ الشركات."""
    global _cache
    with _lock:
        _cache = None
    return len(_load())


def meta() -> dict:
    try:
        with open(path(), encoding="utf-8") as fh:
            raw = json.load(fh)
        return {k: v for k, v in raw.items() if k != "companies"}
    except (OSError, ValueError):
        return {}


def financial_periods(symbol: str) -> list[dict]:
    """صفوفُ السنوات لرمزٍ — بالبنية الداخلية نفسِها التي يرجعها «سهمك».

    والرمزُ يُقبل بصيغتيه: «2222» و«2222.SR».
    """
    base = (symbol or "").split(".")[0].strip()
    rows = _load().get(base)
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("year"), int):
            r = dict(r)
            r.setdefault("source", "investing")
            out.append(r)
    out.sort(key=lambda p: p["year"])
    return out


def census() -> dict:
    d = _load()
    years = sorted({r.get("year") for rows in d.values()
                    for r in rows if isinstance(r, dict)} - {None})
    return {"companies": len(d),
            "rows": sum(len(v) for v in d.values()),
            "years": (f"{years[0]}–{years[-1]}" if years else "—")}
