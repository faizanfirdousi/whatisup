from datetime import date, datetime
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Insight(Base):
    """One LLM-generated narrative per person per week. Global, reused across owners."""

    __tablename__ = "insights"
    __table_args__ = (UniqueConstraint("person_id", "week_start"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("people.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_event_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    significance_total: Mapped[int] = mapped_column(Integer, nullable=False)
    model_used: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    person = relationship("Person", back_populates="insights")
