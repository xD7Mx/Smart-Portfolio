"""
سجلّ الجلسات النشطة — من يدخل تطبيقك، من أي جهاز، ومتى كان آخر نشاط له.

لماذا ملفّ على القرص لا جدول في قاعدة البيانات: طبقة المصادقة تعمل قبل أي
جلسة قاعدة بيانات وفي كل طلب تقريباً، فربطها بالقاعدة يعني كتابةً على كل نداء
ويجرّ ترحيلاً (migration) على قاعدةٍ تحمل بيانات المالك الحقيقية. الملفّ هنا
أخفّ وأأمن: لا يمسّ بيانات المحفظة إطلاقاً، ويُحذف بلا أثر لو أردت.

ما يُسجَّل: بصمة التوكن (jti) · وقت الدخول · آخر نشاط · عنوان IP · وصف الجهاز
المستنبَط من User-Agent. **لا يُسجَّل** أي محتوى للطلبات ولا بيانات محفظة.
"""
from __future__ import annotations

import json
import os
import threading
import time

from app.core.auth import _PWD_PATH  # نفس المجلد القابل للكتابة

_PATH = os.path.join(os.path.dirname(_PWD_PATH), "sessions.json")
_LOCK = threading.Lock()

# لا نكتب على القرص مع كل طلب — نحدّث «آخر نشاط» في الذاكرة ونُنزّله كل دقيقة.
_FLUSH_EVERY = 60
_MAX_SESSIONS = 200          # سقفٌ يمنع تضخّم الملف
_REVOKED_GRACE = 10 * 60     # مهلة بقاء الجلسة المُنهاة في القائمة
_last_flush = 0.0
_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _cache = data if isinstance(data, dict) else {}
    except Exception:
        _cache = {}
    _restore_revoked(_cache)
    return _cache


def _restore_revoked(data: dict) -> None:
    """يُعيد الجلسات المُنهاة إلى قائمة الإبطال في الذاكرة بعد إعادة التشغيل.

    قائمة الإبطال في `auth` ذاكرةٌ فقط، والحقبة لا تُرفع عند الإقلاع كي تبقى
    الجلسات القائمة صالحة. بدون هذا السطر كانت إعادة تشغيل الخادم **تُحيي**
    توكناً أنهيتَه — تُنهي جهازاً مسروقاً فيعود يعمل بعد أول تحديث."""
    try:
        from app.core.auth import _revoked_jti
        now = time.time()
        for jti, row in data.items():
            if not row.get("revoked"):
                continue
            exp = row.get("expires_at")
            exp = float(exp) if exp else now + 24 * 3600   # مجهول الأجل: يوم احتياطاً
            if exp > now:
                _revoked_jti.setdefault(jti, exp)
    except Exception:
        pass


def _save(force: bool = False) -> None:
    global _last_flush
    now = time.time()
    if not force and now - _last_flush < _FLUSH_EVERY:
        return
    _last_flush = now
    data = _load()
    if len(data) > _MAX_SESSIONS:                     # نُبقي الأحدث نشاطاً
        keep = sorted(data.items(), key=lambda kv: kv[1].get("last_seen", 0), reverse=True)[:_MAX_SESSIONS]
        data = dict(keep)
        globals()["_cache"] = data
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, _PATH)                        # كتابة ذرّية: لا ملفّ نصف مكتوب
    except Exception:
        pass


def describe_device(ua: str) -> str:
    """وصفٌ مقروء للجهاز من User-Agent — تقريبيّ بطبيعته، فالـUA قابل للانتحال.
    نعرضه كدليلٍ مساعد لا كإثبات هوية."""
    u = (ua or "").lower()
    if not u:
        return "جهاز غير معروف"
    if "ipad" in u:
        dev = "آيباد"
    elif "iphone" in u:
        dev = "آيفون"
    elif "android" in u:
        dev = "أندرويد"
    elif "windows" in u:
        dev = "ويندوز"
    elif "mac os" in u or "macintosh" in u:
        dev = "ماك"
    elif "linux" in u:
        dev = "لينكس"
    else:
        dev = "جهاز غير معروف"
    if "edg/" in u:
        br = "Edge"
    elif "chrome" in u and "chromium" not in u:
        br = "Chrome"
    elif "firefox" in u:
        br = "Firefox"
    elif "safari" in u:
        br = "Safari"
    else:
        br = None
    return f"{dev} · {br}" if br else dev


