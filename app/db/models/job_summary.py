from __future__ import annotations
import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.job import Job


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_spend_inr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_spend_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    top_merchants: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narrative: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="summary")
