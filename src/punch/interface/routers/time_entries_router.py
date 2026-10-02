from fastapi import APIRouter, Depends

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
    time_entries: PunchesContainer = Depends(get_punches)  # noqa: B008
):
    """Create a new time entry."""

    dto = await time_entries.send(
        CreateTimeEntryCommand(
            employee_number=payload.employee_number,
            location=Location(payload.longitude, payload.latitude),
            source=payload.source,
            idempotency_key=payload.idempotency_key,
            wifi_identifier=payload.wifi_identifier,
            location_confidence=payload.location_confidence
        )
    )

    return _to_response(dto)
