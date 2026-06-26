from dataclasses import dataclass
from comfy.cli_args import args


@dataclass
class AuthConfig:
    enabled: bool = False
    username: str | None = None
    password_hash: str | None = None
    max_failed_attempts: int = 5
    lockout_minutes: int = 15
    session_timeout_hours: int = 24
    rate_limit_count: int = 10
    rate_limit_window: int = 60

    @classmethod
    def from_args(cls) -> "AuthConfig":
        return cls(
            enabled=args.enable_auth,
            username=args.auth_username,
            max_failed_attempts=args.auth_max_failed_attempts,
            lockout_minutes=args.auth_lockout_minutes,
            session_timeout_hours=args.auth_session_timeout_hours,
            rate_limit_count=args.auth_rate_limit_count,
        )