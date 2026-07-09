from fastapi import APIRouter, HTTPException, Response, Request

from ..auth import (
    check_password,
    create_session_token,
    verify_session_token,
    COOKIE_NAME,
    MAX_AGE_SECONDS,
)
from ..schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if not check_password(payload.password):
        raise HTTPException(401, "كلمة المرور غير صحيحة")
    token = create_session_token()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/status")
def auth_status(request: Request):
    from ..config import AUTH_DISABLED

    if AUTH_DISABLED:
        return {"authenticated": True}
    token = request.cookies.get(COOKIE_NAME)
    authenticated = bool(token and verify_session_token(token))
    return {"authenticated": authenticated}
