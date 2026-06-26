from aiohttp import web

from app.auth.config import AuthConfig
from app.auth.session_manager import validate_session

EXEMPT_PATHS = {
    "/login",
    "/auth/login",
    "/api/auth/login",
    "/auth/logout",
    "/api/auth/logout",
    "/auth/captcha",
    "/api/auth/captcha",
    "/auth/status",
    "/api/auth/status",
}

EXEMPT_PREFIXES = (
    "/extensions/",
    "/templates/",
    "/docs/",
)

STATIC_EXTENSIONS = frozenset({
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".json",
    ".webp", ".avif", ".mp4", ".webm",
})


def _is_static_asset(path: str) -> bool:
    _, _, ext = path.rpartition(".")
    return f".{ext}".lower() in STATIC_EXTENSIONS if ext else False


LOGOUT_BUTTON_HTML = (
    "<style>"
    "#comfyui-logout-btn{position:fixed;top:10px;right:10px;z-index:99999;"
    "background:#e74c3c;color:#fff;border:none;padding:6px 14px;border-radius:4px;"
    "cursor:pointer;font-size:13px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
    "opacity:0.7;transition:opacity 0.2s}"
    "#comfyui-logout-btn:hover{opacity:1}"
    "</style>"
    "<button id='comfyui-logout-btn' onclick=\""
    "fetch('/auth/logout',{method:'POST',credentials:'same-origin'}).then(function(){location.href='/login'})"
    "\">Logout</button>"
)


def _inject_logout_button(response: web.StreamResponse) -> web.StreamResponse:
    content_type = response.content_type or ""
    if "text/html" not in content_type:
        return response

    body = None
    if hasattr(response, "body") and response.body is not None:
        body = response.body
    elif isinstance(response, web.FileResponse):
        try:
            with open(response._path, "rb") as f:
                body = f.read()
        except (OSError, AttributeError):
            return response

    if body is None:
        return response

    body_str = body.decode("utf-8", errors="replace")
    if "</body>" in body_str:
        body_str = body_str.replace("</body>", LOGOUT_BUTTON_HTML + "</body>")
        new_response = web.Response(body=body_str.encode("utf-8"), content_type=content_type)
        for key, value in response.headers.items():
            if key.lower() not in ("content-length", "content-type"):
                new_response.headers[key] = value
        return new_response

    return response


def create_auth_middleware(config: AuthConfig):
    if not config.enabled:
        @web.middleware
        async def noop_middleware(request: web.Request, handler):
            return await handler(request)
        return noop_middleware

    @web.middleware
    async def auth_middleware(request: web.Request, handler):
        path = request.path

        if path in EXEMPT_PATHS:
            return await handler(request)

        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await handler(request)

        if _is_static_asset(path):
            return await handler(request)

        user_id = validate_session(request)
        if user_id is not None:
            request["auth_user_id"] = user_id
            response = await handler(request)
            return _inject_logout_button(response)

        accept = request.headers.get("Accept", "")
        if "text/html" in accept or path == "/":
            return web.HTTPFound("/login")

        return web.json_response({"error": "Unauthorized", "detail": "Authentication required"}, status=401)

    return auth_middleware