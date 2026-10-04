from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.infrastructure.database import BaseModel


class AbsenceTypeModel(BaseModel):
    __tablename__ = "absence_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    counts_as_work_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deducts_balance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AbsenceModel(BaseModel):
    __tablename__ = "absences"

    employee_id: Mapped[str] = mapped_column(String(32), ForeignKey("employees.id"), nullable=False, index=True)
    absence_type_id: Mapped[str] = mapped_column(String(32), ForeignKey("absence_types.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    justification_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
