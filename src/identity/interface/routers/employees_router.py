"""Workspace routes. ``GET/PATCH /employees/me`` joins this routers together
with the auth context's guards in a later slice."""

from fastapi import APIRouter, Depends, HTTPException, status

from auth.application.dtos import PrincipalDTO
from auth.interface import require_role
from identity.application import (
    GetEmployeeByIdQuery,
    GetEmployeesQuery,
    OnboardEmployeeCommand,
)
from identity.application.commands import EditEmployeeCommand, SetEmployeeActiveCommand
from identity.application.commands.create_employee import CreateEmployeeCommand
from identity.domain import Role
from identity.infrastructure import UsersContainer
from identity.interface import UpdateEmployeeRequest
from identity.interface.schemas import (
    CreateEmployeeRequest,
    EmployeeListResponse,
    EmployeeResponse,
    OnboardEmployeeRequest,
    RoleSchema,
)

from ..dependencies import get_users

router = APIRouter(prefix="/employees", tags=["employees"])


def _employee_reponse(dto) -> EmployeeResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return EmployeeResponse.model_validate(dto, from_attributes=True)


def _employee_list_response(page) -> EmployeeListResponse:
    """Page DTO (items + total) → wire schema; items are converted one by one."""
    return EmployeeListResponse.model_validate(page, from_attributes=True)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    payload: CreateEmployeeRequest,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    dto = await users.send(
        CreateEmployeeCommand(
            user_id=payload.user_id,
            directory_id=payload.directory_id,
            employee_number=payload.employee_number,
            is_active=payload.is_active,
            phone=payload.phone,
            role=payload.role,
            assignment_start_date=payload.assignment_start_date,
            site_id=payload.site_id,
        )
    )

    return _employee_reponse(dto)


@router.post(
    "/onboard",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def onboard(
    payload: OnboardEmployeeRequest,
    principal: PrincipalDTO = Depends(require_role(Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN)),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    """Create the employee record in a company, with its account unless the email
    already has one (``accountReused``). Everything is saved, or nothing."""
    dto = await users.send(
        OnboardEmployeeCommand(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            directory_id=payload.directory_id,
            employee_number=payload.employee_number,
            is_active=payload.is_active,
            phone=payload.phone,
            role=payload.role,
            assignment_start_date=payload.assignment_start_date,
            site_id=payload.site_id,
            actor_user_id=principal.user_id,
            actor_role=principal.role,
        )
    )
    return _employee_reponse(dto)


_responsible = require_role(Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update(
    employee_id: str,
    payload: UpdateEmployeeRequest,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    """Edit names, phone and role; nobody grants or edits above their own role."""
    dto = await users.send(
        EditEmployeeCommand(
            actor_user_id=principal.user_id,
            actor_role=principal.role,
            employee_id=employee_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            role=payload.role,
        )
    )
    return _employee_reponse(dto)


@router.post("/{employee_id}/deactivate", response_model=EmployeeResponse)
async def deactivate(
    employee_id: str,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    """Leave or departure: the record can no longer punch; the account is untouched."""
    return await _set_active(users, principal, employee_id, active=False)


@router.post("/{employee_id}/activate", response_model=EmployeeResponse)
async def activate(
    employee_id: str,
    principal: PrincipalDTO = Depends(_responsible),  # noqa: B008
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    return await _set_active(users, principal, employee_id, active=True)


async def _set_active(users: UsersContainer, principal: PrincipalDTO, employee_id: str, *, active: bool):
    dto = await users.send(
        SetEmployeeActiveCommand(
            actor_user_id=principal.user_id, actor_role=principal.role, employee_id=employee_id, active=active
        )
    )
    return _employee_reponse(dto)


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    employee_number: str | None = None,
    role: RoleSchema | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeListResponse:
    page = await users.send(
        GetEmployeesQuery(
            employee_number=employee_number,
            # Wire enum → domain enum: the domain specs compare by identity.
            role=Role(role) if role is not None else None,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
    )
    return _employee_list_response(page)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    users: UsersContainer = Depends(get_users),  # noqa: B008
) -> EmployeeResponse:
    dto = await users.send(GetEmployeeByIdQuery(employee_id=employee_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return _employee_reponse(dto)
