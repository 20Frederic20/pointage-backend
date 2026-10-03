from datetime import datetime

from adjustements.domain import RegularizationRequestId, RegularizationStatus, RegularizationRequestCreated, AnomalyId
from core.domain.entity import AggregateRoot


class RegularizationRequest(AggregateRoot[RegularizationRequestId]):

    __slots__ = (
        "_anomaly_id",
        "_request_at",
        "_reason",
        "_proposed_time",
        "_status",
        "_decision_comment",
        "_validated_at"
    )

    def __init__ (
        self,
        regularization_request_id: RegularizationRequestId,
        *,
        anomaly_id: AnomalyId,
        request_at: datetime,
        reason: str,
        proposed_time: datetime,
        status: RegularizationStatus,
        decision_comment: str | None = None,
        validated_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0
    ):
        super().__init__(
            regularization_request_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._anomaly_id = anomaly_id
        self._request_at = request_at
        self._reason = reason
        self._proposed_time = proposed_time
        self._status = status
        self._decision_comment = decision_comment
        self._validated_at = validated_at

    @classmethod
    def create (
        cls,
        regularization_request_id: RegularizationRequestId,
        *,
        request_at: datetime,
        reason: str,
        proposed_time: datetime,
        status: RegularizationStatus,
        anomaly_id: AnomalyId
    ) -> "RegularizationRequest":
        """
        Factory for a brand-new regularization request; records: class:`RegularizationRequestCreated`.
        """
        regularization_request = cls(
            regularization_request_id,
            request_at=request_at,
            reason=reason,
            proposed_time=proposed_time,
            status=status,
            anomaly_id=anomaly_id
        )
        regularization_request.record_event(RegularizationRequestCreated(regularization_request_id))
        return regularization_request

    @property
    def anomaly_id(self) -> AnomalyId:
        return self._anomaly_id

    @property
    def request_at(self) -> datetime:
        return self._request_at

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def proposed_time(self) -> datetime:
        return self._proposed_time

    @property
    def status(self) -> RegularizationStatus:
        return self._status

    @property
    def decision_comment(self) -> str | None:
        return self._decision_comment

    @property
    def validated_at(self) -> datetime | None:
        return self._validated_at
