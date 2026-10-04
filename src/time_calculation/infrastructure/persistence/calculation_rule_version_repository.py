"""SQLAlchemy adapter for the CalculationRuleVersion aggregate — the versioned
save protocol (same as ``UserRepository``)."""

from datetime import date

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError

from ...domain.entities import CalculationRuleVersion
from ...domain.repositories import ICalculationRuleVersionRepository
from ...domain.value_objects import CalculationRuleVersionId
from .models import CalculationRuleVersionModel


class CalculationRuleVersionRepository(ICalculationRuleVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- read side ----------------------------------------------------------

    async def get_by_id(self, calculation_rule_version_id: CalculationRuleVersionId) -> CalculationRuleVersion:
        row = await self._session.get(CalculationRuleVersionModel, calculation_rule_version_id.value)
        if row is None:
            raise NotFoundError(
                f"Calculation rule version {calculation_rule_version_id.value} not found",
                context=calculation_rule_version_id.value,
            )
        return self._to_aggregate(row)

    async def exists(self, calculation_rule_version_id: CalculationRuleVersionId) -> bool:
        row = await self._session.scalar(
            select(CalculationRuleVersionModel.id).where(
                CalculationRuleVersionModel.id == calculation_rule_version_id.value
            )
        )
        return row is not None

    async def find_applicable(self, day: date) -> CalculationRuleVersion | None:
        row = await self._session.scalar(
            select(CalculationRuleVersionModel)
            .where(
                CalculationRuleVersionModel.effective_from <= day,
                or_(
                    CalculationRuleVersionModel.effective_to.is_(None),
                    CalculationRuleVersionModel.effective_to >= day,
                ),
            )
            .limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find_latest(self) -> CalculationRuleVersion | None:
        row = await self._session.scalar(
            select(CalculationRuleVersionModel).order_by(CalculationRuleVersionModel.rule_version.desc()).limit(1)
        )
        return self._to_aggregate(row) if row is not None else None

    # -- write side ---------------------------------------------------------

    async def save(self, calculation_rule_version: CalculationRuleVersion) -> None:
        if calculation_rule_version.version == 0:
            await self._insert(calculation_rule_version)
        else:
            await self._update(calculation_rule_version)
        calculation_rule_version._advance_version()

    async def delete(self, calculation_rule_version_id: CalculationRuleVersionId) -> None:
        await self._session.execute(
            delete(CalculationRuleVersionModel).where(
                CalculationRuleVersionModel.id == calculation_rule_version_id.value
            )
        )

    # -- helpers -------------------------------------------------------------

    async def _insert(self, calculation_rule_version: CalculationRuleVersion) -> None:
        try:
            await self._session.execute(
                insert(CalculationRuleVersionModel).values(
                    id=calculation_rule_version.id.value,
                    rule_version=calculation_rule_version.rule_version,
                    effective_from=calculation_rule_version.effective_from,
                    effective_to=calculation_rule_version.effective_to,
                    min_break_duration=calculation_rule_version.min_break_duration,
                    break_threshold=calculation_rule_version.break_threshold,
                    max_daily_work_duration=calculation_rule_version.max_daily_work_duration,
                    max_amplitude=calculation_rule_version.max_amplitude,
                    created_at=calculation_rule_version.created_at,
                    updated_at=calculation_rule_version.updated_at,
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Calculation rule version {calculation_rule_version.rule_version} already exists",
                context=calculation_rule_version.id.value,
            ) from exc

    async def _update(self, calculation_rule_version: CalculationRuleVersion) -> None:
        result = await self._session.execute(
            update(CalculationRuleVersionModel.__table__)
            .where(CalculationRuleVersionModel.id == calculation_rule_version.id.value)
            .where(CalculationRuleVersionModel.version_id == calculation_rule_version.version)
            .values(
                effective_to=calculation_rule_version.effective_to,
                updated_at=calculation_rule_version.updated_at,
                version_id=calculation_rule_version.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Calculation rule version {calculation_rule_version.id.value} was modified concurrently "
                f"(stale version {calculation_rule_version.version})",
                context=calculation_rule_version.id.value,
            )

    def _to_aggregate(self, row) -> CalculationRuleVersion:
        return CalculationRuleVersion(
            CalculationRuleVersionId(row.id),
            rule_version=row.rule_version,
            effective_from=row.effective_from,
            effective_to=row.effective_to,
            min_break_duration=row.min_break_duration,
            break_threshold=row.break_threshold,
            max_daily_work_duration=row.max_daily_work_duration,
            max_amplitude=row.max_amplitude,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
