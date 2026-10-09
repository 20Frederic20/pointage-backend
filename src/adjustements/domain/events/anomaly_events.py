from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime
from punch.domain.value_objects import TimeEntryId

from ..value_objects import AnomalyId, AnomalyStatus, AnomalyType, Severity


class AnomalyCreated(BaseEvent[AnomalyId]):

    def __init__(
        self,
        anomaly_id: AnomalyId,
        *,
        time_entry_id: TimeEntryId,
        type: AnomalyType,
        severity: Severity,
        status: AnomalyStatus,
        detected_at: datetime,
        resolved_at: datetime | None,
        description: str | None,
    ) -> None:
        super().__init__()
        self.anomaly_id = anomaly_id
        self.time_entry_id = time_entry_id
        self.type = type
        self.severity = severity
        self.status = status
        self.detected_at = detected_at
        self.resolved_at = resolved_at
        self.description = description

    def get_aggregate_id(self) -> AnomalyId:
        return self.anomaly_id

    def get_event_name(self) -> str:
        return "adjustments.anomaly.created"

    def to_payload(self) -> dict:
        return {
            "anomaly_id": self.anomaly_id.value,
            "time_entry_id": self.time_entry_id.value,
            "type": AnomalyType(self.type).value,
            "severity": Severity(self.severity).value,
            "status": AnomalyStatus(self.status).value,
            "detected_at": encode_datetime(self.detected_at),
            "resolved_at": encode_datetime(self.resolved_at),
            "description": self.description,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AnomalyCreated":
        return cls(
            AnomalyId(payload["anomaly_id"]),
            time_entry_id=TimeEntryId(payload["time_entry_id"]),
            type=AnomalyType(payload["type"]),
            severity=Severity(payload["severity"]),
            status=AnomalyStatus(payload["status"]),
            detected_at=decode_datetime(payload["detected_at"]),
            resolved_at=decode_datetime(payload["resolved_at"]),
            description=payload["description"],
        )


class AnomalyResolved(BaseEvent[AnomalyId]):
    """An open anomaly was closed (e.g. neutralized by an approved absence)."""

    def __init__(self, anomaly_id: AnomalyId, *, resolved_at: datetime) -> None:
        super().__init__()
        self.anomaly_id = anomaly_id
        self.resolved_at = resolved_at

    def get_aggregate_id(self) -> AnomalyId:
        return self.anomaly_id

    def get_event_name(self) -> str:
        return "adjustments.anomaly.resolved"

    def to_payload(self) -> dict:
        return {"anomaly_id": self.anomaly_id.value, "resolved_at": encode_datetime(self.resolved_at)}

    @classmethod
    def from_payload(cls, payload: dict) -> "AnomalyResolved":
        return cls(AnomalyId(payload["anomaly_id"]), resolved_at=decode_datetime(payload["resolved_at"]))


class AnomalyImported(BaseEvent[AnomalyId]):
    """An anomaly taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        anomaly_id: AnomalyId,
        *,
        time_entry_id: TimeEntryId,
        type: AnomalyType,
        severity: Severity,
        status: AnomalyStatus,
        detected_at: datetime,
        resolved_at: datetime | None,
        description: str | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.anomaly_id = anomaly_id
        self.time_entry_id = time_entry_id
        self.type = type
        self.severity = severity
        self.status = status
        self.detected_at = detected_at
        self.resolved_at = resolved_at
        self.description = description
        self.created_at = created_at

    def get_aggregate_id(self) -> AnomalyId:
        return self.anomaly_id

    def get_event_name(self) -> str:
        return "adjustments.anomaly.imported"

    def to_payload(self) -> dict:
        return {
            "anomaly_id": self.anomaly_id.value,
            "time_entry_id": self.time_entry_id.value,
            "type": AnomalyType(self.type).value,
            "severity": Severity(self.severity).value,
            "status": AnomalyStatus(self.status).value,
            "detected_at": encode_datetime(self.detected_at),
            "resolved_at": encode_datetime(self.resolved_at),
            "description": self.description,
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "AnomalyImported":
        return cls(
            AnomalyId(payload["anomaly_id"]),
            time_entry_id=TimeEntryId(payload["time_entry_id"]),
            type=AnomalyType(payload["type"]),
            severity=Severity(payload["severity"]),
            status=AnomalyStatus(payload["status"]),
            detected_at=decode_datetime(payload["detected_at"]),
            resolved_at=decode_datetime(payload["resolved_at"]),
            description=payload["description"],
            created_at=decode_datetime(payload["created_at"]),
        )
