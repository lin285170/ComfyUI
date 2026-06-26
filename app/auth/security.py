import secrets

import bcrypt
from aiohttp import web

COOKIE_NAME = "comfyui_session"


def hash_password(plaintext: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))


def generate_session_token() -> str:
    return secrets.token_hex(64)


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def set_session_cookie(response: web.Response, token: str, timeout_hours: int, secure: bool) -> None:
    response.set_cookie(
        COOKIE_NAME, token,
        httponly=True,
        secure=secure,
        samesite="Strict",
        max_age=timeout_hours * 3600,
        path="/",
    )


def clear_session_cookie(response: web.Response) -> None:
    response.del_cookie(COOKIE_NAME, path="/")


def get_session_token(request: web.Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)