from fastapi import APIRouter, Depends

from auth.application.dtos import PrincipalDTO
from auth.interface import get_current_principal
from identity.domain.value_objects.location import Location
from punch.application.commands import CreateTimeEntryCommand
from punch.infrastructure import PunchesContainer
from punch.interface import TimeEntryResponse, CreateTimeEntryRequest, get_punches

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
