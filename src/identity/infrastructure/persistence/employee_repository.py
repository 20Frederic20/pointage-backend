from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.errors import ConflictError, NotFoundError
from core.domain.specifications import Specification
from identity.domain import DirectoryId, EmployeeId, UserId
from identity.domain.entities import Employee
from identity.domain.repositories import IEmployeeRepository
from identity.infrastructure.persistence import EmployeeModel
from identity.infrastructure.translators import EmployeesSpecificationTranslator


class EmployeeRepository(IEmployeeRepository):

    def __init__(
        self,
        session: AsyncSession
    ) -> None:
        self._session = session
        self._translator = EmployeesSpecificationTranslator()


    async def get_by_id(self, employee_id: EmployeeId) -> Employee:
        row = await self._session.get(EmployeeModel, employee_id.value)
        if row is None:
            raise NotFoundError(
                f"Employee {employee_id} not found", context=employee_id.value
            )
        return self._to_aggregate(row)

    async def find_by_employee_number(self, employee_number: str) -> Employee | None:
        row = await self._session.scalar(
            select(EmployeeModel).where(EmployeeModel.employee_number == employee_number)
        )
        return self._to_aggregate(row) if row is not None else None

    async def find(
        self, spec: Specification[Employee], *, limit: int = 50, offset: int = 0
    ) -> list[Employee]:
        stmt = (
            select(EmployeeModel)
            .where(self._translator.translate(spec))
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [self._to_aggregate(row) for row in rows]

    async def count(self, spec: Specification[Employee]) -> int:
        stmt = select(func.count()).select_from(EmployeeModel).where(
            self._translator.translate(spec)
        )
        return await self._session.scalar(stmt) or 0

    async def count_active(self) -> int:
        stmt = (
            select(func.count())
            .select_from(EmployeeModel)
            .where(EmployeeModel.is_active.is_(True))
        )
        return await self._session.scalar(stmt) or 0

    async def save(self, employee: Employee) -> None:
        if employee.version == 0:
            await self._insert(employee)
        else:
            await self._update(employee)
        employee._advance_version()

    async def delete(self, employee_id: EmployeeId) -> None:
        await self._session.execute(
            delete(EmployeeModel).where(EmployeeModel.id == employee_id.value)
        )

    async def exists(self, employee_id: EmployeeId) -> bool:
        row = await self._session.scalar(
            select(EmployeeModel.id).where(EmployeeModel.id == employee_id.value)
        )
        return row is not None

    async def _insert(self, employee: Employee) -> None:
        try:
            await self._session.execute(
                insert(EmployeeModel).values(
                    id=employee.id.value,
                    employee_number=employee.employee_number,
                    user_id=employee.user_id.value,
                    role=employee.role,
                    directory_id=employee.directory_id.value,
                    phone=employee.phone,
                    is_active=employee.is_active,
                    # the domain owns timestamps at insert (single source of
                    # truth — the row stores what the aggregate says)
                    created_at=employee.created_at or datetime.now(UTC),
                    updated_at=employee.updated_at or datetime.now(UTC),
                    version_id=1,
                )
            )
        except IntegrityError as exc:
            raise ConflictError(
                f"Employee {employee.id} already exists (id or email collision)",
                context=employee.email,
            ) from exc

    async def _update(self, employee: Employee) -> None:
        result = await self._session.execute(
            update(EmployeeModel.__table__)
            .where(EmployeeModel.id == employee.id.value)
            .where(EmployeeModel.version_id == employee.version)
            .values(
                employee_number=employee.employee_number,
                user_id=employee.user_id.value,
                role=employee.role,
                directory_id=employee.directory_id.value,
                phone=employee.phone,
                is_active=employee.is_active,
                updated_at=employee.updated_at or datetime.now(UTC),
                version_id=employee.version + 1,
            )
        )
        if result.rowcount == 0:
            raise ConflictError(
                f"Employee {employee.id} was modified concurrently "
                f"(stale version {employee.version})",
                context=employee.id.value,
            )

    def _to_aggregate(self, row) -> Employee:
        return Employee(
            EmployeeId(row.id),
            user_id=UserId(row.user_id),
            directory_id=DirectoryId(row.directory_id),
            employee_number=row.employee_number,
            phone=row.phone,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            version=row.version_id,
        )
