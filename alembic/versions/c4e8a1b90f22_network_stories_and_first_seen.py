"""network stories + person_technologies.first_seen_at

Revision ID: c4e8a1b90f22
Revises: 6c03835e01a0
Create Date: 2026-09-02 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4e8a1b90f22"
down_revision: Union[str, Sequence[str], None] = "6c03835e01a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "person_technologies",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE person_technologies SET first_seen_at = last_seen_at WHERE first_seen_at IS NULL")

    op.create_table(
        "network_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("owner_id", "week_start", name="uq_network_stories_owner_week"),
    )


def downgrade() -> None:
    op.drop_table("network_stories")
    op.drop_column("person_technologies", "first_seen_at")
