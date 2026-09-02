"""add auth_sessions table

Revision ID: d8f2c1a4e9b0
Revises: c4e8a1b90f22
Create Date: 2026-09-02 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8f2c1a4e9b0"
down_revision: Union[str, Sequence[str], None] = "c4e8a1b90f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_owner_id", "auth_sessions", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_owner_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
