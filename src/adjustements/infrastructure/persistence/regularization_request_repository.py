from adjustements.domain import IRegularizationRequestRepository, RegularizationRequest, RegularizationRequestId
from core.domain.errors import NotFoundError
from sqlalchemy import select, insert, delete

from .models import RegularizationRequestModel


def _to_aggregate(regularization_request_model) -> RegularizationRequest:
    return RegularizationRequest(
        regularization_request_id=RegularizationRequestId(regularization_request_model.id),
        anomaly_id=regularization_request_model.anomaly_id,
        request_at=regularization_request_model.request_at,
        reason=regularization_request_model.reason,
        proposed_time=regularization_request_model.proposed_time,
        status=regularization_request_model.status,
        decision_comment=regularization_request_model.decision_comment,
        validated_at=regularization_request_model.validated_at,
        created_at=regularization_request_model.created_at,
        updated_at=regularization_request_model.updated_at,
        version=regularization_request_model.version_ic,
    )


class RegularizationRequestRepository(IRegularizationRequestRepository):

    def __init__(self, session):
        self._session = session

    async def get_by_id(self, aggregate_id: RegularizationRequestId) -> RegularizationRequest:
        row = await self._session.get(RegularizationRequestModel, aggregate_id.value)
        if row is None:
            raise NotFoundError(
                f"Regularization request {aggregate_id} not found",
                context=aggregate_id.value,
            )
        return _to_aggregate(row)

    async def exists(self, aggregate_id: RegularizationRequestId) -> bool:
        row = await self._session.get(RegularizationRequestModel, aggregate_id.value)
        return _to_aggregate(row) is not None

    async def exists_any(self) -> bool:
        row = await self._session.scalar(select(RegularizationRequestModel.id).limit(1))
        return row is not None

    async def save(self, aggregate: RegularizationRequest) -> None:
        if aggregate.version == 0:
            await self._insert(aggregate)
        aggregate._advance_version()

    async def delete(self, aggregate_id: RegularizationRequestId) -> None:
        await self._session.execute(
            delete(RegularizationRequestModel).where(RegularizationRequestModel.id == aggregate_id.value)
        )

    async def _insert(self, regularization_request: RegularizationRequest) -> None:
        try:
            await self._session.execute(
                insert(RegularizationRequestModel).values(
                    id=regularization_request.id.value,
                    anomaly_id=regularization_request.anomaly_id.value,
                    request_at=regularization_request.request_at,
                    reason=regularization_request.reason,
                    proposed_time=regularization_request.proposed_time,
                    status=regularization_request.status,
                    decision_comment=regularization_request.decision_comment,
                    validated_at=regularization_request.validated_at,
                    created_at=regularization_request.created_at,
                    updated_at=regularization_request.updated_at,
                    version_ic=regularization_request.version
                )
            )
        except Exception as e:
            await self._session.rollback()
            raise e