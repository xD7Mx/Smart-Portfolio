"""
Usage-based TTL cache for market data.

Data is fetched from providers ONLY when its cached copy has actually expired —
never on every page load. Each data type has a lifetime that matches how often it
really changes, so provider quotas (e.g. Sahmak 100/day) are spent by genuine need,
not by how many times the site is opened or refreshed.
"""

import json
import os
import tempfile
import time
from threading import Lock

from loguru import logger

_lock = Lock()
_store: dict[str, tuple[float, object]] = {}

# ══ ما طالت حياتُه يُحفظ على القرص ══ (D146)
# كانت الذاكرةُ كلُّها في الرام، فتُمحى مع كلّ إقلاعِ حاوية. فيعود
# التطبيقُ يجلب ما جلبه أمس، وتنفد حصّةُ المزوّد في إعادة جلبٍ لا في
# تحليل. ومكتبةُ «سهمك» عمرُها ثلاثون يوماً — ضياعُها عند كلّ بناءٍ
# يُبطل معناها كلَّه.
#
# ولا يُحفظ كلُّ شيء: الأسعارُ عمرُها ربعُ ساعة، وكتابتُها على القرص
# كلفةٌ بلا عائد. فالحدُّ ساعةٌ فما فوق.
_PERSIST_MIN_TTL = 60 * 60
_dirty = False
_last_write = 0.0
_WRITE_EVERY = 5.0        # ثوانٍ — تجميعُ الكتابات في مسحٍ كامل للسوق


def _path() -> str:
    d = os.environ.get("SP_STATE_DIR", "/app/storage")
    return os.path.join(d, "cache_store.json")


def _load_disk() -> None:
    """يُحمّل ما لم ينتهِ عمرُه بعد. والمنتهي يُترك فلا يُحيا ميت."""
    try:
        with open(_path(), encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return
    if not isinstance(raw, dict):
        return
    now = time.time()
    kept = 0
    for k, item in raw.items():
        if (isinstance(item, list) and len(item) == 2
                and isinstance(item[0], (int, float)) and item[0] > now):
            _store[k] = (float(item[0]), item[1])
            kept += 1
    if kept:
        logger.info(f"cache: restored {kept} long-lived keys from disk")


def _flush(force: bool = False) -> None:
    """كتابةٌ ذرّية ومُجمَّعة. تُستدعى تحت القفل."""
    global _dirty, _last_write
    if not _dirty:
        return
    now = time.time()
    if not force and (now - _last_write) < _WRITE_EVERY:
        return
    # ══ قيمةٌ عصيّةٌ تُترك وحدَها، ولا تُسقط الملفَّ كلَّه ══
    # كان `json.dump` على القاموس جملةً واحدة، فأوّلُ قيمةٍ لا تُسلسَل
    # ترفع TypeError فيضيع **كلُّ** ما كان سينزل معها. تُفحص كلُّ قيمةٍ
    # على حِدة فتُستبعد وحدَها ويَسلم الباقي.
    out = {}
    for k, (exp, v) in _store.items():
        if exp - now < _PERSIST_MIN_TTL - 1:
            continue
        try:
            json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
        out[k] = [exp, v]
    tmp = None
    try:
        path = _path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False)
        os.replace(tmp, path)
        tmp = None
        _dirty, _last_write = False, now
    except OSError:
        # قرصٌ ممتلئ أو للقراءة فقط: الذاكرةُ تبقى عاملةً في الرام.
        _dirty = False
    finally:
        # المؤقّتُ لا يُترك خلفنا: تراكمُه يملأ القرصَ بصمت.
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass

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
    global _dirty
    with _lock:
        _store[key] = (time.time() + ttl, value)
        if ttl >= _PERSIST_MIN_TTL:
            _dirty = True
            _flush()


def flush() -> None:
    """يُنزل ما تبقّى إلى القرص فوراً — عند الإطفاء أو بعد مسحٍ كامل."""
    with _lock:
        _flush(force=True)


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
    global _dirty
    with _lock:
        _store.clear()
        _dirty = True
        _flush(force=True)


def purge_expired() -> int:
    """يزيل المفاتيح المنتهية فقط (بلا مسح جماعي) — تنظيف يومي خفيف يمنع تراكم
    المفاتيح المؤرّخة الميتة (رأي/تقييم/نبذة الأمس) في الذاكرة. لا يمسّ أي مفتاح
    ما زال حيًّا فلا يُبطِل كاشًا نافعًا ولا يستهلك حصّة المزوّد. يعيد عدد المُزال."""
    now = time.time()
    with _lock:
        dead = [k for k, (exp, _) in _store.items() if exp <= now]
        for k in dead:
            del _store[k]
        if dead:
            globals()["_dirty"] = True
            _flush(force=True)
    return len(dead)


_load_disk()

# ══ الإنزالُ عند الإطفاء ══
# الكتابةُ مُجمَّعةٌ كلَّ خمس ثوان، فقد يبقى آخرُ ما كُتب في الرام حين
# تُطفأ الحاوية. و`atexit` يضمن نزولَه — وإلّا ضاع آخرُ ما جُلب، وهو
# عينُ العطب الذي نعالجه.
import atexit as _atexit
_atexit.register(flush)
