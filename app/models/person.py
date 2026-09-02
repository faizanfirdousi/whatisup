from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Person(Base):
    """Tracked GitHub identity. Global — shared across owners.
    Two owners tracking the same person share one row (and one set of events/insights)."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    github_username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    events_etag: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    connections = relationship("Connection", back_populates="person", lazy="noload")
    activity_events = relationship("ActivityEvent", back_populates="person", lazy="noload")
    insights = relationship("Insight", back_populates="person", lazy="noload")
