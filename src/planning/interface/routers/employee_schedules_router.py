from fastapi import APIRouter, Depends, status

from planning.application.commands import AssignEmployeeScheduleCommand, EndEmployeeScheduleCommand
from planning.infrastructure import PlanningContainer
from planning.interface import (
    AssignEmployeeScheduleRequest,
    EmployeeScheduleResponse,
    EndEmployeeScheduleRequest,
    get_planning,
)

router = APIRouter(prefix="/employee-schedules", tags=["employee-schedules"])


def _to_response(dto) -> EmployeeScheduleResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return EmployeeScheduleResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=EmployeeScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_employee_schedule(
    payload: AssignEmployeeScheduleRequest,
    planning: PlanningContainer = Depends(get_planning),  # noqa: B008
) -> EmployeeScheduleResponse:
    """Assign a time profile version to an employee."""
    dto = await planning.send(
        AssignEmployeeScheduleCommand(
            employee_id=payload.employee_id,
            time_profile_version_id=payload.time_profile_version_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    )
    return _to_response(dto)


@router.post("/{employee_schedule_id}/end", response_model=EmployeeScheduleResponse)
async def end_employee_schedule(
    employee_schedule_id: str,
    payload: EndEmployeeScheduleRequest,
    planning: PlanningContainer = Depends(get_planning),  # noqa: B008
) -> EmployeeScheduleResponse:
    """Set the last day of an employee schedule."""
    dto = await planning.send(
        EndEmployeeScheduleCommand(employee_schedule_id=employee_schedule_id, end_date=payload.end_date)
    )
    return _to_response(dto)
