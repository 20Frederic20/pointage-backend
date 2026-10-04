from dataclasses import dataclass

from core.application import Query
from ..dtos import RegularizationRequestDTO


@dataclass(frozen=True)
class GetRegularizationRequestByIdQuery(Query):
    regularization_request_id: str

    Result: RegularizationRequestDTO | None = None