def open_session(jti: str, ip: str, ua: str, expires_at: float | None = None,
                 device_id: str | None = None) -> list[str]:
    """يُسجَّل عند تسجيل دخول ناجح. و`expires_at` وقت انتهاء التوكن نفسه —
    بدونه كان السجلّ يحتفظ بجلساتٍ ماتت منذ أيام ويعرضها كأنها قائمة.

    يُعيد قائمة التوكنات التي حلّت محلّها هذه الجلسة (جلسات **نفس الجهاز**
    الأقدم) كي يُبطلها المُنادي. لماذا: الجهاز الواحد لا يحمل إلا توكناً واحداً
    فعلياً — الدخول الجديد يستبدل القديم في المتصفّح — فبقاء القديم صالحاً على
    الخادم توسيعٌ صامت لسطح الخطر، وصفٌّ ميّتٌ إضافي في القائمة."""
    if not jti:
        return []
    with _LOCK:
        data = _load()
        now = time.time()
        # الجلسات السابقة لنفس الجهاز: تُميَّز بالمعرّف الثابت إن وُجد. ولا
        # نلجأ إلى (UA + IP) بديلاً، لأن جهازين متطابقين خلف نفس الشبكة
        # يتشابهان تماماً — فنطرد جهازاً بريئاً ظنّاً أنه هو نفسه.
        superseded: list[str] = []
        if device_id:
            for k, r in data.items():
                if k != jti and not r.get("revoked") and r.get("device_id") == device_id:
                    r["revoked"] = True
                    r["last_seen"] = now
                    r["superseded"] = True
                    superseded.append(k)
        data[jti] = {
            "jti": jti, "ip": ip or "—", "ua": ua or "",
            "device": describe_device(ua),
            "device_id": device_id or None,
            "created_at": now, "last_seen": now, "revoked": False,
            "expires_at": float(expires_at) if expires_at else None,
        }
        _prune(data)
        _save(force=True)
        return superseded


def _prune(data: dict) -> None:
    """يحذف ما انتهى أجله فعلاً: توكنٌ منتهي الصلاحية، أو جلسةٌ أُنهيت قبل
    أكثر من يوم. السجلّ يجب أن يعرض **ما هو قائمٌ الآن** لا أرشيف دخولٍ
    قديم — قائمةٌ فيها عشرون صفّاً ميتاً تُخفي الصفّ الحيّ الوحيد المهمّ."""
    now = time.time()
    for jti in [k for k, r in data.items() if (
        (r.get("expires_at") and now > float(r["expires_at"]) + 60)
        # جلسةٌ أُنهيت بلا وقت انتهاء معروف: تُحذف بعد يوم. أما المعروفة الأجل
        # فيكفيها الشرط الأول — ويجب أن تبقى في الملفّ حتى ينتهي أجل توكنها،
        # لأن قائمة الإبطال تُستعاد منها بعد إعادة التشغيل. (إخفاؤها من العرض
        # يتمّ في `list_sessions` لا بالحذف.)
        or (r.get("revoked") and not r.get("expires_at")
            and now - float(r.get("last_seen") or 0) > 24 * 3600)
        # صفٌّ قديم بلا وقت انتهاء (سُجّل قبل هذا التحديث): يُحذف بعد يومٍ
        # من آخر نشاط. إبقاؤه شهراً كان يملأ القائمة بصفوفٍ ميتة تُخفي الحيّ.
        or (not r.get("expires_at") and now - float(r.get("last_seen") or 0) > 24 * 3600)
    )]:
        data.pop(jti, None)


