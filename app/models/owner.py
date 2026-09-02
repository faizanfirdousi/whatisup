from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, func, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Owner(Base):
    """A user of the WhatIsUp application."""

    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    github_username: Mapped[str | None] = mapped_column(String, nullable=True)
    github_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_scopes: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_email: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builder: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Self-referential link to their own Person profile
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), nullable=True)
    
    # In Phase 3:
    highlights_acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collect_in_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships — noload so GET /api/me does not pull the whole network
    connections = relationship("Connection", back_populates="owner", lazy="noload")
