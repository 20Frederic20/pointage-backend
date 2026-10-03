from datetime import datetime

from adjustements.domain import RegularizationRequestId, RegularizationStatus, RegularizationRequestCreated
from core.domain.entity import AggregateRoot


class RegularizationRequest(AggregateRoot[RegularizationRequestId]):

    __slots__ = (
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
        status: RegularizationStatus
    ) -> "RegularizationRequest":
        """
        Factory for a brand-new regularization request; records: class:`RegularizationRequestCreated`.
        """
        regularization_request = cls(
            regularization_request_id,
            request_at=request_at,
            reason=reason,
            proposed_time=proposed_time,
            status=status
        )
        regularization_request.record_event(RegularizationRequestCreated(regularization_request_id))
        return regularization_request