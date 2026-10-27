from datetime import datetime

from ..errors import AnomalyAlreadyDecidedError, DecisionCommentRequiredError, DecisionCommentTooLongError
from ..events.anomaly_events import (
    AnomalyCreated,
    AnomalyImported,
    AnomalyRejected,
    AnomalyResolved,
    AnomalyValidated,
)
from ..value_objects import AnomalyId, AnomalyStatus, AnomalyType, Severity
from core.domain.entity import AggregateRoot
from core.domain.errors import ConflictError
from identity.domain import EmployeeId, UserId
from punch.domain import TimeEntryId

MAX_DECISION_COMMENT_LENGTH = 512


class Anomaly(AggregateRoot[AnomalyId]):

    __slots__ = (
        "_time_entry_id",
        "_type",
        "_severity",
        "_status",
        "_detected_at",
        "_resolved_at",
        "_description",
        "_employee_id",
        "_assisted_by_user_id",
        "_decided_by",
        "_decided_at",
        "_decision_comment",
    )

    def __init__ (
        self,
        anomaly_id: AnomalyId,
        *,
        time_entry_id: TimeEntryId,
        type: AnomalyType,
        severity: Severity,
        status: AnomalyStatus,
        detected_at: datetime,
        resolved_at: datetime | None = None,
        description: str | None = None,
        employee_id: EmployeeId | None = None,
        assisted_by_user_id: UserId | None = None,
        decided_by: UserId | None = None,
        decided_at: datetime | None = None,
        decision_comment: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0
    ):
        """

        :param anomaly_id:
        :param time_entry_id:
        :param type:
        :param severity:
        :param status:
        :param detected_at:
        :param resolved_at:
        :param description:
        :param created_at:
        :param updated_at:
        :param version:
        """
        super().__init__(
            anomaly_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._time_entry_id = time_entry_id
        self._description = description
        self._type = type
        self._severity = severity
        self._status = status
        self._detected_at = detected_at
        self._resolved_at = resolved_at
        self._description = description
        self._employee_id = employee_id
        self._assisted_by_user_id = assisted_by_user_id
        self._decided_by = decided_by
        self._decided_at = decided_at
        self._decision_comment = decision_comment

    @classmethod
    def create (
        cls,
        anomaly_id: AnomalyId,
        *,
        time_entry_id: TimeEntryId,
        type: AnomalyType,
        severity: Severity,
        status: AnomalyStatus,
        detected_at: datetime,
        resolved_at: datetime | None = None,
        description: str | None = None,
        employee_id: EmployeeId | None = None,
        assisted_by_user_id: UserId | None = None,
    ) -> "Anomaly":
        """
        Factory for a brand-new anomaly.
        """
        anomaly = cls.rehydrate(anomaly_id, [])
        anomaly._raise(
            AnomalyCreated(
                anomaly_id,
                time_entry_id=time_entry_id,
                type=type,
                severity=severity,
                status=status,
                detected_at=detected_at,
                resolved_at=resolved_at,
                description=description,
                employee_id=employee_id,
                assisted_by_user_id=assisted_by_user_id,
            )
        )
        return anomaly

    def validate(self, *, decided_by: UserId, decided_at: datetime, comment: str | None = None) -> None:
        """Accept an open anomaly; records :class:`AnomalyValidated`."""
        self._ensure_decidable()
        self._ensure_comment_fits(comment)
        self._raise(AnomalyValidated(self.id, decided_by=decided_by, decided_at=decided_at, comment=comment))

    def reject(self, *, decided_by: UserId, decided_at: datetime, comment: str) -> None:
        """Refuse an open anomaly (a comment is required); records :class:`AnomalyRejected`."""
        self._ensure_decidable()
        if not comment or not comment.strip():
            raise DecisionCommentRequiredError(
                f"A comment is required to reject anomaly {self.id.value}", context=self.id.value
            )
        self._ensure_comment_fits(comment)
        self._raise(AnomalyRejected(self.id, decided_by=decided_by, decided_at=decided_at, comment=comment))

    def _ensure_comment_fits(self, comment: str | None) -> None:
        if comment is not None and len(comment) > MAX_DECISION_COMMENT_LENGTH:
            raise DecisionCommentTooLongError(
                f"Decision comment exceeds {MAX_DECISION_COMMENT_LENGTH} characters", context=self.id.value
            )

    def _ensure_decidable(self) -> None:
        if self._status not in (AnomalyStatus.OPEN, AnomalyStatus.IN_PROGRESS):
            raise AnomalyAlreadyDecidedError(
                f"Anomaly {self.id.value} is already {self._status}", context=self.id.value
            )

    def resolve(self, *, resolved_at: datetime) -> None:
        """``resoudre``: close an open anomaly; records :class:`AnomalyResolved`."""
        if self._status in (
            AnomalyStatus.RESOLVED,
            AnomalyStatus.CANCELLED,
            AnomalyStatus.VALIDATED,
            AnomalyStatus.REJECTED,
        ):
            raise ConflictError(
                f"Anomaly {self.id.value} is already {self._status}",
                context=self.id.value,
            )
        self._raise(AnomalyResolved(self.id, resolved_at=resolved_at))

    def _apply(self, event) -> None:
        match event:
            case AnomalyCreated() | AnomalyImported():
                self._time_entry_id = event.time_entry_id
                self._type = event.type
                self._severity = event.severity
                self._status = event.status
                self._detected_at = event.detected_at
                self._resolved_at = event.resolved_at
                self._description = event.description
                self._employee_id = event.employee_id
                self._assisted_by_user_id = event.assisted_by_user_id
                self._decided_by = getattr(event, "decided_by", None)
                self._decided_at = getattr(event, "decided_at", None)
                self._decision_comment = getattr(event, "decision_comment", None)
                if isinstance(event, AnomalyImported):
                    self._created_at = event.created_at
            case AnomalyResolved():
                self._status = AnomalyStatus.RESOLVED
                self._resolved_at = event.resolved_at
            case AnomalyValidated() | AnomalyRejected():
                self._status = (
                    AnomalyStatus.VALIDATED if isinstance(event, AnomalyValidated) else AnomalyStatus.REJECTED
                )
                self._decided_by = event.decided_by
                self._decided_at = event.decided_at
                self._decision_comment = event.comment
                self._resolved_at = event.decided_at
            case _:
                super()._apply(event)

    @property
    def type(self) -> AnomalyType:
        return self._type

    @property
    def time_entry_id(self) -> TimeEntryId:
        return self._time_entry_id

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    def status(self) -> AnomalyStatus:
        return self._status

    @property
    def detected_at(self) -> datetime:
        return self._detected_at

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def description(self) -> str | None:
        return self._description


    @property
    def employee_id(self) -> EmployeeId | None:
        return self._employee_id

    @property
    def assisted_by_user_id(self) -> UserId | None:
        return self._assisted_by_user_id

    @property
    def decided_by(self) -> UserId | None:
        return self._decided_by

    @property
    def decided_at(self) -> datetime | None:
        return self._decided_at

    @property
    def decision_comment(self) -> str | None:
        return self._decision_comment
