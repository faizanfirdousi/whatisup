from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Owner(Base):
    """v0 stand-in for 'user'. No password, no OAuth fields yet.
    In v1 this gains github_oauth_id and a real session, but PK and FKs stay the same."""

    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    github_username: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_email: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    connections = relationship("Connection", back_populates="owner", lazy="selectin")
