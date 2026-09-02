"""Index activity events for digest queries

Revision ID: e4b7c9d1a2f0
Revises: d8f2c1a4e9b0
Create Date: 2026-09-02 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e4b7c9d1a2f0"
down_revision: Union[str, Sequence[str], None] = "d8f2c1a4e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_activity_events_person_occurred",
        "activity_events",
        ["person_id", "occurred_at"],
    )
    op.create_index(
        "ix_activity_events_person_type_occurred",
        "activity_events",
        ["person_id", "event_type", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_events_person_type_occurred", table_name="activity_events")
    op.drop_index("ix_activity_events_person_occurred", table_name="activity_events")
