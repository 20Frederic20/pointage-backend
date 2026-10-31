from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime
from identity.domain.value_objects.ids import EmployeeId, UserId
from punch.domain.value_objects import TimeEntryId

from ..value_objects import AnomalyId, AnomalyStatus, AnomalyType, Severity


def _employee_id(value: str | None) -> EmployeeId | None:
    return EmployeeId(value) if value else None


def _user_id(value: str | None) -> UserId | None:
    return UserId(value) if value else None


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
        employee_id: EmployeeId | None = None,
        assisted_by_user_id: UserId | None = None,
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
        self.employee_id = employee_id
        self.assisted_by_user_id = assisted_by_user_id

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
            "employee_id": self.employee_id.value if self.employee_id else None,
            "assisted_by_user_id": self.assisted_by_user_id.value if self.assisted_by_user_id else None,
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
            employee_id=_employee_id(payload.get("employee_id")),
            assisted_by_user_id=_user_id(payload.get("assisted_by_user_id")),
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
        employee_id: EmployeeId | None = None,
        assisted_by_user_id: UserId | None = None,
        decided_by: UserId | None = None,
        decided_at: datetime | None = None,
        decision_comment: str | None = None,
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
        self.employee_id = employee_id
        self.assisted_by_user_id = assisted_by_user_id
        self.created_at = created_at
        self.decided_by = decided_by
        self.decided_at = decided_at
        self.decision_comment = decision_comment

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
            "employee_id": self.employee_id.value if self.employee_id else None,
            "assisted_by_user_id": self.assisted_by_user_id.value if self.assisted_by_user_id else None,
            "created_at": encode_datetime(self.created_at),
            "decided_by": self.decided_by.value if self.decided_by else None,
            "decided_at": encode_datetime(self.decided_at),
            "decision_comment": self.decision_comment,
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
            employee_id=_employee_id(payload.get("employee_id")),
            assisted_by_user_id=_user_id(payload.get("assisted_by_user_id")),
            created_at=decode_datetime(payload["created_at"]),
            decided_by=_user_id(payload.get("decided_by")),
            decided_at=decode_datetime(payload.get("decided_at")),
            decision_comment=payload.get("decision_comment"),
        )


class _AnomalyDecided(BaseEvent[AnomalyId]):
    """A manager decided on an open anomaly."""

    def __init__(
        self, anomaly_id: AnomalyId, *, decided_by: UserId, decided_at: datetime, comment: str | None = None
    ) -> None:
        super().__init__()
        self.anomaly_id = anomaly_id
        self.decided_by = decided_by
        self.decided_at = decided_at
        self.comment = comment

    def get_aggregate_id(self) -> AnomalyId:
        return self.anomaly_id

    def to_payload(self) -> dict:
        return {
            "anomaly_id": self.anomaly_id.value,
            "decided_by": self.decided_by.value,
            "decided_at": encode_datetime(self.decided_at),
            "comment": self.comment,
        }

    @classmethod
    def from_payload(cls, payload: dict):
        return cls(
            AnomalyId(payload["anomaly_id"]),
            decided_by=UserId(payload["decided_by"]),
            decided_at=decode_datetime(payload["decided_at"]),
            comment=payload.get("comment"),
        )


class AnomalyValidated(_AnomalyDecided):
    """The anomaly was accepted."""

    def get_event_name(self) -> str:
        return "adjustments.anomaly.validated"


class AnomalyRejected(_AnomalyDecided):
    """The anomaly was refused."""

    def get_event_name(self) -> str:
        return "adjustments.anomaly.rejected"
