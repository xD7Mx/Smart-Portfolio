"""
Single-owner auth: the site is public read-only (anyone can view the
portfolio, market data, etc.) but only the owner — who holds the one shared
APP_PASSWORD — can change anything. `require_auth` lets every GET through
unconditionally and only checks the JWT on state-changing requests
(POST/PUT/PATCH/DELETE), so a valid token is the difference between "can
look" and "can control".
"""
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


# ── Password override (changeable from the UI) ───────────────────
# The owner can change the password from Settings → الأمان. We DON'T rewrite
# the plaintext .env (not mounted into the container, and plaintext is worse):
# instead we persist a salted PBKDF2 hash in the app's writable data dir. It
# takes effect immediately (no restart) and survives restarts, for BOTH copies.
# When no override exists yet, we fall back to APP_PASSWORD from .env.
import hashlib
import json
import os

_PWD_PATH = "/app/data/auth.json" if os.path.isdir("/app/data") else os.path.join(os.getcwd(), "auth.json")
_PBKDF2_ROUNDS = 200_000


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS).hex()


def _load_override() -> dict | None:
    try:
        with open(_PWD_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if d.get("hash") and d.get("salt") else None
    except Exception:
        return None


def set_password(new_password: str) -> bool:
    """Persist a new owner password (salted hash). Immediate effect.

    **ويُبطل كل الجلسات القائمة.** ثغرة كانت قائمة: تغيير كلمة المرور لم يكن
    يمسّ التوكنات الصادرة سلفاً، فمن بيده توكن مسرَّب يبقى داخلاً إلى أن ينتهي
    أجله — أي أن تغيير كلمة المرور لا يطرده. الآن يُقلب حقبة التوكنات معه،
    فيسقط كل توكن قديم فوراً وتظهر شاشة القفل على كل نسخة."""
    salt = secrets.token_hex(16)
    data = {"salt": salt, "hash": _hash_password(new_password, salt)}
    try:
        os.makedirs(os.path.dirname(_PWD_PATH), exist_ok=True)
        with open(_PWD_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        bump_token_epoch()
        return True
    except Exception:
        return False


def verify_password(password: str) -> bool:
    ov = _load_override()
    if ov:
        # constant-time compare of the derived hashes
        return secrets.compare_digest(_hash_password(password, ov["salt"]), ov["hash"])
    # constant-time compare — avoids leaking password length/prefix via timing
    return secrets.compare_digest(password, settings.APP_PASSWORD)


# ── Login rate-limiting ──────────────────────────────────────────
# In-memory per-client-IP tracker — this is a single-process personal app,
# not a distributed service, so no shared store is needed. Not foolproof
# behind a proxy that doesn't forward the real client IP, but it stops the
# common case of unlimited scripted password guesses.
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 5 * 60
_login_attempts: dict[str, list[float]] = defaultdict(list)


def check_login_rate_limit(client_ip: str) -> None:
    now = time.time()
    recent = [t for t in _login_attempts[client_ip] if now - t < LOGIN_WINDOW_SECONDS]
    _login_attempts[client_ip] = recent
    if len(recent) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"محاولات كثيرة جداً — حاول مرة أخرى بعد {LOGIN_WINDOW_SECONDS // 60} دقائق",
        )


def record_login_failure(client_ip: str) -> None:
    _login_attempts[client_ip].append(time.time())


def clear_login_attempts(client_ip: str) -> None:
    _login_attempts.pop(client_ip, None)


# ── Token issuance + real revocation on logout ───────────────────
# Each token gets a unique jti; logout adds it to an in-memory revoked set
# instead of just deleting the token client-side, so a captured/leaked
# token can actually be killed rather than staying valid until it expires.
_revoked_jti: dict[str, float] = {}  # jti -> expiry timestamp, for pruning


# ── حقبة التوكنات (Token epoch) — إبطال شامل بضغطة واحدة ─────────
# المشكلة التي تحلّها: إبطال التوكن الواحد (jti) لا يكفي حين يتسرّب الرابط أو
# كلمة المرور — عندها تريد إسقاط **كل** ما صدر سلفاً دفعةً واحدة، بلا معرفة
# بمن يحمل ماذا. كل توكن يحمل رقم الحقبة التي صدر فيها؛ ورفع الرقم يُبطل كل
# ما سبقه في اللحظة نفسها، فتظهر شاشة القفل على كل نسخة مفتوحة.
#
# الحقبة تُخزَّن على القرص (تصمد عبر إعادة التشغيل) وتُرفع في حالتين **فقط**:
#   • تغيير كلمة المرور   → لا يبقى توكن قديم بعد تغييرها
#   • طلب صريح من المالك  → «إنهاء كل الجلسات» من الإعدادات
#
# وكانت تُرفع أيضاً مع كل إقلاع، فيطرد كلُّ تحديثٍ للحزمة كلَّ الأجهزة ويطالب
# المالك بكلمة المرور من جديد. والإقلاع ليس حدثاً أمنياً: لم تتسرّب كلمة ولا
# طُلب إنهاء، وإنما أُعيد تشغيل الخدمة. فربطُ الإبطال به يجعل التحديث الروتيني
# يُقرأ كاختراق، ويُعوّد المالك على إدخال كلمته مراراً بلا سبب — وذلك بذاته
# إضعافٌ للأمان لا تعزيزٌ له.
_EPOCH_PATH = os.path.join(os.path.dirname(_PWD_PATH), "token_epoch.json")


def _read_epoch() -> int:
    try:
        with open(_EPOCH_PATH, encoding="utf-8") as f:
            return int(json.load(f).get("epoch") or 0)
    except Exception:
        return 0


def _write_epoch(value: int) -> None:
    try:
        os.makedirs(os.path.dirname(_EPOCH_PATH), exist_ok=True)
        with open(_EPOCH_PATH, "w", encoding="utf-8") as f:
            json.dump({"epoch": value, "at": int(time.time())}, f)
    except Exception:
        pass


def bump_token_epoch() -> int:
    """يرفع الحقبة → تسقط كل التوكنات الصادرة قبل هذه اللحظة."""
    global _EPOCH
    _EPOCH = _read_epoch() + 1
    _write_epoch(_EPOCH)
    # السجلّ يجب أن يطابق الواقع: لم تبقَ جلسة صالحة واحدة.
    try:
        from app.core import sessions
        sessions.clear_all()
    except Exception:
        pass
    return _EPOCH


def current_token_epoch() -> int:
    return _EPOCH


# الحقبة تُقرأ كما هي عند الإقلاع — لا تُرفع. فتبقى الجلسات القائمة صالحة عبر
# إعادة التشغيل والتحديث، ولا يسقطها إلا تغيير كلمة المرور أو إنهاءٌ صريح.
_EPOCH = _read_epoch()


def _prune_revoked() -> None:
    now = time.time()
    expired = [j for j, exp in _revoked_jti.items() if exp < now]
    for j in expired:
        _revoked_jti.pop(j, None)


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": "owner", "jti": uuid.uuid4().hex, "exp": expire, "ep": _EPOCH},
        settings.JWT_SECRET, algorithm=ALGORITHM,
    )


