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
# ‏D582: الملفُّ مشتركٌ بين الخادم والمسحة والكواشف — كلُّ عمليةٍ كانت تكتبه كاملاً من ذاكرتها فتمحو ما
# كتبه غيرُها (قِيس: مفاتيحُ السلامة والتوصيات التي جهّزها الخادمُ غابت عن القرص بعد مسحة النشر).
# فالكتابةُ تدمج ما على القرص متى كتبه غيرُنا منذ آخر كتابةٍ لنا، والمسحُ الكلّيُّ (clear) وحده لا يدمج.
_disk_mtime = 0.0
_wipe = False


def _path() -> str:
    d = os.environ.get("SP_STATE_DIR", "/app/storage")
    return os.path.join(d, "cache_store.json")


def _load_disk() -> None:
    """يُحمّل ما لم ينتهِ عمرُه بعد. والمنتهي يُترك فلا يُحيا ميت."""
    global _disk_mtime
    try:
        with open(_path(), encoding="utf-8") as fh:
            raw = json.load(fh)
        _disk_mtime = os.stat(_path()).st_mtime
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


def _write_merged(force_wipe: bool = False) -> None:
    """‏D592: الكتابةُ إلى القرص خارجَ مسار الطلبات — التحليلُ والتسلسلُ خارجَ القفل، والدمجُ تحته سريع.

    قِيس على الخادم: كان الدمجُ (D582) يُجرى داخل `set` تحت القفل وفي حلقة الأحداث، فكلّما كتبت المسحةُ الملفَّ
    أعاد الخادمُ تحليلَ ميجابايتاتٍ في كتابته التالية، والمسحةُ كذلك — فتوقّف ردُّ الصحة (مهلةُ 10 ثوانٍ)
    وطالت المسحةُ من ربع ساعةٍ إلى أكثر من ساعة. فصار الخيطُ الخلفيُّ وحده يقرأ ويكتب."""
    global _dirty, _last_write, _disk_mtime, _wipe
    now = time.time()
    with _lock:                                                   # لقطةٌ سريعة: مراجعُ لا نسخٌ عميقة
        wipe = _wipe or force_wipe
        snap = {k: (exp, v) for k, (exp, v) in _store.items() if exp - now >= _PERSIST_MIN_TTL - 1}
        _dirty = False
        known_mtime = _disk_mtime
    out = {}
    for k, (exp, v) in snap.items():                              # التحقّقُ من قابلية التسلسل خارجَ القفل
        try:
            json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
        out[k] = [exp, v]
    path = _path()
    lock_fh = None
    tmp = None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            import fcntl
            lock_fh = open(path + ".lock", "a")
            fcntl.flock(lock_fh, fcntl.LOCK_EX)                   # كاتبٌ واحدٌ بين العمليات
        except (ImportError, OSError):
            lock_fh = None
        absorb = {}
        if not wipe:
            try:
                mt = os.stat(path).st_mtime
            except OSError:
                mt = known_mtime
            if mt != known_mtime:                                  # كتبه غيرُنا ⇒ يُدمج (D582)
                try:
                    with open(path, encoding="utf-8") as fh:
                        raw = json.load(fh)
                except (OSError, ValueError):
                    raw = {}
                for k, item in (raw.items() if isinstance(raw, dict) else []):
                    if not (isinstance(item, list) and len(item) == 2 and isinstance(item[0], (int, float))):
                        continue
                    exp = float(item[0])
                    if exp - now < _PERSIST_MIN_TTL - 1:
                        continue
                    mine = out.get(k)
                    if mine is None or exp > mine[0]:
                        out[k] = [exp, item[1]]
                        absorb[k] = (exp, item[1])
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False)
        os.replace(tmp, path)
        tmp = None
        new_mtime = os.stat(path).st_mtime
        with _lock:                                               # يستوعب ما ينقصه — دمجُ قواميسَ سريع
            for k, item in absorb.items():
                cur = _store.get(k)
                if cur is None or item[0] > cur[0]:
                    _store[k] = item
            _disk_mtime, _last_write = new_mtime, now
            if wipe:
                _wipe = False
    except OSError:
        pass                                                      # قرصٌ ممتلئ أو للقراءة: الذاكرةُ تبقى عاملة
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        if lock_fh is not None:
            try:
                lock_fh.close()
            except OSError:
                pass


_wake = None
_writer = None


def _writer_loop() -> None:
    while True:
        _wake.wait(_WRITE_EVERY)
        _wake.clear()
        time.sleep(_WRITE_EVERY)                                  # تجميعُ ما يتلاحق من حفظات
        if _dirty:
            try:
                _write_merged()
            except Exception:                                     # noqa: BLE001
                pass


def _flush(force: bool = False) -> None:
    """تُستدعى تحت القفل: لا تكتب — توقظ الكاتبَ الخلفيّ وحده (D592)."""
    global _wake, _writer
    import threading
    if _wake is None:
        _wake = threading.Event()
    if _writer is None or not _writer.is_alive():
        _writer = threading.Thread(target=_writer_loop, name="cache-writer", daemon=True)
        _writer.start()
    _wake.set()


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


def expire_prefix(prefix: str, ttl: int = 7 * 24 * 3600) -> int:
    """‏D619: يُبطل كلَّ مفتاحٍ يبدأ بـ`prefix` بشاهدِ قبرٍ (قيمةٌ فارغةٌ طويلةُ العمر) لا بحذف —
    الحذفُ وحده يُعيد الدمجُ مع القرص القيمةَ القديمة، والشاهدُ يغلبها في الدمج ويُقرأ «لا شيء» فيُعاد الحساب."""
    global _dirty
    n = 0
    with _lock:
        for k in list(_store):
            if k.startswith(prefix) and _store[k][1] is not None:
                _store[k] = (time.time() + ttl, None)
                n += 1
        if n:
            _dirty = True
            _flush()
    return n


def expire_keys(keys, ttl: int = 7 * 24 * 3600) -> int:
    """كـ`expire_prefix` لمفاتيحَ بعينها — البادئةُ «fvm:v36:7202» تُصيب «72020» كذلك."""
    global _dirty
    n = 0
    with _lock:
        for k in keys:
            if k in _store and _store[k][1] is not None:
                _store[k] = (time.time() + ttl, None)
                n += 1
        if n:
            _dirty = True
            _flush()
    return n


def flush() -> None:
    """يُنزل ما تبقّى إلى القرص فوراً — عند الإطفاء أو بعد مسحٍ كامل (متزامنٌ عمداً)."""
    if _dirty or _wipe:
        _write_merged()


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
    global _dirty, _wipe
    with _lock:
        _store.clear()
        _dirty, _wipe = True, True                      # مسحٌ كلّيٌّ مقصود: لا يُدمج ما على القرص
    _write_merged(force_wipe=True)


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
