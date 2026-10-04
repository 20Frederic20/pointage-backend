from fastapi import APIRouter, Depends, status

from absences.application.commands import CreateAbsenceTypeCommand
from absences.infrastructure import AbsencesContainer
from absences.interface import AbsenceTypeResponse, CreateAbsenceTypeRequest, get_absences

router = APIRouter(prefix="/absence-types", tags=["absence-types"])


def _to_response(dto) -> AbsenceTypeResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return AbsenceTypeResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=AbsenceTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_absence_type(
    payload: CreateAbsenceTypeRequest,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> AbsenceTypeResponse:
    """Create a new absence type."""
    dto = await absences.send(
        CreateAbsenceTypeCommand(
            name=payload.name,
            paid=payload.paid,
            counts_as_work_time=payload.counts_as_work_time,
            deducts_balance=payload.deducts_balance,
        )
    )
    return _to_response(dto)
