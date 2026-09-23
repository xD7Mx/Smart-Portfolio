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

import atexit
import fcntl
import json
import os
import time
from threading import Event, Lock, Thread

_lock = Lock()
_PATH = os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if os.path.isdir("/app/data") else
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lastgood.json")
)
_mem: dict | None = None  # نسخةُ الذاكرة — تُنعَش متى تغيّر الملفّ
_mtime: float | None = None    # زمنُ الملفّ حين قُرئ إلى الذاكرة


def _read_disk() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:                                             # noqa: BLE001
        return {}


# ══ ونسخةُ الذاكرة تُنعَش متى تغيّر الملفّ ══ (D423)
# كانت تُقرأ **مرّةً واحدةً** ثمّ تخدم عمرَ العملية كلَّه. فعمليةٌ
# طويلةُ العمر لا ترى شيئاً كتبته عمليةٌ أخرى بعد إقلاعها — تقرأ غياباً
# حيث المفتاحُ موجودٌ على القرص. وفحصُ زمنِ التعديل رخيصٌ (‏`stat`
# واحدة) وينعش دون أن يُلغي تجميعَ الكتابة.
def _load() -> dict:
    global _mem, _mtime
    try:
        m = os.stat(_PATH).st_mtime
    except OSError:
        m = None
    if _mem is None or (m is not None and m != _mtime):
        disk = _read_disk()
        if _mem is not None and _dirty_keys:
            # وما لم يُكتب بعدُ من هذه العملية لا يُفقَد بالإنعاش
            for k in _dirty_keys:
                if k in _mem:
                    disk[k] = _mem[k]
        _mem, _mtime = disk, m
    return _mem


# ══ الكتابةُ تتجمّع ولا تتكرّر مع كلّ نقطة ══ (D168)
# كانت كلُّ حفظةٍ تُسلسل المخزنَ **كلَّه** إلى القرص. وقد بلغ الملفُّ على
# الخادم ‎7.8 ميجابايت و‎1077 مفتاحاً، فقِيست الحفظةُ الواحدة **1.277
# ثانية** — ومسحُ السوق يحفظ نحو أربعِ مئةِ مرّة، أي ‎~٩ دقائق كتابةً
# على القرص. وكلفةٌ تربيعية: كلّما امتلأ المخزنُ بطُؤ حفظُه.
#
# والأسوأُ أنّ `save` تُستدعى من شيفرةٍ لا متزامنة: ثانيةٌ وربعٌ من
# دخلٍ/خرجٍ حاجبٍ داخل حلقة الأحداث تُجمّد **كلَّ** طلبٍ آخر معها. فهذا
# هو بطءُ فتح الصفحات مقيساً، لا مظنوناً.
#
# فصارت الحفظةُ تُحدِّث الذاكرةَ فوراً — وهي التي تخدم القراءةَ أصلاً —
# وتَسِمُ المخزنَ متّسخاً، ويكتب خيطٌ خلفيٌّ مرّةً كلَّ خمسِ ثوانٍ مهما
# كثُرت الحفظات. فأربعُ مئةِ حفظةٍ تصير كتابةً أو كتابتين.
#
# والمقايضةُ مقصودةٌ ومحدودة: انهيارٌ مفاجئ يفقد خمسَ ثوانٍ من مخزنٍ
# **احتياطيّ** يُعاد بناؤه من المزوّد. ولا يُفقد شيءٌ عند الإغلاق
# المنتظم — `atexit` يُفرِغ ما تبقّى.
_FLUSH_INTERVAL = 5.0
_dirty_keys: set[str] = set()
_wake = Event()
_flusher_started = False


# ══ والكتابةُ تدمج ولا تحلّ محلّ ══ (D423)
# قِيس على خادم المالك: حصادُ القوائم أعلن «قُرئت 176»، ثمّ قرأ كاشفُ
# `xbrl_store_census.py` القرصَ فوجد **صفرَ رمزٍ** تحت `market:xbrl` —
# والملفُّ سليمٌ قابلٌ للكتابة وفيه ‎273 مفتاحاً أخرى. فالحصادُ كُتب
# ثمّ مُحي.
#
# وسببُه هنا بعينه: `flush` كانت تكتب نسخةَ **هذه** العملية كاملةً فوق
# الملفّ. والخادمُ الطويلُ العمر يقرأ المخزَنَ عند إقلاعه — قبل الحصاد —
# ثمّ يكتب لقطةَ أسعارٍ كلَّ خمسِ ثوانٍ، فتنزل نسختُه القديمةُ فوق
# الملفّ وتمحو كلَّ مفتاحٍ كتبته عمليةٌ أخرى بعده.
#
# وأثرُه لم يكن مفتاحاً ضائعاً: **مسحةُ التقييم تعذّرت في ‎269 من ‎273**،
# والسلسلةُ «لها قوائمُ = 0/60»، وصفرُ سعرٍ عادلٍ للسوق كلِّه. أي أنّ
# المحرّكَين يعملان على قوائمَ تُمحى من تحتهما بلا تنبيه.
#
# فصارت تُكتب **المفاتيحُ المتّسخةُ وحدَها**: يُقرأ الملفُّ من القرص
# لحظةَ الكتابة، وتُركَّب عليه، ويُستبدَل. وقفلٌ على ملفٍّ جانبيّ يمنع
# تشابكَ عمليتين بين القراءة والاستبدال — فالنافذةُ ملّي ثانيةٍ لكنّها
# تكفي لمحوٍ صامت.
def flush() -> None:
    """يكتب ما تراكم إن كان ثمّة تراكم. آمنٌ للنداء في أيّ وقت."""
    global _mem, _mtime
    with _lock:
        if not _dirty_keys:
            return
        mine = {k: _mem[k] for k in _dirty_keys if _mem and k in _mem}
        _dirty_keys.clear()
    if not mine:
        return
    lock_path = f"{_PATH}.lock"
    lf = None
    try:
        lf = open(lock_path, "a+")
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        merged = _read_disk()
        merged.update(mine)
        tmp = f"{_PATH}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False)
        os.replace(tmp, _PATH)
        with _lock:
            _mem = merged
            try:
                _mtime = os.stat(_PATH).st_mtime
            except OSError:
                _mtime = None
    except Exception:
        # النسخةُ في الذاكرة ما تزال تخدم عمرَ هذه العملية، وتُعاد
        # المحاولةُ في الدورة التالية — فلا يضيع شيءٌ بصمت.
        with _lock:
            _dirty_keys.update(mine)
    finally:
        if lf is not None:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            finally:
                lf.close()


def _flush_loop() -> None:
    while True:
        _wake.wait(_FLUSH_INTERVAL)
        _wake.clear()
        flush()


def _ensure_flusher() -> None:
    global _flusher_started
    if _flusher_started:
        return
    _flusher_started = True
    Thread(target=_flush_loop, daemon=True, name="lastgood-flush").start()
    atexit.register(flush)


def save(key: str, data) -> None:
    """Persist a successful payload (no-op on falsy data)."""
    if not data:
        return
    with _lock:
        store = _load()
        store[key] = {"data": data, "saved_at": time.time()}
        _dirty_keys.add(key)
    _ensure_flusher()


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
