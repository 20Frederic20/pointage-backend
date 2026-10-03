from datetime import datetime

from adjustements.domain import AnomalyId, AnomalyType, Severity, AnomalyStatus, AnomalyCreated
from core.domain.entity import AggregateRoot


class Anomaly(AggregateRoot[AnomalyId]):

    __slots__ = (
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
        anomaly = cls(
            anomaly_id,
            type=type,
            severity=severity,
            status=status,
            detected_at=detected_at,
            resolved_at=resolved_at,
            description=description
        )
        anomaly.record_event(AnomalyCreated(anomaly_id))
        return anomaly