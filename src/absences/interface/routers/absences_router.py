from fastapi import APIRouter, Depends, HTTPException, Response, status

from absences.application.commands import (
    ApproveAbsenceCommand,
    DeclareAbsenceCommand,
    NeutralizeAnomalyCommand,
    RejectAbsenceCommand,
)
from absences.application.queries import GetAbsenceByIdQuery
from absences.infrastructure import AbsencesContainer
from absences.interface import (
    AbsenceResponse,
    DeclareAbsenceRequest,
    NeutralizeAnomalyRequest,
    get_absences,
)

router = APIRouter(prefix="/absences", tags=["absences"])


def _to_response(dto) -> AbsenceResponse:
    """DTO (dataclass) → wire schema, camelCase by alias."""
    return AbsenceResponse.model_validate(dto, from_attributes=True)


@router.post(
    "",
    response_model=AbsenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def declare_absence(
    payload: DeclareAbsenceRequest,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> AbsenceResponse:
    """Declare an absence for an employee."""
    dto = await absences.send(
        DeclareAbsenceCommand(
            employee_id=payload.employee_id,
            absence_type_id=payload.absence_type_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            reason=payload.reason,
            justification_reference=payload.justification_reference,
        )
    )
    return _to_response(dto)


@router.get("/{absence_id}", response_model=AbsenceResponse)
async def get_absence(
    absence_id: str,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> AbsenceResponse:
    """Load one absence."""
    dto = await absences.send(GetAbsenceByIdQuery(absence_id=absence_id))
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found")
    return _to_response(dto)


@router.post("/{absence_id}/approve", response_model=AbsenceResponse)
async def approve_absence(
    absence_id: str,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> AbsenceResponse:
    """Approve a pending absence."""
    dto = await absences.send(ApproveAbsenceCommand(absence_id=absence_id))
    return _to_response(dto)


@router.post("/{absence_id}/reject", response_model=AbsenceResponse)
async def reject_absence(
    absence_id: str,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> AbsenceResponse:
    """Reject a pending absence."""
    dto = await absences.send(RejectAbsenceCommand(absence_id=absence_id))
    return _to_response(dto)


@router.post(
    "/{absence_id}/neutralize-anomaly",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def neutralize_anomaly(
    absence_id: str,
    payload: NeutralizeAnomalyRequest,
    absences: AbsencesContainer = Depends(get_absences),  # noqa: B008
) -> Response:
    """Resolve an anomaly covered by an approved absence."""
    await absences.send(
        NeutralizeAnomalyCommand(absence_id=absence_id, anomaly_id=payload.anomaly_id)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
