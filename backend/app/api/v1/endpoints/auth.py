import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.auth import (
    check_login_rate_limit, clear_login_attempts, create_access_token,
    record_login_failure, revoke_token, verify_password, set_password,
    require_owner, bump_token_epoch, current_token_epoch,
)
from app.core.response import success_response

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def _client_ip(request: Request) -> str:
    # خلف وسيط، العنوان الحقيقي في X-Forwarded-For لا في request.client.
    fwd = request.headers.get("x-forwarded-for") or ""
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def login(data: LoginRequest, request: Request):
    ip = _client_ip(request)
    check_login_rate_limit(ip)
    if not verify_password(data.password):
        record_login_failure(ip)
        raise HTTPException(401, "Incorrect password")
    clear_login_attempts(ip)
    token = create_access_token()
    # تسجيل الجلسة: بصمة التوكن + الجهاز + العنوان — أساس شاشة «الجلسات النشطة».
    try:
        from jose import jwt as _jwt
        from app.core.auth import ALGORITHM as _ALG
        from app.core.config import settings as _st
        from app.core import sessions as _sess
        _payload = _jwt.decode(token, _st.JWT_SECRET, algorithms=[_ALG])
        old = _sess.open_session(
            _payload.get("jti"), ip, request.headers.get("user-agent") or "",
            expires_at=_payload.get("exp"),
            device_id=(request.headers.get("x-device-id") or "").strip()[:64] or None,
        )
        # جلسات نفس الجهاز الأقدم تُبطَل فعلياً لا شكلاً: توكنٌ لم يعد أحدٌ
        # يستعمله يجب ألا يبقى مقبولاً على الخادم.
        from app.core.auth import _revoked_jti
        for _j in old or []:
            _revoked_jti[_j] = float(_payload.get("exp") or 0) or (time.time() + 86400)
    except Exception:
        pass
    return success_response(data={"access_token": token, "token_type": "bearer"})


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, _: None = Depends(require_owner)):
    """تغيير كلمة مرور المالك — يتحقّق من الحالية ثم يحفظ الجديدة (مُجزّأة) فوراً."""
    if not verify_password(data.current_password):
        raise HTTPException(401, "كلمة المرور الحالية غير صحيحة")
    if len(data.new_password) < 4:
        raise HTTPException(400, "كلمة المرور الجديدة قصيرة جداً")
    if not set_password(data.new_password):
        raise HTTPException(500, "تعذّر حفظ كلمة المرور — حاول مرة أخرى")
    return success_response(message="تم تغيير كلمة المرور بنجاح.")


@router.post("/logout")
async def logout(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """Actually invalidates the token server-side (adds it to the revoked
    set) instead of relying only on the client deleting it — so a
    previously-issued token can't keep working after logout."""
    if creds is not None:
        revoke_token(creds.credentials)
    return success_response(message="Logged out.")


@router.post("/revoke-all", dependencies=[Depends(require_owner)])
async def revoke_all_sessions():
    """إنهاء **كل** الجلسات على كل الأجهزة فوراً — بما فيها جلستك الحالية.

    الأداة المقصودة عند تسرّب الرابط أو كلمة المرور: لا تحتاج معرفة من يحمل
    توكناً ولا من أي جهاز — رفعُ الحقبة يُسقط كل ما صدر قبل هذه اللحظة، فتظهر
    شاشة القفل على كل نسخة مفتوحة في الحال. الدخول بعدها بكلمة المرور فقط."""
    ep = bump_token_epoch()
    return success_response(data={"epoch": ep}, message="أُنهيت كل الجلسات — يلزم تسجيل الدخول من جديد.")


@router.post("/sessions/revoke-others", dependencies=[Depends(require_owner)])
async def revoke_other_sessions(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """إنهاء كل الجلسات **عدا جلستك** — الفعل المطلوب عند الشكّ: تطرد الأجهزة
    الأخرى وتبقى أنت داخل التطبيق. أما «إنهاء الكل» فيطردك معها."""
    from app.core.auth import _revoked_jti, _prune_revoked
    from app.core import sessions
    keep = _jti_of(creds)
    _prune_revoked()
    closed = sessions.close_others(keep or "")
    for jti in closed:
        _revoked_jti[jti] = time.time() + 60 * 60 * 24 * 30
    return success_response(data={"closed": len(closed)},
                            message=f"أُنهيت {len(closed)} جلسة أخرى — جلستك الحالية باقية.")


@router.get("/session-info", dependencies=[Depends(require_owner)])
async def session_info():
    """معلومات الجلسة الحالية — رقم الحقبة النافذة (لتشخيص الإبطال الشامل)."""
    return success_response(data={"epoch": current_token_epoch()})


def _jti_of(creds) -> str | None:
    """بصمة توكن الطالب — بها نُميّز «هذا الجهاز» في القائمة."""
    if creds is None:
        return None
    try:
        from jose import jwt as _jwt
        from app.core.config import settings as _st
        from app.core.auth import ALGORITHM as _ALG
        return _jwt.decode(creds.credentials, _st.JWT_SECRET, algorithms=[_ALG]).get("jti")
    except Exception:
        return None


@router.get("/sessions", dependencies=[Depends(require_owner)])
async def list_sessions(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """الجلسات المسجَّلة: الجهاز · العنوان · الدخول · آخر نشاط.

    حدود ما نعرفه، بصراحة: وصف الجهاز مستنبَط من ترويسة User-Agent وهي قابلة
    للانتحال؛ والعنوان قد يكون عنوان وسيط لا عنوان المستخدم. كلاهما دليلٌ
    استرشادي لا إثبات هوية."""
    from app.core import sessions
    return success_response(data=sessions.list_sessions(current_jti=_jti_of(creds)))


@router.post("/sessions/{jti}/revoke", dependencies=[Depends(require_owner)])
async def revoke_session(jti: str):
    """إنهاء جلسة بعينها — يسقط توكنها فوراً دون المساس ببقية الأجهزة."""
    from app.core.auth import _revoked_jti, _prune_revoked
    from app.core import sessions
    _prune_revoked()
    _revoked_jti[jti] = time.time() + 60 * 60 * 24 * 30
    sessions.close_session(jti)
    return success_response(message="أُنهيت الجلسة.")
