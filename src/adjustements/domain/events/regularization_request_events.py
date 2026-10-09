from datetime import datetime

from core.domain.events import BaseEvent, decode_datetime, encode_datetime

from ..value_objects import AnomalyId, RegularizationRequestId, RegularizationStatus


class RegularizationRequestCreated(BaseEvent[RegularizationRequestId]):

    def __init__(
        self,
        regularization_request_id: RegularizationRequestId,
        *,
        anomaly_id: AnomalyId,
        request_at: datetime,
        reason: str,
        proposed_time: datetime,
        status: RegularizationStatus,
    ) -> None:
        super().__init__()
        self.regularization_request_id = regularization_request_id
        self.anomaly_id = anomaly_id
        self.request_at = request_at
        self.reason = reason
        self.proposed_time = proposed_time
        self.status = status

    def get_aggregate_id(self) -> RegularizationRequestId:
        return self.regularization_request_id

    def get_event_name(self) -> str:
        return "adjustments.regularization_request.created"

    def to_payload(self) -> dict:
        return {
            "regularization_request_id": self.regularization_request_id.value,
            "anomaly_id": self.anomaly_id.value,
            "request_at": encode_datetime(self.request_at),
            "reason": self.reason,
            "proposed_time": encode_datetime(self.proposed_time),
            "status": RegularizationStatus(self.status).value,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "RegularizationRequestCreated":
        return cls(
            RegularizationRequestId(payload["regularization_request_id"]),
            anomaly_id=AnomalyId(payload["anomaly_id"]),
            request_at=decode_datetime(payload["request_at"]),
            reason=payload["reason"],
            proposed_time=decode_datetime(payload["proposed_time"]),
            status=RegularizationStatus(payload["status"]),
        )


class RegularizationRequestImported(BaseEvent[RegularizationRequestId]):
    """A regularization request taken over from the state tables when event sourcing started."""

    def __init__(
        self,
        regularization_request_id: RegularizationRequestId,
        *,
        anomaly_id: AnomalyId,
        request_at: datetime,
        reason: str,
        proposed_time: datetime,
        status: RegularizationStatus,
        decision_comment: str | None,
        validated_at: datetime | None,
        created_at: datetime,
    ) -> None:
        super().__init__()
        self.regularization_request_id = regularization_request_id
        self.anomaly_id = anomaly_id
        self.request_at = request_at
        self.reason = reason
        self.proposed_time = proposed_time
        self.status = status
        self.decision_comment = decision_comment
        self.validated_at = validated_at
        self.created_at = created_at

    def get_aggregate_id(self) -> RegularizationRequestId:
        return self.regularization_request_id

    def get_event_name(self) -> str:
        return "adjustments.regularization_request.imported"

    def to_payload(self) -> dict:
        return {
            "regularization_request_id": self.regularization_request_id.value,
            "anomaly_id": self.anomaly_id.value,
            "request_at": encode_datetime(self.request_at),
            "reason": self.reason,
            "proposed_time": encode_datetime(self.proposed_time),
            "status": RegularizationStatus(self.status).value,
            "decision_comment": self.decision_comment,
            "validated_at": encode_datetime(self.validated_at),
            "created_at": encode_datetime(self.created_at),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "RegularizationRequestImported":
        return cls(
            RegularizationRequestId(payload["regularization_request_id"]),
            anomaly_id=AnomalyId(payload["anomaly_id"]),
            request_at=decode_datetime(payload["request_at"]),
            reason=payload["reason"],
            proposed_time=decode_datetime(payload["proposed_time"]),
            status=RegularizationStatus(payload["status"]),
            decision_comment=payload["decision_comment"],
            validated_at=decode_datetime(payload["validated_at"]),
            created_at=decode_datetime(payload["created_at"]),
        )
