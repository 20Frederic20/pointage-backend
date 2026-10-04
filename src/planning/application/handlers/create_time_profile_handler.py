"""Create a time profile."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import TimeProfile
from ...domain.repositories import ITimeProfileRepository
from ...domain.value_objects import TimeProfileId
from ..commands import CreateTimeProfileCommand
from ..dtos import TimeProfileDTO


class CreateTimeProfileHandler(CommandHandler[CreateTimeProfileCommand, TimeProfileDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        time_profile_repository: ITimeProfileRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._time_profiles = time_profile_repository

    async def _execute(
        self, request: CreateTimeProfileCommand
    ) -> tuple[TimeProfileDTO, Sequence[AggregateRoot]]:
        time_profile = TimeProfile.create(
            TimeProfileId.generate(), name=request.name, timezone=request.timezone
        )
        return TimeProfileDTO.from_aggregate(time_profile), [time_profile]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeProfile):
            await self._time_profiles.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
