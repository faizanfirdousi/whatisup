from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class ActivityEvent(Base):
    """Normalized activity event from GitHub. Global per person."""

    __tablename__ = "activity_events"
    __table_args__ = (UniqueConstraint("source", "external_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("people.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="github")
    external_event_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    repo_full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, deferred=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    significance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    person = relationship("Person", back_populates="activity_events")
