"""Add a dated version to a time profile."""

from collections.abc import Sequence

from core.application import CommandHandler, IEventOutbox, IUnitOfWork
from core.domain.entity import AggregateRoot

from ...domain.entities import TimeProfile, TimeProfileDay
from ...domain.repositories import ITimeProfileRepository
from ...domain.value_objects import TimeProfileDayId, TimeProfileId, TimeProfileVersionId
from ..commands import AddTimeProfileVersionCommand
from ..dtos import TimeProfileDTO


class AddTimeProfileVersionHandler(CommandHandler[AddTimeProfileVersionCommand, TimeProfileDTO]):
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
        self, request: AddTimeProfileVersionCommand
    ) -> tuple[TimeProfileDTO, Sequence[AggregateRoot]]:
        time_profile = await self._time_profiles.get_by_id(TimeProfileId(request.time_profile_id))
        time_profile.add_version(
            TimeProfileVersionId.generate(),
            effective_from=request.effective_from,
            days=tuple(
                TimeProfileDay(
                    TimeProfileDayId.generate(),
                    day_of_week=day.day_of_week,
                    start_time=day.start_time,
                    end_time=day.end_time,
                    break_duration=day.break_duration,
                    break_threshold=day.break_threshold,
                    tolerance=day.tolerance,
                )
                for day in request.days
            ),
        )
        return TimeProfileDTO.from_aggregate(time_profile), [time_profile]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, TimeProfile):
            await self._time_profiles.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
