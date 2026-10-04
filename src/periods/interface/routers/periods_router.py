from fastapi import APIRouter, Depends, HTTPException, status

from periods.application.commands import ClosePeriodCommand, LockPeriodCommand, OpenPeriodCommand
from periods.application.queries import GetPeriodByIdQuery
from periods.infrastructure import PeriodsContainer
from periods.interface import OpenPeriodRequest, PeriodResponse, get_periods

router = APIRouter(prefix="/periods", tags=["periods"])


def _to_response(dto) -> PeriodResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return PeriodResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=PeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_period(
    payload: OpenPeriodRequest,
    periods: PeriodsContainer = Depends(get_periods),  # noqa: B008
) -> PeriodResponse:
    """Open a new period."""
    dto = await periods.send(OpenPeriodCommand(start_date=payload.start_date, end_date=payload.end_date))
    return _to_response(dto)


@router.get("/{period_id}", response_model=PeriodResponse)
async def get_period(
    period_id: str,
    periods: PeriodsContainer = Depends(get_periods),  # noqa: B008
) -> PeriodResponse:
    """Load one period."""
    dto = await periods.send(GetPeriodByIdQuery(period_id=period_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")
    return _to_response(dto)


@router.post("/{period_id}/lock", response_model=PeriodResponse)
async def lock_period(
    period_id: str,
    periods: PeriodsContainer = Depends(get_periods),  # noqa: B008
) -> PeriodResponse:
    """Lock an open period before closing it."""
    dto = await periods.send(LockPeriodCommand(period_id=period_id))
    return _to_response(dto)


@router.post("/{period_id}/close", response_model=PeriodResponse)
async def close_period(
    period_id: str,
    periods: PeriodsContainer = Depends(get_periods),  # noqa: B008
) -> PeriodResponse:
    """Close a period once no blocking anomaly is left open."""
    dto = await periods.send(ClosePeriodCommand(period_id=period_id))
    return _to_response(dto)
