"""One-off backfill for the employee actions (deactivation, several companies).

Until now an employee record's ``is_active`` was never checked, and the
onboarding form left it off by default: real employees may be "inactive"
without anyone knowing. The record also did not store its company. Run once,
from ``src/``, after ``sql/migrations/2026-10-31-employee-actions.sql``::

    uv run python -m scripts.activate_and_backfill_employees

* every inactive record is activated (``EmployeeActivated``);
* every record without a company gets the root directory of its earliest
  assignment (``EmployeeCompanySet``); a record with no assignment is left as is.

The projection runner, started with the app, carries both into the read database.
Re-runnable: a second run changes nothing.
"""

import asyncio
import logging

from core.infrastructure.database import SQLAlchemyUnitOfWork, build_engine, build_session_factory
from core.infrastructure.event_store import EventStore
from core.settings import DatabaseSettings
from identity.application.services import CompanyService
from identity.domain import EmployeeId
from identity.domain.entities import Employee
from identity.infrastructure.persistence.event_sourced_directory_repository import EventSourcedDirectoryRepository
from identity.infrastructure.persistence.event_sourced_employee_assignment_repository import (
    EventSourcedEmployeeAssignmentRepository,
)
from identity.infrastructure.persistence.event_sourced_employee_repository import (
    EMPLOYEE_EVENT_TYPES,
    EMPLOYEE_STREAM,
    EventSourcedEmployeeRepository,
)

logger = logging.getLogger(__name__)


async def backfill(employees, employee_repository, assignment_repository, company_service) -> tuple[int, int]:
    """Activate and set the company of ``employees``; returns ``(activated, companies_set)``."""
    activated = companies_set = 0
    for employee in employees:
        if not employee.is_active:
            employee.activate()
            activated += 1
        if employee.company_directory_id is None:
            assignments = await assignment_repository.find_by_employee(employee.id)
            if assignments:
                earliest = assignments[-1]  # most recent start first
                employee.set_company(await company_service.root_of(earliest.directory_id))
                companies_set += 1
        if employee.domain_events:
            await employee_repository.save(employee)
    return activated, companies_set


async def main() -> None:
    engine = build_engine(DatabaseSettings())
    session_factory = build_session_factory(engine)
    try:
        async with session_factory() as session, SQLAlchemyUnitOfWork(session):
            store = EventStore(session)
            ids = await store.find_stream_ids(EMPLOYEE_STREAM)
            streams = await store.load_streams(ids, EMPLOYEE_EVENT_TYPES)
            employees = [Employee.rehydrate(EmployeeId(stream_id), events) for stream_id, events in streams.items()]
            activated, companies_set = await backfill(
                employees,
                EventSourcedEmployeeRepository(store),
                EventSourcedEmployeeAssignmentRepository(store),
                CompanyService(EventSourcedDirectoryRepository(store)),
            )
        print(f"{len(employees)} employee record(s): {activated} activated, {companies_set} company set")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
