from fastapi import APIRouter, Depends, status

from time_calculation.application.commands import CreateCalculationRuleVersionCommand
from time_calculation.infrastructure import TimeCalculationContainer
from time_calculation.interface import (
    CalculationRuleVersionResponse,
    CreateCalculationRuleVersionRequest,
    get_time_calculation,
)

router = APIRouter(prefix="/calculation-rule-versions", tags=["calculation-rule-versions"])


def _to_response(dto) -> CalculationRuleVersionResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return CalculationRuleVersionResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=CalculationRuleVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_calculation_rule_version(
    payload: CreateCalculationRuleVersionRequest,
    time_calculation: TimeCalculationContainer = Depends(get_time_calculation),  # noqa: B008
) -> CalculationRuleVersionResponse:
    """Create a rule version; the previous one ends the day before."""
    dto = await time_calculation.send(
        CreateCalculationRuleVersionCommand(
            effective_from=payload.effective_from,
            min_break_duration=payload.min_break_duration,
            break_threshold=payload.break_threshold,
            max_daily_work_duration=payload.max_daily_work_duration,
            max_amplitude=payload.max_amplitude,
        )
    )
    return _to_response(dto)
