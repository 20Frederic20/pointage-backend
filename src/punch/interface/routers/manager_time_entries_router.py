from fastapi import APIRouter, Depends

from auth.application.dtos import PrincipalDTO
from auth.interface import require_role
from identity.domain import Role
from punch.application.commands import CreateManagerTimeEntryCommand
from punch.infrastructure import PunchesContainer
from punch.interface import CreateManagerTimeEntryRequest, TimeEntryResponse, get_punches

router = APIRouter(prefix="/employees", tags=["time-entries"])

_responsible = require_role(Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN)


@router.post(
    "/{employee_id}/time-entries",
    response_model=TimeEntryResponse,
    status_code=201,
)
async def create_manager_time_entry(
    employee_id: str,
    payload: CreateManagerTimeEntryRequest,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    time_entries: PunchesContainer = Depends(get_punches),  # noqa: B008
):
    """Punch for an employee, counted immediately. The server decides the time and IN or OUT."""
    dto = await time_entries.send(
        CreateManagerTimeEntryCommand(
            actor_user_id=principal.user_id,
            actor_role=principal.role,
            employee_id=employee_id,
            idempotency_key=payload.idempotency_key,
        )
    )
    return TimeEntryResponse.model_validate(dto, from_attributes=True)
