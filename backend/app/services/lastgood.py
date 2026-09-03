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
import json
import os
import time
from threading import Event, Lock, Thread

_lock = Lock()
_PATH = os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if os.path.isdir("/app/data") else
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lastgood.json")
)
_mem: dict | None = None  # write-through memory copy — disk read only once


def _load() -> dict:
    global _mem
    if _mem is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                _mem = json.load(f)
        except Exception:
            _mem = {}
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
_dirty = False
_wake = Event()
_flusher_started = False


def flush() -> None:
    """يكتب ما تراكم إن كان ثمّة تراكم. آمنٌ للنداء في أيّ وقت."""
    global _dirty
    with _lock:
        if not _dirty:
            return
        store = dict(_load())
        _dirty = False
    try:
        tmp = f"{_PATH}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False)
        os.replace(tmp, _PATH)
    except Exception:
        # النسخةُ في الذاكرة ما تزال تخدم عمرَ هذه العملية، وتُعاد
        # المحاولةُ في الدورة التالية — فلا يضيع شيءٌ بصمت.
        with _lock:
            _dirty = True


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
    global _dirty
    with _lock:
        store = _load()
        store[key] = {"data": data, "saved_at": time.time()}
        _dirty = True
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