def revoke_token(token: str) -> None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        _prune_revoked()
        _revoked_jti[jti] = exp
        try:
            from app.core import sessions
            sessions.close_session(jti)
        except Exception:
            pass


_revoked_restored = False


def _restore_revoked_once() -> None:
    """تُقرأ الجلسات المُنهاة من القرص عند أوّل فحصٍ بعد الإقلاع.

    قائمة الإبطال هنا في الذاكرة، والحقبة لا تُرفع عند الإقلاع كي تبقى الجلسات
    القائمة صالحة عبر التحديث — فبدون هذه القراءة كانت إعادة تشغيل الخادم
    **تُحيي** توكناً أنهيتَه: تُنهي جلسة جهازٍ مسروق فتعود تعمل بعد أول تحديث."""
    global _revoked_restored
    if _revoked_restored:
        return
    _revoked_restored = True
    try:
        from app.core import sessions
        sessions._load()          # يستدعي داخلَه إعادة تعبئة قائمة الإبطال
    except Exception:
        pass


def _decode_and_check_revocation(token: str) -> None:
    _restore_revoked_once()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    if payload.get("jti") in _revoked_jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session has been logged out")
    # حقبة أقدم من الحالية ⇒ توكن صادر قبل آخر إبطال شامل (إقلاع/تغيير كلمة
    # المرور/إنهاء الجلسات). لا يُقبل مهما بقي من أجله.
    if int(payload.get("ep") or 0) != _EPOCH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired — please sign in again")


def client_ip(request: Request) -> str:
    """أقرب ما نستطيع لعنوان العميل. خلف وسيط (Nginx/Cloudflare) يصل العنوان
    في X-Forwarded-For؛ أوّل قيمة فيه هي العميل الأصلي. بلا وسيط يُمرَّر
    العنوان مباشرةً. ملاحظة صدق: هذه الترويسة قابلة للتزوير من العميل، فهي
    دليلٌ استرشادي لا إثبات."""
    fwd = request.headers.get("x-forwarded-for") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    return getattr(request.client, "host", None) or "—"


def _track(request: Request, token: str) -> None:
    """تحديث سجلّ الجلسة — لا يُفشل الطلب أبداً مهما حدث فيه."""
    try:
        from app.core import sessions
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        sessions.touch(payload.get("jti") or "", client_ip(request),
                       request.headers.get("user-agent") or "",
                       device_id=(request.headers.get("x-device-id") or "").strip()[:64] or None)
    except Exception:
        pass


async def require_auth(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    # قفل كامل (بقرار المالك): لا قراءة ولا كتابة بلا توكن صالح — الموقع
    # لا يُرى إطلاقاً بدون كلمة المرور. (سابقاً كانت طلبات GET عامة للقراءة.)
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    _decode_and_check_revocation(creds.credentials)
    _track(request, creds.credentials)


async def require_owner(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    """Unlike require_auth, this checks the token on EVERY request regardless
    of HTTP method — for the rare endpoint too sensitive to expose as a
    public GET (a full data-export download is a bigger leak than any single
    read screen, even though it's technically a GET)."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    _decode_and_check_revocation(creds.credentials)
