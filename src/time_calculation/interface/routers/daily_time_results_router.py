from fastapi import APIRouter, Depends, HTTPException, status

from time_calculation.application.commands import (
    CalculateDailyTimeCommand,
    RecalculatePeriodCommand,
    ValidateDailyTimeResultCommand,
)
from time_calculation.application.queries import GetDailyTimeResultByIdQuery
from time_calculation.infrastructure import TimeCalculationContainer
from time_calculation.interface import (
    CalculateDailyTimeRequest,
    DailyTimeResultResponse,
    PeriodRecalculationResponse,
    RecalculatePeriodRequest,
    get_time_calculation,
)

router = APIRouter(prefix="/daily-time-results", tags=["daily-time-results"])


def _to_response(dto) -> DailyTimeResultResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return DailyTimeResultResponse.model_validate(dto, from_attributes=True)


@router.post("/calculate", response_model=DailyTimeResultResponse)
async def calculate_daily_time(
    payload: CalculateDailyTimeRequest,
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> DailyTimeResultResponse:
    """Calculate, or recalculate, one employee's work date."""
    dto = await time_calculation.send(
        CalculateDailyTimeCommand(employee_id=payload.employee_id, work_date=payload.work_date)
    )
    return _to_response(dto)


@router.post("/recalculate-period", response_model=PeriodRecalculationResponse)
async def recalculate_period(
    payload: RecalculatePeriodRequest,
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> PeriodRecalculationResponse:
    """Recalculate every scheduled employee's days of an open period."""
    dto = await time_calculation.send(RecalculatePeriodCommand(period_id=payload.period_id))
    return PeriodRecalculationResponse.model_validate(dto, from_attributes=True)


@router.get("/{daily_time_result_id}", response_model=DailyTimeResultResponse)
async def get_daily_time_result(
    daily_time_result_id: str,
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> DailyTimeResultResponse:
    """Load one daily time result."""
    dto = await time_calculation.send(GetDailyTimeResultByIdQuery(daily_time_result_id=daily_time_result_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily time result not found")
    return _to_response(dto)


@router.post("/{daily_time_result_id}/validate", response_model=DailyTimeResultResponse)
async def validate_daily_time_result(
    daily_time_result_id: str,
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> DailyTimeResultResponse:
    """Validate a daily time result."""
    dto = await time_calculation.send(ValidateDailyTimeResultCommand(daily_time_result_id=daily_time_result_id))
    return _to_response(dto)
