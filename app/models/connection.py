from datetime import datetime
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Connection(Base):
    """Owner <-> Person many-to-many, with close-circle flag."""

    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("owner_id", "person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("owners.id"), nullable=False)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("people.id"), nullable=False)
    is_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    owner = relationship("Owner", back_populates="connections")
    person = relationship("Person", back_populates="connections")
