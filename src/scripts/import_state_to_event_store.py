"""One-off takeover of the state tables into the event store.

Run once, from ``src/``, after ``sql/event_store.sql`` on the write database
(the existing ``pointage_db``, which still holds the old state tables) and
``sql/read_model.sql`` on the new, empty read database::

    uv run python -m scripts.import_state_to_event_store

Each existing row becomes a stream with one ``*Imported`` event holding its
current state (the history before this day is not known, only the state).
Contexts go in foreign-key order, so the projection runner — started with the
app — replays them into the read database without breaking a reference.
Re-runnable: rows whose stream already exists are skipped.
"""

import asyncio
import logging

from absences.infrastructure.importer import import_absences_streams
from adjustements.infrastructure.importer import import_adjustements_streams
from core.infrastructure.database import (
    SQLAlchemyUnitOfWork,
    build_engine,
    build_session_factory,
)
from core.infrastructure.event_store import EventStore
from core.settings import DatabaseSettings
from identity.infrastructure.importer import import_identity_streams
from periods.infrastructure.importer import import_periods_streams
from planning.infrastructure.importer import import_planning_streams
from punch.infrastructure.importer import import_punch_streams
from time_calculation.infrastructure.importer import import_time_calculation_streams

logger = logging.getLogger(__name__)

IMPORTERS = (
    ("identity", import_identity_streams),
    ("punch", import_punch_streams),
    ("adjustements", import_adjustements_streams),
    ("absences", import_absences_streams),
    ("planning", import_planning_streams),
    ("periods", import_periods_streams),
    ("time_calculation", import_time_calculation_streams),
)


async def main() -> None:
    engine = build_engine(DatabaseSettings())
    session_factory = build_session_factory(engine)
    try:
        for name, import_streams in IMPORTERS:
            # One transaction per context: the state tables and the event
            # store live in the same (write) database.
            async with session_factory() as session, SQLAlchemyUnitOfWork(session):
                count = await import_streams(state_session=session, event_store=EventStore(session))
            print(f"{name}: {count} stream(s) imported")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
