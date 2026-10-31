from typing import Protocol

from ..domain.value_objects import AnomalyStatus, AnomalyType
from .dtos import AnomalyListItemDTO


class IAnomalyReadRepository(Protocol):
    """Read side of the back-office anomaly list: the anomaly joined with its
    time entry, the punched employee and the assistant (read database)."""

    async def find(
        self,
        *,
        status: AnomalyStatus | None = None,
        type: AnomalyType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AnomalyListItemDTO]:
        """Matching rows, ``detected_at`` descending."""
        ...

    async def count(self, *, status: AnomalyStatus | None = None, type: AnomalyType | None = None) -> int: ...

    async def get(self, anomaly_id: str) -> AnomalyListItemDTO | None: ...
