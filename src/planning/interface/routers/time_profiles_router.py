from fastapi import APIRouter, Depends, HTTPException, status

from planning.application.commands import (
    AddTimeProfileVersionCommand,
    CreateTimeProfileCommand,
    TimeProfileDayData,
)
from planning.application.queries import GetTimeProfileByIdQuery
from planning.infrastructure import PlanningContainer
from planning.interface import (
    AddTimeProfileVersionRequest,
    CreateTimeProfileRequest,
    TimeProfileResponse,
    get_planning,
)

router = APIRouter(prefix="/time-profiles", tags=["time-profiles"])


def _to_response(dto) -> TimeProfileResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return TimeProfileResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=TimeProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_time_profile(
    payload: CreateTimeProfileRequest,
    planning: PlanningContainer = Depends(get_planning),  # noqa: B008
) -> TimeProfileResponse:
    """Create a new time profile."""
    dto = await planning.send(CreateTimeProfileCommand(name=payload.name, timezone=payload.timezone))
    return _to_response(dto)


@router.get("/{time_profile_id}", response_model=TimeProfileResponse)
async def get_time_profile(
    time_profile_id: str,
    planning: PlanningContainer = Depends(get_planning),  # noqa: B008
) -> TimeProfileResponse:
    """Load one time profile with its versions."""
    dto = await planning.send(GetTimeProfileByIdQuery(time_profile_id=time_profile_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time profile not found")
    return _to_response(dto)


@router.post(
    "/{time_profile_id}/versions",
    response_model=TimeProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_time_profile_version(
    time_profile_id: str,
    payload: AddTimeProfileVersionRequest,
    planning: PlanningContainer = Depends(get_planning),  # noqa: B008
) -> TimeProfileResponse:
    """Add a dated version; the previous version ends the day before."""
    dto = await planning.send(
        AddTimeProfileVersionCommand(
            time_profile_id=time_profile_id,
            effective_from=payload.effective_from,
            days=tuple(
                TimeProfileDayData(
                    day_of_week=day.day_of_week,
                    start_time=day.start_time,
                    end_time=day.end_time,
                    break_duration=day.break_duration,
                    break_threshold=day.break_threshold,
                    tolerance=day.tolerance,
                )
                for day in payload.days
            ),
        )
    )
    return _to_response(dto)
