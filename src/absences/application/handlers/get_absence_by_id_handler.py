"""Load one absence."""

from core.application import QueryHandler
from core.domain.errors import NotFoundError

from ...domain.repositories import IAbsenceRepository
from ...domain.value_objects import AbsenceId
from ..dtos import AbsenceDTO
from ..queries import GetAbsenceByIdQuery


class GetAbsenceByIdHandler(QueryHandler[GetAbsenceByIdQuery, AbsenceDTO | None]):
    def __init__(self, *, absence_repository: IAbsenceRepository) -> None:
        super().__init__()
        self._absences = absence_repository

    async def handle(self, request: GetAbsenceByIdQuery) -> AbsenceDTO | None:
        try:
            absence = await self._absences.get_by_id(AbsenceId(request.absence_id))
        except NotFoundError:
            return None
        return AbsenceDTO.from_aggregate(absence)
