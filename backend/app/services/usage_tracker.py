"""
Lightweight daily usage tracker + rate guard for market-data providers.
Counts real API calls per provider, resets each day, and lets the caller check
`can_call()` BEFORE hitting a provider so the app never exceeds a free-tier
quota — it degrades gracefully (uses cached/last data) instead of erroring.

## لماذا يُحفظ العدّاد على القرص

كان في الذاكرة وحدها، فيعود إلى الصفر مع كلّ إقلاعِ حاوية. وحدُّ المزوّد
يُحسب على **عنوان الخادم** ولا يعرف أنّ الحاوية أُعيدت. فبعد كلّ بناءٍ
يظنّ الحارسُ أنّ الحصّةَ كاملة، ويطلب، فيردّ المصدرُ ‏`429`. وقد نفدت
مئةُ «سهمك» يوماً كاملاً بهذه الطريقة وحدها. (D146)

واليومُ يُحسب بتوقيت **UTC+3** لا بتوقيت الخادم: «سهمك» تصفّر عند منتصف
ليل التوقيت العربيّ، فلو صُفِّر العدّادُ في موعدٍ آخر لظنّ أنّ له حصّةً
جديدة قبل أن تتجدّد حقّاً.
"""

import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from threading import Lock
from app.core.config import settings as cfg

_lock = Lock()

# ساعاتُ التوقيت العربيّ — مرجعُ التصفير عند المزوّد
_AST = timezone(timedelta(hours=3))


def _today_ast() -> str:
    return datetime.now(_AST).date().isoformat()


def _path() -> str:
    d = getattr(cfg, "SP_STATE_DIR", None) or os.environ.get(
        "SP_STATE_DIR", "/app/storage")
    return os.path.join(d, "usage_counts.json")


def _load() -> tuple[str, dict]:
    """يقرأ عدّادَ اليوم من القرص. وملفٌّ لِيومٍ مضى يُهمَل لا يُعتدّ به."""
    try:
        with open(_path(), encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict) and raw.get("day") == _today_ast():
            counts = raw.get("counts")
            if isinstance(counts, dict):
                return raw["day"], {k: int(v) for k, v in counts.items()
                                    if isinstance(v, (int, float))}
    except (OSError, ValueError, TypeError):
        # لا مِلفَّ أو مِلفٌّ تالف: يُبدأ من الصفر ولا يُسقَط التطبيق.
        pass
    return _today_ast(), {}


def _load_sites() -> dict:
    """الإسنادُ يُقرأ مع العدّاد، ويُهمَل إن كان ليومٍ مضى."""
    try:
        with open(_path(), encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict) and raw.get("day") == _today_ast():
            st = raw.get("sites")
            if isinstance(st, dict):
                return {k: int(v) for k, v in st.items()
                        if isinstance(v, (int, float))}
    except (OSError, ValueError, TypeError):
        pass
    return {}


def _save() -> None:
    """كتابةٌ ذرّية: مؤقّتٌ ثمّ إحلال، فلا يُقرأ ملفٌّ نصفَ مكتوب."""
    try:
        path = _path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"day": _day, "counts": _counts, "sites": _sites}, fh)
        os.replace(tmp, path)
    except OSError:
        # قرصٌ ممتلئ أو للقراءة فقط: العدُّ يبقى في الذاكرة ولا ينهار شيء.
        pass


_day, _counts = _load()
_sites: dict = _load_sites()


def _limits() -> dict:
    """Daily limits, overridable from settings/.env."""
    return {
        "yahoo":  getattr(cfg, "YAHOO_DAILY_LIMIT", 5_000),
        "sahmak": getattr(cfg, "SAHMAK_DAILY_LIMIT", 100),
        "gemini": getattr(cfg, "GEMINI_DAILY_LIMIT", 1500),
    }


def _reset_if_new_day() -> None:
    global _day, _counts, _sites
    today = _today_ast()
    if today != _day:
        _day = today
        _counts = {}
        # الإسنادُ يُصفَّر مع العدّاد — وإلّا نُسب استهلاكُ اليوم إلى أمس.
        _sites = {}
        _save()


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


def _caller() -> str:
    """موضعُ الاستدعاء الحقيقيّ: أوّلُ إطارٍ خارج هذه الوحدة.

    `record` تُستدعى من `market_data` في ثمانية مواضع، ومن دوالَّ أعلى منها.
    فيُصعَد في المكدّس حتى يُتجاوَز هذا الملفُّ نفسُه — وإلا كان كلُّ نداءٍ
    منسوباً إلى السطر الذي يسجّل، لا إلى الذي يطلب.
    """
    try:
        f = sys._getframe(2)
        for _ in range(6):
            if f is None:
                break
            name = f.f_code.co_filename
            if not name.endswith("usage_tracker.py"):
                return f"{pathlib.Path(name).stem}.{f.f_code.co_name}"
            f = f.f_back
    except Exception:                                             # noqa: BLE001
        pass
    return "?"


def record(provider: str) -> None:
    """Increment the call counter for a provider (call on every real request).

    ══ العدُّ بلا إسناد لا يُصلح شيئاً ══
    بلغ ياهو سقفَه (‏5000/5000) فامتنع التطبيقُ عن الجلب حتى منتصف ليل مكة،
    ولم يكن في الملفّ ما يقول **أيُّ مسارٍ** أكل الحصّة — فيُخمَّن الجاني
    ويُعالَج الظنّ. فصار كلُّ نداءٍ يُنسَب إلى موضع طلبه، ويُحفظ الإسنادُ
    مع العدّاد. كلفتُه إطارٌ من المكدّس لكلّ نداءٍ شبكيّ — لا تُذكر بجانب
    نداءٍ عبر الشبكة.
    """
    with _lock:
        _reset_if_new_day()
        _counts[provider] = _counts.get(provider, 0) + 1
        key = f"{provider}:{_caller()}"
        _sites[key] = _sites.get(key, 0) + 1
        _save()


def sites(provider: str | None = None) -> dict:
    """الإسنادُ: كم نداءً من كلِّ موضع، مرتّباً تنازلياً."""
    with _lock:
        _reset_if_new_day()
        items = {k: v for k, v in _sites.items()
                 if provider is None or k.startswith(f"{provider}:")}
        return dict(sorted(items.items(), key=lambda x: -x[1]))


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
