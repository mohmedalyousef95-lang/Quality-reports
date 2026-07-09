from fastapi import Request, HTTPException, status
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import APP_PASSWORD, SECRET_KEY, AUTH_DISABLED

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="quality-reports-auth")


def check_password(password: str) -> bool:
    return password == APP_PASSWORD


def create_session_token() -> str:
    return _serializer.dumps({"authenticated": True})


def verify_session_token(token: str) -> bool:
    try:
        data = _serializer.loads(token, max_age=MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return bool(data.get("authenticated"))


def require_auth(request: Request) -> None:
    if AUTH_DISABLED:
        return
    token = request.cookies.get(COOKIE_NAME)
    if not token or not verify_session_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="غير مصرح"
        )