def touch(jti: str, ip: str, ua: str, device_id: str | None = None) -> None:
    """يُحدَّث «آخر نشاط» مع كل طلب موثَّق — بلا كتابة قرص في كل مرّة."""
    if not jti:
        return
    with _LOCK:
        data = _load()
        row = data.get(jti)
        if row is None:
            # جلسة صدرت قبل تفعيل التتبّع (أو بعد إعادة تشغيل) — نُثبتها الآن
            # بدل تجاهلها، فلا تبقى جلسة نشطة خارج السجلّ.
            # جلسةٌ صدرت قبل تفعيل التتبّع أو بعد إعادة تشغيل: تُثبَّت الآن
            # وتُوسم «جلسة سابقة» بدل «جهاز غير معروف» — الأولى تفسّر نفسها.
            row = {"jti": jti, "created_at": time.time(), "revoked": False,
                   "device": "جلسة سابقة"}
            data[jti] = row
        row["last_seen"] = time.time()
        row["ip"] = ip or row.get("ip") or "—"
        # جلسةٌ فُتحت قبل هذا التحديث تكتسب معرّف جهازها من أوّل طلبٍ بعده،
        # فتدخل في قاعدة «جلسة واحدة لكل جهاز» بدل أن تبقى خارجها للأبد.
        if device_id and not row.get("device_id"):
            row["device_id"] = device_id
        if ua:
            row["ua"] = ua
            row["device"] = describe_device(ua)
        _save()


def close_session(jti: str) -> None:
    if not jti:
        return
    with _LOCK:
        data = _load()
        if jti in data:
            data[jti]["revoked"] = True
            data[jti]["last_seen"] = time.time()
            _save(force=True)


def list_sessions(active_within_minutes: int = 60, current_jti: str | None = None) -> list[dict]:
    """الجلسات القائمة مرتّبة بالأحدث نشاطاً، والحالية موسومة صراحةً.

    `current` هو أهمّ حقلٍ هنا: بدونه ترى قائمةً متشابهة ولا تعرف أيّها أنت،
    فإمّا تتردّد في إنهاء جلسةٍ غريبة أو تطرد نفسك بالخطأ."""
    with _LOCK:
        data = _load()
        _prune(data)
        _save(force=True)
        now = time.time()
        out = []
        for row in data.values():
            last = float(row.get("last_seen") or 0)
            exp = row.get("expires_at")
            # المُنهاة تُعرض دقائق ليرى المالك تأكيد الإنهاء، ثم تختفي من
            # القائمة (وتبقى في الملفّ لأجل الإبطال). ثمانية صفوفٍ ميتة كانت
            # تُخفي الصفّ الحيّ الوحيد المهمّ.
            if row.get("revoked") and now - last > _REVOKED_GRACE:
                continue
            # جلسةٌ استبدلها دخولٌ جديد من **نفس الجهاز**: لا تُعرض إطلاقاً.
            # عرضها يُقلق بلا سبب — تظنّ أن جهازاً غريباً طُرد للتوّ.
            if row.get("superseded"):
                continue
            out.append({
                "jti": row.get("jti"),
                "device": row.get("device") or "جهاز غير معروف",
                "ip": row.get("ip") or "—",
                "created_at": int(row.get("created_at") or 0),
                "last_seen": int(last),
                "expires_at": int(exp) if exp else None,
                "revoked": bool(row.get("revoked")),
                "current": bool(current_jti and row.get("jti") == current_jti),
                "active": (not row.get("revoked")) and (now - last) <= active_within_minutes * 60,
            })
        # الجلسة الحالية أوّلاً دائماً، ثم الأحدث نشاطاً.
        out.sort(key=lambda r: (not r["current"], -r["last_seen"]))
        return out


def close_others(keep_jti: str) -> list[str]:
    """إنهاء كل الجلسات عدا الحالية — الفعل الذي يحتاجه المالك فعلاً حين يشكّ:
    يطرد الأجهزة الأخرى ولا يطرد نفسه، فلا يفقد شاشته وهو يعالج تسرّباً."""
    with _LOCK:
        data = _load()
        closed = []
        for jti, row in data.items():
            if jti != keep_jti and not row.get("revoked"):
                row["revoked"] = True
                row["last_seen"] = time.time()
                closed.append(jti)
        _save(force=True)
        return closed


def clear_all() -> None:
    with _LOCK:
        globals()["_cache"] = {}
        _save(force=True)
