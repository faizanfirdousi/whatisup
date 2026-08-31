from datetime import date, datetime
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class DigestDelivery(Base):
    """Audit log of what was actually sent/displayed."""

    __tablename__ = "digest_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("owners.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_method: Mapped[str] = mapped_column(String, nullable=False)  # 'web' | 'console'
    status: Mapped[str] = mapped_column(String, nullable=False)  # 'sent' | 'failed'
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
