import logging
import time
from datetime import timedelta

from app.auth.config import AuthConfig
from app.auth.models import FailedAttempt, User, _utc_now
from app.database.db import create_session as db_session

logger = logging.getLogger(__name__)

_memory_rate_limit: dict[str, list[float]] = {}
_cleanup_counter = 0


def _cleanup_ip_entry(ip: str, now: float, window: int) -> None:
    if ip in _memory_rate_limit:
        _memory_rate_limit[ip] = [t for t in _memory_rate_limit[ip] if now - t < window]
        if not _memory_rate_limit[ip]:
            del _memory_rate_limit[ip]


def _full_cleanup(now: float, window: int) -> None:
    for ip in list(_memory_rate_limit.keys()):
        _memory_rate_limit[ip] = [t for t in _memory_rate_limit[ip] if now - t < window]
        if not _memory_rate_limit[ip]:
            del _memory_rate_limit[ip]


def check_rate_limit(ip_address: str, config: AuthConfig) -> tuple[bool, str | None]:
    global _cleanup_counter
    now = time.time()
    _cleanup_counter += 1
    if _cleanup_counter >= 100:
        _full_cleanup(now, config.rate_limit_window)
        _cleanup_counter = 0
    else:
        _cleanup_ip_entry(ip_address, now, config.rate_limit_window)
    attempts = _memory_rate_limit.get(ip_address, [])
    if len(attempts) >= config.rate_limit_count:
        wait_time = int(config.rate_limit_window - (now - attempts[0]))
        return False, f"Too many login attempts. Please wait {wait_time} seconds."
    return True, None


def record_failed_attempt(username: str, ip_address: str, config: AuthConfig) -> None:
    now = time.time()
    _memory_rate_limit.setdefault(ip_address, []).append(now)
    _cleanup_ip_entry(ip_address, now, config.rate_limit_window)

    try:
        with db_session() as db:
            db.add(FailedAttempt(username=username, ip_address=ip_address))
            db.commit()

            cutoff = _utc_now() - timedelta(minutes=config.lockout_minutes)
            count = (
                db.query(FailedAttempt)
                .filter(
                    FailedAttempt.username == username,
                    FailedAttempt.attempted_at >= cutoff,
                )
                .count()
            )
            if count >= config.max_failed_attempts:
                user = db.query(User).filter(User.username == username).first()
                if user:
                    user.locked_until = _utc_now() + timedelta(minutes=config.lockout_minutes)
                    db.commit()
                    logger.warning("Account '%s' locked until %s", username, user.locked_until)
    except Exception:
        logger.error("Failed to persist failed attempt", exc_info=True)


def is_account_locked(username: str) -> tuple[bool, str | None]:
    try:
        with db_session() as db:
            user = db.query(User).filter(User.username == username).first()
            if user and user.locked_until:
                now = _utc_now()
                if user.locked_until > now:
                    remaining = int((user.locked_until - now).total_seconds() / 60) + 1
                    return True, f"Account locked. Try again in {remaining} minutes."
                else:
                    user.locked_until = None
                    db.commit()
    except Exception:
        logger.error("Failed to check account lock status", exc_info=True)
    return False, None


def clear_failed_attempts(username: str) -> None:
    try:
        with db_session() as db:
            db.query(FailedAttempt).filter(FailedAttempt.username == username).delete()
            db.commit()
    except Exception:
        logger.error("Failed to clear failed attempts", exc_info=True)