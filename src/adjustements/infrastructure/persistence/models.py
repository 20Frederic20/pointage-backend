from adjustements.domain import AnomalyType, AnomalyStatus, Severity, RegularizationStatus
from core.infrastructure.database import BaseModel

from shapely.geometry import Point
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column


class AnomalyModel(BaseModel):
    __tablename__ = "anomalies"

    time_entry_id: Mapped[str] = mapped_column(String(32), ForeignKey("time_entries.id"), nullable=False)
    type: Mapped[AnomalyType] = mapped_column(String(32), nullable=False)
    status: Mapped[AnomalyStatus] = mapped_column(String(32), nullable=False)
    severity: Mapped[Severity] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class RegularizationRequestModel(BaseModel):
    __tablename__ = "regularization_requests"

    anomaly_id: Mapped[str] = mapped_column(String(32), ForeignKey("anomalies.id"), nullable=False)
    status: Mapped[RegularizationStatus] = mapped_column(String(32), nullable=False)
    request_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    proposed_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=False)
    decision_comment: Mapped[str | None] = mapped_column(String(512), nullable=True)