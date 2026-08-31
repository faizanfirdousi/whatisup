from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Technology(Base):
    """Normalized technology name (lowercase)."""

    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class PersonTechnology(Base):
    """Rule-derived tech profile per person."""

    __tablename__ = "person_technologies"

    person_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("people.id"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("technologies.id"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
