from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from auth.application.dtos import PrincipalDTO
from auth.interface import get_current_principal
from identity.domain.value_objects.location import Location
from punch.application.commands import (
    CreateAssistedTimeEntryCommand,
    CreateTimeEntryCommand,
)
from punch.application.ports import MAX_PHOTO_BYTES
from punch.application.queries import LookupEmployeeQuery
from punch.infrastructure import PunchesContainer
from punch.interface import (
    CreateTimeEntryRequest,
    EmployeeLookupResponse,
    TimeEntryResponse,
    get_punches,
)

router = APIRouter(prefix="/time-entries", tags=["time-entries"])

def _to_response(dto) -> TimeEntryResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return TimeEntryResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=TimeEntryResponse,
    status_code=201,
)
async def create_time_entry(
    payload: CreateTimeEntryRequest,
    principal: PrincipalDTO = Depends(get_current_principal),  # noqa: B008
    time_entries: PunchesContainer = Depends(get_punches)  # noqa: B008
):
    """Punch for the connected employee. The server decides IN or OUT."""

    dto = await time_entries.send(
        CreateTimeEntryCommand(
            user_id=principal.user_id,
            location=Location(latitude=payload.latitude, longitude=payload.longitude),
            source=payload.source,
            idempotency_key=payload.idempotency_key,
            wifi_identifier=payload.wifi_identifier,
        )
    )

    return _to_response(dto)



@router.get(
    "/assisted/employees/{employee_number}",
    response_model=EmployeeLookupResponse,
)
async def lookup_assisted_employee(
    employee_number: str,
    principal: PrincipalDTO = Depends(get_current_principal),  # noqa: B008
    time_entries: PunchesContainer = Depends(get_punches),  # noqa: B008
):
    """Before an assisted punch: the name behind an employee number, so the
    colleague confirms it is them. 404 if unknown or inactive, 409 for the caller's own."""
    dto = await time_entries.send(
        LookupEmployeeQuery(actor_user_id=principal.user_id, employee_number=employee_number)
    )
    return EmployeeLookupResponse.model_validate(dto, from_attributes=True)


@router.post(
    "/assisted",
    response_model=TimeEntryResponse,
    status_code=201,
)
async def create_assisted_time_entry(
    employee_number: Annotated[str, Form(min_length=1, max_length=64)],
    latitude: Annotated[float, Form()],
    longitude: Annotated[float, Form()],
    idempotency_key: Annotated[str, Form(min_length=1, max_length=255)],
    photo: Annotated[UploadFile, File()],
    wifi_identifier: Annotated[str | None, Form(max_length=255)] = None,
    principal: PrincipalDTO = Depends(get_current_principal),  # noqa: B008
    time_entries: PunchesContainer = Depends(get_punches),  # noqa: B008
):
    """Punch for the colleague whose number is typed, from the caller's phone,
    with a selfie. The entry is PENDING until a manager decides its anomaly."""
    # One byte past the limit is enough for the handler to refuse the file.
    content = await photo.read(MAX_PHOTO_BYTES + 1)
    dto = await time_entries.send(
        CreateAssistedTimeEntryCommand(
            actor_user_id=principal.user_id,
            employee_number=employee_number,
            location=Location(latitude=latitude, longitude=longitude),
            photo=content,
            photo_content_type=photo.content_type or "",
            idempotency_key=idempotency_key,
            wifi_identifier=wifi_identifier,
        )
    )
    return _to_response(dto)
