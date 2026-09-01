from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class PipelineRun(Base):
    """Audit log for pipeline executions. Also serves as a global lock."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    phase: Mapped[str] = mapped_column(String, nullable=False)  # 'collect' | 'narrate' | 'all'
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="running"
    )  # 'running' | 'ok' | 'error'
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    people_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
