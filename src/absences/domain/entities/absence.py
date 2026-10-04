from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from core.domain.entity import AggregateRoot
from identity.domain import EmployeeId

from ..errors import (
    AbsenceNotApprovedError,
    AbsenceNotPendingError,
    AbsenceTypeInactiveError,
    AnomalyNotCoveredByAbsenceError,
    InvalidAbsencePeriodError,
)
from ..events import AbsenceApproved, AbsenceDeclared, AbsenceRejected
from ..value_objects import AbsenceId, AbsenceStatus, AbsenceTypeId
from .absence_type import AbsenceType

if TYPE_CHECKING:
    from adjustements.domain.entities import Anomaly


class Absence(AggregateRoot[AbsenceId]):
    """An employee's absence over ``[start_at, end_at]``, pending until decided."""

    __slots__ = (
        "_absence_type_id",
        "_employee_id",
        "_end_at",
        "_justification_reference",
        "_reason",
        "_start_at",
        "_status",
    )

    def __init__(
        self,
        absence_id: AbsenceId,
        *,
        employee_id: EmployeeId,
        absence_type_id: AbsenceTypeId,
        start_at: datetime,
        end_at: datetime,
        reason: str,
        status: AbsenceStatus = AbsenceStatus.PENDING,
        justification_reference: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(absence_id, created_at=created_at, updated_at=updated_at, version=version)
        self._employee_id = employee_id
        self._absence_type_id = absence_type_id
        self._start_at = start_at
        self._end_at = end_at
        self._reason = reason
        self._status = AbsenceStatus(status)
        self._justification_reference = justification_reference

    @classmethod
    def declare(
        cls,
        absence_id: AbsenceId,
        *,
        employee_id: EmployeeId,
        absence_type: AbsenceType,
        start_at: datetime,
        end_at: datetime,
        reason: str,
        justification_reference: str | None = None,
    ) -> "Absence":
        """``declarerAbsence``: a new, pending absence of an active type."""
        if end_at <= start_at:
            raise InvalidAbsencePeriodError(
                "An absence must end after it starts",
                context=f"{start_at.isoformat()} -> {end_at.isoformat()}",
            )
        if not absence_type.active:
            raise AbsenceTypeInactiveError(
                f"Absence type {absence_type.name!r} is no longer active",
                context=absence_type.id.value,
            )
        absence = cls(
            absence_id,
            employee_id=employee_id,
            absence_type_id=absence_type.id,
            start_at=start_at,
            end_at=end_at,
            reason=reason,
            justification_reference=justification_reference,
        )
        absence.record_event(AbsenceDeclared(absence_id))
        return absence

    # ---- behaviour ----------------------------------------------------------

    @property
    def duration(self) -> timedelta:
        """``calculerDuree``: calendar span of the absence."""
        return self._end_at - self._start_at

    def covers(self, moment: datetime) -> bool:
        return self._start_at <= moment <= self._end_at

    def approve(self) -> None:
        """``valider``."""
        self._decide(AbsenceStatus.APPROVED)
        self.record_event(AbsenceApproved(self.id))

    def reject(self) -> None:
        """``refuser``."""
        self._decide(AbsenceStatus.REJECTED)
        self.record_event(AbsenceRejected(self.id))

    def neutralize_anomaly(self, anomaly: "Anomaly", *, anomaly_employee_id: EmployeeId) -> None:
        """``neutraliserAnomalie``: an approved absence resolves an anomaly of the
        same employee detected while they were absent."""
        if self._status != AbsenceStatus.APPROVED:
            raise AbsenceNotApprovedError(
                "Only an approved absence can neutralize an anomaly",
                context=self.id.value,
            )
        if anomaly_employee_id != self._employee_id or not self.covers(anomaly.detected_at):
            raise AnomalyNotCoveredByAbsenceError(
                "The anomaly belongs to another employee or falls outside the absence",
                context=anomaly.id.value,
            )
        anomaly.resolve(resolved_at=datetime.now(UTC))

    def _decide(self, status: AbsenceStatus) -> None:
        if self._status != AbsenceStatus.PENDING:
            raise AbsenceNotPendingError(
                f"Absence is already {self._status.value}",
                context=self.id.value,
            )
        self._status = status
        self.touch()

    # ---- state ----------------------------------------------------------------

    @property
    def employee_id(self) -> EmployeeId:
        return self._employee_id

    @property
    def absence_type_id(self) -> AbsenceTypeId:
        return self._absence_type_id

    @property
    def start_at(self) -> datetime:
        return self._start_at

    @property
    def end_at(self) -> datetime:
        return self._end_at

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def status(self) -> AbsenceStatus:
        return self._status

    @property
    def justification_reference(self) -> str | None:
        return self._justification_reference
