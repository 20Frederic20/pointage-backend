from datetime import datetime

from ..events.anomaly_events import AnomalyCreated, AnomalyImported, AnomalyResolved
from ..value_objects import AnomalyId, AnomalyStatus, AnomalyType, Severity
from core.domain.entity import AggregateRoot
from core.domain.errors import ConflictError
from punch.domain import TimeEntryId


class Anomaly(AggregateRoot[AnomalyId]):

    __slots__ = (
        "_time_entry_id",
        "_type",
        "_severity",
        "_status",
        "_detected_at",
        "_resolved_at",
        "_description"
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
        description: str | None = None
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
            )
        )
        return anomaly

    def resolve(self, *, resolved_at: datetime) -> None:
        """``resoudre``: close an open anomaly; records :class:`AnomalyResolved`."""
        if self._status in (AnomalyStatus.RESOLVED, AnomalyStatus.CANCELLED):
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
                if isinstance(event, AnomalyImported):
                    self._created_at = event.created_at
            case AnomalyResolved():
                self._status = AnomalyStatus.RESOLVED
                self._resolved_at = event.resolved_at
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
