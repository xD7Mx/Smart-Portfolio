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


# شدّةُ الحكم مرتّبةً — لا تُقارَن الأحكامُ بنصّها بل برتبتها.
_RANK = {"COMPLIANT": 0, "MIXED": 1, "NON_COMPLIANT": 2}
_AR_STATUS = {"COMPLIANT": "نقية", "MIXED": "مختلطة",
              "NON_COMPLIANT": "غير متوافقة"}


def rating(symbol: str) -> dict | None:
    """Returns {status, purification?, source} for a Saudi symbol, applying the
    layer priority (Maqasid → Argaam → None). None means neither source covers
    it, so the caller uses the honest AI lookup."""
    base = str(symbol or "").replace(".SR", "").strip()

    r = _maqasid().get("ratings", {}).get(base)
    if r:
        out = {"status": r.get("status"), "purification": r.get("purification"),
               "source": r.get("source", "المقاصد"), "note": r.get("note")}
        # ══ الأولويةُ للتغطية، والأشدُّ يغلب عند التعارض ══
        # رأى المالكُ «المملكة» (‏4280) مختلطةً وهي غيرُ متوافقةٍ عند أرقام.
        # والأولويةُ كانت تأخذ المقاصدَ صامتةً فيُخفى الخلاف. وقِيس مداه:
        # ‎54 اختلافاً بين المصدرين، في ‎52 منها المقاصدُ أشدّ — فالأولويةُ
        # تعمل صواباً — وفي اثنين فقط أرقامُ أشدّ (‏4280 · 4072).
        #
        # ونصُّ الميثاق: «عند الشك يُخفَّض التقييم لا يُرفَع». وحكمٌ شرعيٌّ
        # أخفُّ من أحد مصدرَيه ليس ترجيحاً بل تساهلٌ في أخطرِ ما نعرضه.
        # فيُؤخذ الأشدُّ ويُعلَن الخلافُ بمصدريه — ولا يُطهَّر ما حُكم بعدم
        # توافقه، فيسقط مبلغُ التطهير معه.
        a0 = _argaam().get("ratings", {}).get(base)
        if a0 and _RANK.get(a0.get("status"), 0) > _RANK.get(out["status"], 0):
            out = {"status": a0.get("status"), "purification": None,
                   "source": "أرقام · والمقاصد أخفّ",
                   "note": f"تعارضُ مصدرين — أُخذ الأشدّ. المقاصد: "
                           f"{_AR_STATUS.get(r.get('status'), r.get('status'))}."}
        return out

    a = _argaam().get("ratings", {}).get(base)
    if a:
        srcs = a.get("sources", [])
        if a.get("status") == "COMPLIANT":
            source = " و".join(srcs) if srcs else "أرقام"
        else:
            source = "أرقام"
        return {"status": a.get("status"), "purification": None, "source": source}

    return None
