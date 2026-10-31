"""Employee assignment routes: where an employee works, and from when to when."""

from fastapi import APIRouter, Depends, status

from auth.application.dtos import PrincipalDTO
from auth.interface import require_role
from identity.domain import Role

from identity.application.commands import AssignEmployeeCommand, EndEmployeeAssignmentCommand
from identity.application.queries import GetEmployeeAssignmentsQuery
from identity.infrastructure import UsersContainer
from identity.interface.schemas import (
    AssignEmployeeRequest,
    EmployeeAssignmentResponse,
    EndEmployeeAssignmentRequest,
)

from ..dependencies import get_users

router = APIRouter(prefix="/employee-assignments", tags=["employee-assignments"])

_responsible = require_role(Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN)


def _assignment_response(dto) -> EmployeeAssignmentResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return EmployeeAssignmentResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=EmployeeAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign(
    payload: AssignEmployeeRequest,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeAssignmentResponse:
    """A transfer when an assignment is running: it ends the day before (or is
    cancelled when it starts the same day)."""
    dto = await users.send(
        AssignEmployeeCommand(
            employee_id=payload.employee_id,
            directory_id=payload.directory_id,
            site_id=payload.site_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            actor_user_id=principal.user_id,
            actor_role=principal.role,
        )
    )
    return _assignment_response(dto)


@router.get("", response_model=list[EmployeeAssignmentResponse])
async def list_for_employee(
    employee_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> list[EmployeeAssignmentResponse]:
    """An employee's assignments, most recent first (``?employee_id=…``)."""
    dtos = await users.send(GetEmployeeAssignmentsQuery(employee_id=employee_id))
    return [_assignment_response(dto) for dto in dtos]


@router.post("/{employee_assignment_id}/end", response_model=EmployeeAssignmentResponse)
async def end(
    employee_assignment_id: str,
    payload: EndEmployeeAssignmentRequest,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeAssignmentResponse:
    dto = await users.send(
        EndEmployeeAssignmentCommand(
            employee_assignment_id=employee_assignment_id,
            end_date=payload.end_date,
            actor_user_id=principal.user_id,
            actor_role=principal.role,
        )
    )
    return _assignment_response(dto)
