import logging
import uuid

from aiohttp import web

from app.auth.captcha import (
    cleanup_expired_captchas,
    generate_captcha_image,
    generate_captcha_text,
    store_captcha,
    verify_captcha,
)
from app.auth.config import AuthConfig
from app.auth.login_page import LOGIN_PAGE_HTML
from app.auth.models import User
from app.auth.rate_limiter import check_rate_limit, clear_failed_attempts, is_account_locked, record_failed_attempt
from app.auth.security import (
    clear_session_cookie,
    generate_csrf_token,
    set_session_cookie,
    verify_password,
)
from app.auth.session_manager import create_session, delete_session, validate_session
from app.database.db import create_session as db_session

logger = logging.getLogger(__name__)


class AuthRoutes:
    def __init__(self, config: AuthConfig):
        self.config = config

    def register(self, app: web.Application) -> None:
        app.router.add_get("/login", self._login_page)
        app.router.add_post("/auth/login", self._login)
        app.router.add_post("/api/auth/login", self._login)
        app.router.add_post("/auth/logout", self._logout)
        app.router.add_post("/api/auth/logout", self._logout)
        app.router.add_get("/auth/logout", self._logout_page)
        app.router.add_get("/api/auth/logout", self._logout_page)
        app.router.add_get("/auth/captcha", self._captcha_image)
        app.router.add_get("/api/auth/captcha", self._captcha_image)
        app.router.add_get("/auth/status", self._auth_status)
        app.router.add_get("/api/auth/status", self._auth_status)

    async def _login_page(self, request: web.Request) -> web.Response:
        if validate_session(request) is not None:
            raise web.HTTPFound("/")
        csrf_token = generate_csrf_token()
        html = LOGIN_PAGE_HTML.replace("{{CSRF_TOKEN}}", csrf_token)
        response = web.Response(text=html, content_type="text/html")
        response.set_cookie("csrf_token", csrf_token, httponly=False, samesite="Strict", path="/auth/")
        return response

    async def _login(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        username = data.get("username", "").strip()
        password = data.get("password", "")
        captcha_id = data.get("captcha_id", "")
        captcha_answer = data.get("captcha_answer", "").strip()
        csrf_token = data.get("csrf_token", "")

        cookie_csrf = request.cookies.get("csrf_token", "")
        if not csrf_token or not cookie_csrf or csrf_token != cookie_csrf:
            return web.json_response({"error": "Invalid CSRF token"}, status=403)

        ip = request.remote

        allowed, rate_msg = check_rate_limit(ip, self.config)
        if not allowed:
            return web.json_response({"error": rate_msg}, status=429)

        if not verify_captcha(captcha_id, captcha_answer):
            record_failed_attempt(username or "unknown", ip, self.config)
            return web.json_response({"error": "Invalid CAPTCHA. Please try again."}, status=400)

        locked, lock_msg = is_account_locked(username)
        if locked:
            return web.json_response({"error": lock_msg}, status=423)

        try:
            with db_session() as db:
                user = db.query(User).filter(User.username == username).first()
                if user is None or not verify_password(password, user.password_hash):
                    record_failed_attempt(username, ip, self.config)
                    return web.json_response({"error": "Invalid username or password"}, status=401)

                clear_failed_attempts(username)
                session_token = create_session(request, user.id, self.config.session_timeout_hours)
        except Exception as e:
            logger.error("Login error: %s", e, exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

        response = web.json_response({"success": True, "redirect": "/"})
        is_secure = request.url.scheme == "https"
        set_session_cookie(response, session_token, self.config.session_timeout_hours, is_secure)
        return response

    async def _logout(self, request: web.Request) -> web.Response:
        delete_session(request)
        response = web.json_response({"success": True})
        clear_session_cookie(response)
        return response

    async def _logout_page(self, request: web.Request) -> web.Response:
        delete_session(request)
        response = web.HTTPFound("/login")
        clear_session_cookie(response)
        return response

    async def _captcha_image(self, request: web.Request) -> web.Response:
        cleanup_expired_captchas()
        captcha_id = uuid.uuid4().hex
        text = generate_captcha_text()
        store_captcha(captcha_id, text)
        image_data = generate_captcha_image(text)
        return web.Response(
            body=image_data,
            content_type="image/png",
            headers={"X-Captcha-Id": captcha_id, "Cache-Control": "no-store"},
        )

    async def _auth_status(self, request: web.Request) -> web.Response:
        user_id = validate_session(request)
        if user_id is not None:
            return web.json_response({"authenticated": True, "username": self.config.username})
        return web.json_response({"authenticated": False})