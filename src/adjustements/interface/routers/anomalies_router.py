"""Back-office anomalies: list, detail, selfie, and the validate / reject
decision, followed by the recalculation of the punched employee's day."""

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Body, Depends, Query, Response

from adjustements.application.commands import DecideAnomalyCommand
from adjustements.application.dtos import AnomalyDecisionDTO, AnomalyListItemDTO
from adjustements.application.queries import GetAnomaliesQuery, GetAnomalyByIdQuery
from adjustements.domain.value_objects import AnomalyStatus, AnomalyType
from adjustements.infrastructure.container import AdjustementsContainer
from adjustements.interface.dependancies import get_anomalies
from adjustements.interface.schemas import (
    AnomalyDecisionRequest,
    AnomalyItemResponse,
    AnomalyListResponse,
)
from auth.application.dtos import PrincipalDTO
from auth.interface import require_role
from core.audit import audit
from core.domain.errors import DomainError, NotFoundError
from identity.domain import Role
from time_calculation.application.commands import CalculateDailyTimeCommand
from time_calculation.infrastructure import TimeCalculationContainer
from time_calculation.interface import get_time_calculation

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

_responsible = require_role(Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN)


def _to_response(item: AnomalyListItemDTO) -> AnomalyItemResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return AnomalyItemResponse.model_validate(item, from_attributes=True)


async def _get_item(anomalies: AdjustementsContainer, anomaly_id: str) -> AnomalyListItemDTO:
    item = await anomalies.send(GetAnomalyByIdQuery(anomaly_id=anomaly_id))
    if item is None:
        raise NotFoundError(f"Anomaly {anomaly_id} not found", context=anomaly_id)
    return item


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    status: AnomalyStatus | None = None,
    type: AnomalyType | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: PrincipalDTO = Depends(_responsible),  # noqa: B008
    anomalies: AdjustementsContainer = Depends(get_anomalies),  # noqa: B008
) -> AnomalyListResponse:
    """Anomalies for the back-office, newest detection first."""
    page = await anomalies.send(GetAnomaliesQuery(status=status, type=type, limit=limit, offset=offset))
    return AnomalyListResponse(items=[_to_response(i) for i in page.items], total=page.total)


@router.get("/{anomaly_id}", response_model=AnomalyItemResponse)
async def get_anomaly(
    anomaly_id: str,
    _: PrincipalDTO = Depends(_responsible),  # noqa: B008
    anomalies: AdjustementsContainer = Depends(get_anomalies),  # noqa: B008
) -> AnomalyItemResponse:
    return _to_response(await _get_item(anomalies, anomaly_id))


@router.get("/{anomaly_id}/photo")
async def get_anomaly_photo(
    anomaly_id: str,
    _: PrincipalDTO = Depends(_responsible),  # noqa: B008
    anomalies: AdjustementsContainer = Depends(get_anomalies),  # noqa: B008
) -> Response:
    """The assisted punch's selfie, streamed through the API. 404 when the
    anomaly or its photo is missing."""
    item = await _get_item(anomalies, anomaly_id)
    if item.photo_key is None:
        raise NotFoundError(f"Anomaly {anomaly_id} has no photo", context=anomaly_id)
    content, content_type = await anomalies.photo_storage.get(item.photo_key)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{anomaly_id}/validate", response_model=AnomalyItemResponse)
async def validate_anomaly(
    anomaly_id: str,
    payload: AnomalyDecisionRequest | None = Body(default=None),  # noqa: B008
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    anomalies: AdjustementsContainer = Depends(get_anomalies),  # noqa: B008
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> AnomalyItemResponse:
    """Accept the punch: it now counts. Comment optional."""
    return await _decide(anomaly_id, "VALIDATE", payload, principal, anomalies, time_calculation)


@router.post("/{anomaly_id}/reject", response_model=AnomalyItemResponse)
async def reject_anomaly(
    anomaly_id: str,
    payload: AnomalyDecisionRequest | None = Body(default=None),  # noqa: B008
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    anomalies: AdjustementsContainer = Depends(get_anomalies),  # noqa: B008
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> AnomalyItemResponse:
    """Refuse the punch: it never counts. Comment required."""
    return await _decide(anomaly_id, "REJECT", payload, principal, anomalies, time_calculation)


async def _decide(
    anomaly_id: str,
    decision: Literal["VALIDATE", "REJECT"],
    payload: AnomalyDecisionRequest | None,
    principal: PrincipalDTO,
    anomalies: AdjustementsContainer,
    time_calculation: TimeCalculationContainer,
) -> AnomalyItemResponse:
    # 1. The decision, committed by its own unit of work.
    result: AnomalyDecisionDTO = await anomalies.send(
        DecideAnomalyCommand(
            actor_user_id=principal.user_id,
            actor_role=principal.role,
            anomaly_id=anomaly_id,
            decision=decision,
            comment=payload.comment if payload else None,
        )
    )
    # 2. Then the day, in a separate transaction: its failure never undoes the decision.
    #    The day is the punch's date in the employee's time-profile timezone.
    try:
        work_date = await time_calculation.work_date_of(result.employee_id, result.occured_at)
        await time_calculation.send(CalculateDailyTimeCommand(employee_id=result.employee_id, work_date=work_date))
    except DomainError as exc:
        audit.warning(
            "action=RECALC_AFTER_DECISION anomaly=%s status=SKIPPED reason=%s", anomaly_id, exc.code
        )
    except Exception as exc:  # noqa: BLE001 - the decision is committed: never turn it into a 500
        audit.exception(
            "action=RECALC_AFTER_DECISION anomaly=%s status=FAILED reason=%s", anomaly_id, type(exc).__name__
        )
    # 3. The row, from the read side (names), with the decision overlaid: the
    #    projection runs asynchronously and may not have caught up yet.
    decided = result.anomaly
    item = await anomalies.send(GetAnomalyByIdQuery(anomaly_id=anomaly_id))
    if item is None:
        item = AnomalyListItemDTO(
            id=decided.id,
            type=decided.type,
            severity=decided.severity,
            status=decided.status,
            detected_at=decided.detected_at,
            employee_id=result.employee_id,
            occured_at=result.occured_at,
        )
    item = replace(
        item, status=decided.status, decided_at=decided.decided_at, decision_comment=decided.decision_comment
    )
    return _to_response(item)
