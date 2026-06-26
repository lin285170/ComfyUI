import logging
from datetime import datetime, timedelta, timezone

from aiohttp import web

from app.auth.models import Session, _utc_now
from app.auth.security import generate_session_token, get_session_token
from app.database.db import create_session as db_session

logger = logging.getLogger(__name__)


def create_session(request: web.Request, user_id: int, timeout_hours: int) -> str:
    token = generate_session_token()
    now = _utc_now()
    expires = now + timedelta(hours=timeout_hours)
    ip = request.remote

    with db_session() as db:
        db.query(Session).filter(Session.user_id == user_id).delete()
        session = Session(
            token=token,
            user_id=user_id,
            expires_at=expires,
            user_agent=request.headers.get("User-Agent", ""),
            ip_address=ip,
        )
        db.add(session)
        db.commit()
    return token


def validate_session(request: web.Request) -> int | None:
    token = get_session_token(request)
    if not token:
        return None
    try:
        with db_session() as db:
            session = db.query(Session).filter(Session.token == token).first()
            if session is None:
                return None
            if session.expires_at <= _utc_now():
                db.delete(session)
                db.commit()
                return None
            return session.user_id
    except Exception:
        logger.error("Session validation error", exc_info=True)
        return None


def delete_session(request: web.Request) -> None:
    token = get_session_token(request)
    if token:
        try:
            with db_session() as db:
                db.query(Session).filter(Session.token == token).delete()
                db.commit()
        except Exception:
            logger.error("Session deletion error", exc_info=True)


def cleanup_expired_sessions() -> None:
    try:
        with db_session() as db:
            db.query(Session).filter(Session.expires_at <= _utc_now()).delete()
            db.commit()
    except Exception:
        logger.warning("Session cleanup failed", exc_info=True)