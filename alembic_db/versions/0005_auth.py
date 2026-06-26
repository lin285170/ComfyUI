"""
Create auth tables: auth_users, auth_sessions, auth_failed_attempts.

Revision ID: 0005_auth
Revises: 0004_drop_tag_type
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0005_auth"
down_revision: Union[str, None] = "0004_drop_tag_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(256), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auth_users_username", "auth_users", ["username"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_auth_sessions_token", "auth_sessions", ["token"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "auth_failed_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(256), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_auth_failed_attempts_ip_at", "auth_failed_attempts", ["ip_address", "attempted_at"])
    op.create_index("ix_auth_failed_attempts_user_at", "auth_failed_attempts", ["username", "attempted_at"])


def downgrade() -> None:
    op.drop_table("auth_failed_attempts")
    op.drop_table("auth_sessions")
    op.drop_table("auth_users")