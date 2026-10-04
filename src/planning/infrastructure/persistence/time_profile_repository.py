"""SQLAlchemy adapter for the TimeProfile aggregate (profile, versions, days).

The profile row follows the versioned save protocol of ``UserRepository``.
Versions are append-only: a new version is inserted with its days, an
existing one only ever has its ``effective_to`` updated.
"""

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import TimeProfile, TimeProfileDay, TimeProfileVersion
from ...domain.repositories import ITimeProfileRepository
from ...domain.value_objects import DayOfWeek, TimeProfileDayId, TimeProfileId, TimeProfileVersionId
from .models import TimeProfileDayModel, TimeProfileModel, TimeProfileVersionModel


class TimeProfileRepository(ITimeProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, time_profile_id: TimeProfileId) -> TimeProfile:
        row = await self._session.get(TimeProfileModel, time_profile_id.value)
        if row is None:
            raise NotFoundError(
                f"Time profile {time_profile_id.value} not found", context=time_profile_id.value
            )
        return await self._to_aggregate(row)

    async def find_by_version_id(self, time_profile_version_id: TimeProfileVersionId) -> TimeProfile | None:
        time_profile_id = await self._session.scalar(
            select(TimeProfileVersionModel.time_profile_id).where(
                TimeProfileVersionModel.id == time_profile_version_id.value
            )
        )
        if time_profile_id is None:
            return None
        return await self.get_by_id(TimeProfileId(time_profile_id))

    async def exists(self, time_profile_id: TimeProfileId) -> bool:
        row = await self._session.scalar(
            select(TimeProfileModel.id).where(TimeProfileModel.id == time_profile_id.value)
        )
        return row is not None

    # -- write side ---------------------------------------------------------

    async def save(self, time_profile: TimeProfile) -> None:
        if time_profile.version == 0:
            await self._insert(time_profile)
        else:
            await self._update(time_profile)
        await self._save_versions(time_profile)
        time_profile._advance_version()

    async def delete(self, time_profile_id: TimeProfileId) -> None:
        version_ids = select(TimeProfileVersionModel.id).where(
            TimeProfileVersionModel.time_profile_id == time_profile_id.value
        )
        await self._session.execute(
            delete(TimeProfileDayModel).where(TimeProfileDayModel.time_profile_version_id.in_(version_ids))
        )
        await self._session.execute(
            delete(TimeProfileVersionModel).where(TimeProfileVersionModel.time_profile_id == time_profile_id.value)
        )
        await self._session.execute(delete(TimeProfileModel).where(TimeProfileModel.id == time_profile_id.value))

    # -- helpers -------------------------------------------------------------

    async def _insert(self, time_profile: TimeProfile) -> None:
        try:
            await self._session.execute(
                insert(TimeProfileModel).values(
                    id=time_profile.id.value,
                    name=time_profile.name,
                    timezone=time_profile.timezone,
                    active=time_profile.active,
                    created_at=time_profile.created_at,
                    updated_at=time_profile.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Time profile {time_profile.id.value} conflicts with an existing row",
                context=time_profile.id.value,
            ) from exc

    async def _update(self, time_profile: TimeProfile) -> None:
        result = await self._session.execute(
            update(TimeProfileModel.__table__)
            .where(TimeProfileModel.id == time_profile.id.value)
            .where(TimeProfileModel.version_id == time_profile.version)
            .values(
                name=time_profile.name,
                timezone=time_profile.timezone,
                active=time_profile.active,
                updated_at=time_profile.updated_at,
                version_id=time_profile.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Time profile {time_profile.id.value} was modified concurrently "
                f"(stale version {time_profile.version})",
                context=time_profile.id.value,
            )

    async def _save_versions(self, time_profile: TimeProfile) -> None:
        stored_ids = set(
            (
                await self._session.scalars(
                    select(TimeProfileVersionModel.id).where(
                        TimeProfileVersionModel.time_profile_id == time_profile.id.value
                    )
                )
            ).all()
        )
        for profile_version in time_profile.versions:
            if profile_version.id.value in stored_ids:
                await self._session.execute(
                    update(TimeProfileVersionModel.__table__)
                    .where(TimeProfileVersionModel.id == profile_version.id.value)
                    .values(effective_to=profile_version.effective_to, updated_at=profile_version.updated_at)
                )
                continue
            await self._session.execute(
                insert(TimeProfileVersionModel).values(
                    id=profile_version.id.value,
                    time_profile_id=time_profile.id.value,
                    version=profile_version.version,
                    effective_from=profile_version.effective_from,
                    effective_to=profile_version.effective_to,
                    created_at=profile_version.created_at,
                    updated_at=profile_version.updated_at,
                    version_id=1,
                )
            )
            for day in profile_version.days:
                await self._session.execute(
                    insert(TimeProfileDayModel).values(
                        id=day.id.value,
                        time_profile_version_id=profile_version.id.value,
                        day_of_week=day.day_of_week.value,
                        start_time=day.start_time,
                        end_time=day.end_time,
                        break_duration=day.break_duration,
                        break_threshold=day.break_threshold,
                        tolerance=day.tolerance,
                        created_at=day.created_at,
                        updated_at=day.updated_at,
                        version_id=1,
                    )
                )

    async def _to_aggregate(self, row) -> TimeProfile:
        version_rows = (
            await self._session.scalars(
                select(TimeProfileVersionModel)
                .where(TimeProfileVersionModel.time_profile_id == row.id)
                .order_by(TimeProfileVersionModel.version)
            )
        ).all()
        day_rows = (
            await self._session.scalars(
                select(TimeProfileDayModel).where(
                    TimeProfileDayModel.time_profile_version_id.in_([v.id for v in version_rows])
                )
            )
        ).all()
        versions = [
            TimeProfileVersion(
                TimeProfileVersionId(version_row.id),
                version=version_row.version,
                effective_from=version_row.effective_from,
                effective_to=version_row.effective_to,
                days=tuple(
                    TimeProfileDay(
                        TimeProfileDayId(day_row.id),
                        day_of_week=DayOfWeek(day_row.day_of_week),
                        start_time=day_row.start_time,
                        end_time=day_row.end_time,
                        break_duration=day_row.break_duration,
                        break_threshold=day_row.break_threshold,
                        tolerance=day_row.tolerance,
                        created_at=day_row.created_at,
                        updated_at=day_row.updated_at,
                    )
                    for day_row in day_rows
                    if day_row.time_profile_version_id == version_row.id
                ),
                created_at=version_row.created_at,
                updated_at=version_row.updated_at,
            )
            for version_row in version_rows
        ]
        return TimeProfile(
            TimeProfileId(row.id),
            name=row.name,
            timezone=row.timezone,
            active=row.active,
            versions=versions,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
