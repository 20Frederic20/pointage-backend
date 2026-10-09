"""Event sourcing against real Postgres: event store, projections, import, API.

Needs a Postgres + PostGIS server where the test may create databases::

    TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:7433/postgres uv run pytest tests/test_event_sourcing_postgres.py

Skipped without ``TEST_POSTGRES_URL``. Each run recreates two throwaway
databases, ``pointage_test_write`` and ``pointage_test_read``.
"""

import asyncio
import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

ADMIN_URL = os.environ.get("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="set TEST_POSTGRES_URL to run the Postgres tests")

SQL = Path(__file__).resolve().parent.parent / "src" / "sql"
WRITE_DB, READ_DB = "pointage_test_write", "pointage_test_read"


def _url(database: str, driver: str = "postgresql+psycopg") -> str:
    base, _, _ = ADMIN_URL.rpartition("/")
    return f"{driver}{base[len('postgresql'):]}/{database}"


def _recreate(database: str, schema: Path) -> None:
    import psycopg

    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {database}")
    with psycopg.connect(_url(database, "postgresql"), autocommit=True) as connection:
        connection.execute(schema.read_text())


@pytest.fixture
def databases():
    _recreate(WRITE_DB, SQL / "event_store.sql")
    _recreate(READ_DB, SQL / "read_model.sql")
    return _url(WRITE_DB), _url(READ_DB)


def _factories(write_url: str, read_url: str):
    from sqlalchemy.ext.asyncio import create_async_engine

    from core.infrastructure.database import build_session_factory

    write_engine, read_engine = create_async_engine(write_url), create_async_engine(read_url)
    return write_engine, read_engine, build_session_factory(write_engine), build_session_factory(read_engine)


async def _project_all(write_factory, read_factory) -> int:
    from workers.projections import build_projection_worker

    runner = build_projection_worker(write_session_factory=write_factory, read_session_factory=read_factory)
    total = 0
    while projected := await runner.poll_once():
        total += projected
    return total


# ---- event store -------------------------------------------------------------


def test_append_load_concurrency_and_unique_keys(databases):
    from core.domain.errors import ConflictError
    from core.infrastructure.database import SQLAlchemyUnitOfWork
    from core.infrastructure.event_store import EventStore
    from identity.domain import UserId
    from identity.domain.entities import User
    from identity.infrastructure.persistence.event_sourced_user_repository import EventSourcedUserRepository

    async def scenario():
        write_engine, read_engine, write, _ = _factories(*databases)
        user = User.register_owner(UserId.generate(), email=" Boss@Pointage.bj ", password_hash="h")
        async with write() as session, SQLAlchemyUnitOfWork(session):
            await EventSourcedUserRepository(EventStore(session)).save(user)
        assert user.version == 1

        # Two writers load version 1; the second append is refused.
        async with write() as first, write() as second:
            a = await EventSourcedUserRepository(EventStore(first)).get_by_id(user.id)
            b = await EventSourcedUserRepository(EventStore(second)).get_by_id(user.id)
            assert (a.email, a.version) == ("boss@pointage.bj", 1)
            a.deactivate()
            b.record_activity()
            async with SQLAlchemyUnitOfWork(first):
                await EventSourcedUserRepository(EventStore(first)).save(a)
            with pytest.raises(ConflictError):
                async with SQLAlchemyUnitOfWork(second):
                    await EventSourcedUserRepository(EventStore(second)).save(b)

        # Same email, other stream: the unique key refuses it.
        twin = User.register_owner(UserId.generate(), email="boss@pointage.bj", password_hash=None)
        with pytest.raises(ConflictError):
            async with write() as session, SQLAlchemyUnitOfWork(session):
                await EventSourcedUserRepository(EventStore(session)).save(twin)

        async with write() as session:
            reloaded = await EventSourcedUserRepository(EventStore(session)).find_by_email("BOSS@pointage.bj")
        assert (reloaded.id, reloaded.is_active, reloaded.version) == (user.id, False, 2)
        await write_engine.dispose()
        await read_engine.dispose()

    asyncio.run(scenario())


def test_projection_is_exactly_once_and_follows_the_stream(databases):
    from sqlalchemy import text

    from core.infrastructure.database import SQLAlchemyUnitOfWork
    from core.infrastructure.event_store import EventStore
    from identity.domain import DirectoryId, SiteId, SiteKind
    from identity.domain.entities import Directory, Site
    from identity.domain.value_objects.location import Location
    from identity.infrastructure.persistence.event_sourced_directory_repository import EventSourcedDirectoryRepository
    from identity.infrastructure.persistence.event_sourced_site_repository import EventSourcedSiteRepository

    async def scenario():
        write_engine, read_engine, write, read = _factories(*databases)
        directory = Directory.create(DirectoryId.generate(), code="DG", name="Direction")
        site = Site.create(SiteId.generate(), directory_id=directory.id, name="Siège", location=Location(6.36, 2.41),
                           kind=SiteKind.PRINCIPAL)
        annex = Site.create(SiteId.generate(), directory_id=directory.id, name="Annexe", location=Location(6.49, 2.62),
                            kind=SiteKind.ANNEX)
        async with write() as session, SQLAlchemyUnitOfWork(session):
            store = EventStore(session)
            await EventSourcedDirectoryRepository(store).save(directory)
            await EventSourcedSiteRepository(store).save(site)
            await EventSourcedSiteRepository(store).save(annex)
        # Several events of one stream in one batch: swap principal and annex.
        async with write() as session, SQLAlchemyUnitOfWork(session):
            sites = EventSourcedSiteRepository(EventStore(session))
            site, annex = await sites.get_by_id(site.id), await sites.get_by_id(annex.id)
            site.make_annex()
            annex.make_principal()
            await sites.save(site)
            await sites.save(annex)
            assert (await sites.find_principal(directory.id)).id == annex.id

        assert await _project_all(write, read) == 5
        assert await _project_all(write, read) == 0  # nothing projected twice
        async with read() as session:
            rows = (await session.execute(text("SELECT name, kind, version_id FROM sites ORDER BY name"))).all()
            position = await session.scalar(text("SELECT position FROM projection_checkpoints"))
        assert [tuple(row) for row in rows] == [("Annexe", "PRINCIPAL", 2), ("Siège", "ANNEX", 2)]
        assert position == 5
        await write_engine.dispose()
        await read_engine.dispose()

    asyncio.run(scenario())


def test_anomaly_lookups_read_the_punch_streams(databases):
    from adjustements.domain import AnomalyId
    from adjustements.domain.entities import Anomaly
    from adjustements.domain.value_objects import AnomalyStatus, AnomalyType, Severity
    from adjustements.infrastructure.persistence.event_sourced_anomaly_repository import EventSourcedAnomalyRepository
    from core.infrastructure.database import SQLAlchemyUnitOfWork
    from core.infrastructure.event_store import EventStore
    from identity.domain import EmployeeId
    from identity.domain.value_objects.location import Location
    from punch.domain import EntryType, TimeEntryId
    from punch.domain.entities import TimeEntry
    from punch.infrastructure.persistence.event_sourced_time_entry_repository import EventSourcedTimeEntryRepository

    async def scenario():
        write_engine, read_engine, write, _ = _factories(*databases)
        employee_id = EmployeeId.generate()
        entry = TimeEntry.create(TimeEntryId.generate(), employee_id=employee_id, entry_type=EntryType.IN,
                                 location=Location(6.36, 2.41))
        now = datetime.now(UTC)
        anomaly = Anomaly.create(AnomalyId.generate(), time_entry_id=entry.id, type=AnomalyType.MISSING_OUT,
                                 severity=Severity.BLOCKING, status=AnomalyStatus.OPEN, detected_at=now)
        async with write() as session, SQLAlchemyUnitOfWork(session):
            store = EventStore(session)
            await EventSourcedTimeEntryRepository(store).save(entry)
            await EventSourcedAnomalyRepository(store).save(anomaly)
        async with write() as session:
            anomalies = EventSourcedAnomalyRepository(EventStore(session))
            entries = EventSourcedTimeEntryRepository(EventStore(session))
            day = (now - timedelta(hours=1), now + timedelta(hours=1))
            assert await anomalies.exists_open_blocking_between(*day)
            assert [a.id for a in await anomalies.find_open_by_employee_between(employee_id, *day)] == [anomaly.id]
            assert (await entries.find_last_by_employee_id(employee_id)).id == entry.id
            assert [e.id for e in await entries.find_by_employee_between(employee_id, *day)] == [entry.id]
            loaded = await anomalies.get_by_id(anomaly.id)
            loaded.resolve(resolved_at=now)
            async with SQLAlchemyUnitOfWork(session):
                await anomalies.save(loaded)
            assert not await anomalies.exists_open_blocking_between(*day)
        await write_engine.dispose()
        await read_engine.dispose()

    asyncio.run(scenario())


def test_an_id_of_another_kind_is_not_found_and_a_bad_event_is_parked(databases):
    from sqlalchemy import text

    from core.domain.errors import NotFoundError
    from core.infrastructure.database import SQLAlchemyUnitOfWork
    from core.infrastructure.event_store import EventStore
    from identity.domain import DirectoryId, EmployeeId, Role, UserId
    from identity.domain.entities import Directory, Employee, User
    from identity.infrastructure.persistence.event_sourced_directory_repository import EventSourcedDirectoryRepository
    from identity.infrastructure.persistence.event_sourced_employee_repository import EventSourcedEmployeeRepository
    from identity.infrastructure.persistence.event_sourced_user_repository import EventSourcedUserRepository

    async def scenario():
        write_engine, read_engine, write, read = _factories(*databases)
        user = User.register_owner(UserId.generate(), email="a@pointage.bj", password_hash=None)
        async with write() as session, SQLAlchemyUnitOfWork(session):
            await EventSourcedUserRepository(EventStore(session)).save(user)
        async with write() as session:
            employees = EventSourcedEmployeeRepository(EventStore(session))
            assert not await employees.exists(EmployeeId(user.id.value))
            with pytest.raises(NotFoundError):
                await employees.get_by_id(EmployeeId(user.id.value))

        # The write side accepts an employee whose user the read model lacks
        # (written straight to the store, bypassing the handler's check): its
        # projection fails, is parked, and the next events still project.
        orphan = Employee.create(EmployeeId.generate(), user_id=UserId.generate(), employee_number="0000000001",
                                 is_active=True, role=Role.EMPLOYEE)
        directory = Directory.create(DirectoryId.generate(), code="DG", name="Direction")
        async with write() as session, SQLAlchemyUnitOfWork(session):
            store = EventStore(session)
            await EventSourcedEmployeeRepository(store).save(orphan)
            await EventSourcedDirectoryRepository(store).save(directory)
        assert await _project_all(write, read) == 3
        async with read() as session:
            parked = (await session.execute(text("SELECT stream_id, error FROM projection_failures"))).all()
            directories = await session.scalar(text("SELECT count(*) FROM directories"))
            users = await session.scalar(text("SELECT count(*) FROM users"))
        assert [row.stream_id for row in parked] == [orphan.id.value]
        assert parked[0].error.startswith("ConflictError")  # the read repository wraps the FK violation
        assert (directories, users) == (1, 1)
        await write_engine.dispose()
        await read_engine.dispose()

    asyncio.run(scenario())


# ---- import of the state tables ---------------------------------------------


def test_import_then_replay_rebuilds_the_same_rows(databases):
    """The state tables (here: a read database filled through the API) are
    imported as streams, then replayed into an empty read database."""
    import psycopg

    write_url, read_url = databases
    _run_api_scenario(write_url, read_url)

    legacy, rebuilt = "pointage_test_legacy", "pointage_test_rebuilt"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        for name in (legacy, rebuilt):
            admin.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {legacy} TEMPLATE {READ_DB}")
    with psycopg.connect(_url(legacy, "postgresql"), autocommit=True) as connection:
        connection.execute((SQL / "event_store.sql").read_text())
    _recreate(rebuilt, SQL / "read_model.sql")

    async def scenario():
        from core.infrastructure.database import SQLAlchemyUnitOfWork
        from core.infrastructure.event_store import EventStore
        from scripts.import_state_to_event_store import IMPORTERS

        write_engine, read_engine, write, read = _factories(_url(legacy), _url(rebuilt))
        for _, import_streams in IMPORTERS:
            async with write() as session, SQLAlchemyUnitOfWork(session):
                await import_streams(state_session=session, event_store=EventStore(session))
        for _, import_streams in IMPORTERS:  # re-runnable
            async with write() as session, SQLAlchemyUnitOfWork(session):
                assert await import_streams(state_session=session, event_store=EventStore(session)) == 0
        await _project_all(write, read)
        await write_engine.dispose()
        await read_engine.dispose()

    asyncio.run(scenario())

    tables = ("users", "directories", "sites", "employees", "employee_assignments", "time_entries", "absence_types",
              "absences", "anomalies", "regularization_requests", "time_profiles", "time_profile_versions",
              "time_profile_days", "employee_schedules", "periods", "calculation_rule_versions", "daily_time_results")
    with psycopg.connect(_url(legacy, "postgresql")) as before, psycopg.connect(_url(rebuilt, "postgresql")) as after:
        for table in tables:
            query = f"SELECT to_jsonb(t) - 'version_id' FROM {table} t ORDER BY id"
            assert before.execute(query).fetchall() == after.execute(query).fetchall(), table


# ---- the API over both databases ---------------------------------------------


def test_api_over_write_and_read_databases(databases):
    _run_api_scenario(*databases)


def _run_api_scenario(write_url: str, read_url: str) -> None:
    os.environ.update(
        APP_ENV="test", APP_PORT="8000", JWT_SECRET="s" * 40,
        DB_NAME="x", DB_USER="x", DB_PASSWORD="x", DB_HOST="x", DB_PORT="1",
        REDIS_HOST="x", REDIS_PORT="1", REDIS_DB="0",
        DATABASE_URL=write_url, READ_DATABASE_URL=read_url,
    )
    from fastapi.testclient import TestClient

    from main import create_app

    def ok(response, status=None):
        assert response.status_code < 400 and status in (None, response.status_code), response.text
        return response.json() if response.content else None

    def eventually(read, done=lambda body: True):
        """Reads trail the commands by one projection poll."""
        for _ in range(100):
            response = read()
            if response.status_code < 400 and done(response.json()):
                return response.json()
            time.sleep(0.05)
        raise AssertionError(f"read model never caught up: {response.status_code} {response.text}")

    today = date.today()
    with TestClient(create_app()) as client:
        ok(client.post("/users/register", json={"email": "boss@pointage.bj", "password": "secret123"}), 201)
        token = eventually(lambda: client.post(
            "/auth/login", json={"identifier": "boss@pointage.bj", "password": "secret123"}))["accessToken"]
        admin = {"Authorization": f"Bearer {token}"}
        assert client.post("/users/register", json={"email": "boss@pointage.bj"}, headers=admin).status_code == 409
        user = ok(client.post("/users/register", json={"email": "emp@pointage.bj", "password": "secret123"},
                              headers=admin), 201)

        directory = ok(client.post("/directories", json={"code": "DG", "name": "Direction"}), 201)
        principal = ok(client.post("/sites", json={"directory_id": directory["id"], "name": "Siège",
                                                   "latitude": 6.3654, "longitude": 2.4183}), 201)
        annex = ok(client.post("/sites", json={"directory_id": directory["id"], "name": "Annexe",
                                               "latitude": 6.4969, "longitude": 2.6289}), 201)
        assert (principal["kind"], annex["kind"]) == ("PRINCIPAL", "ANNEX")
        ok(client.post(f"/sites/{annex['id']}/make-principal"))
        assert client.post(f"/sites/{annex['id']}/deactivate").status_code == 409
        sites = eventually(lambda: client.get(f"/directories/{directory['id']}/sites"),
                           lambda body: body and body[0]["id"] == annex["id"])
        assert [site["kind"] for site in sites] == ["PRINCIPAL", "ANNEX"]

        employee = ok(client.post("/employees", json={
            "user_id": user["id"], "directory_id": directory["id"], "employee_number": "0000000001",
            "is_active": True, "site_id": principal["id"], "assignment_start_date": (today - timedelta(days=3)).isoformat(),
        }), 201)
        assert client.post("/employees", json={"user_id": user["id"], "directory_id": directory["id"],
                                               "employee_number": "0000000001"}).status_code == 409
        eventually(lambda: client.get(f"/employee-assignments?employee_id={employee['id']}"), bool)

        employee_token = eventually(lambda: client.post(
            "/auth/login", json={"identifier": "0000000001", "password": "secret123"}))["accessToken"]
        as_employee = {"Authorization": f"Bearer {employee_token}"}
        here = {"latitude": 6.3655, "longitude": 2.4183, "source": "MOBILE"}
        first = ok(client.post("/time-entries", json={**here, "idempotency_key": "k1"}, headers=as_employee), 201)
        second = ok(client.post("/time-entries", json={**here, "idempotency_key": "k2"}, headers=as_employee), 201)
        assert (first["entry_type"], second["entry_type"]) == ("IN", "OUT")
        far = client.post("/time-entries", json={"latitude": 6.4969, "longitude": 2.6289, "source": "MOBILE",
                                                 "idempotency_key": "k3"}, headers=as_employee)
        assert far.status_code == 422

        absence_type = ok(client.post("/absence-types", json={"name": "Maladie", "paid": True,
                                                              "counts_as_work_time": False, "deducts_balance": False}), 201)
        now = datetime.now(UTC)
        absence = ok(client.post("/absences", json={
            "employee_id": employee["id"], "absence_type_id": absence_type["id"], "reason": "flu",
            "start_at": (now + timedelta(days=1)).isoformat(), "end_at": (now + timedelta(days=2)).isoformat(),
        }), 201)
        ok(client.post(f"/absences/{absence['id']}/approve"))
        eventually(lambda: client.get(f"/absences/{absence['id']}"), lambda body: body["status"] == "APPROVED")

        profile = ok(client.post("/time-profiles", json={"name": "Bureau", "timezone": "Africa/Porto-Novo"}), 201)
        days = [{"day_of_week": day, "start_time": "08:00:00", "end_time": "17:00:00", "break_duration": "PT1H",
                 "break_threshold": "PT6H", "tolerance": "PT10M"}
                for day in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")]
        ok(client.post(f"/time-profiles/{profile['id']}/versions",
                       json={"effective_from": (today - timedelta(days=30)).isoformat(), "days": days}), 201)
        profile = ok(client.post(f"/time-profiles/{profile['id']}/versions",
                                 json={"effective_from": (today - timedelta(days=10)).isoformat(), "days": days}), 201)
        version_id = profile["versions"][-1]["id"]
        ok(client.post("/employee-schedules", json={"employee_id": employee["id"], "time_profile_version_id": version_id,
                                                    "start_date": (today - timedelta(days=5)).isoformat()}), 201)
        period = ok(client.post("/periods", json={"start_date": (today - timedelta(days=20)).isoformat(),
                                                  "end_date": (today + timedelta(days=10)).isoformat()}), 201)
        assert client.post("/periods", json={"start_date": today.isoformat(),
                                             "end_date": today.isoformat()}).status_code == 409
        ok(client.post("/calculation-rule-versions", json={
            "effective_from": (today - timedelta(days=60)).isoformat(), "min_break_duration": "PT30M",
            "break_threshold": "PT6H", "max_daily_work_duration": "PT10H", "max_amplitude": "PT12H",
        }), 201)
        result = ok(client.post("/daily-time-results/calculate",
                                json={"employee_id": employee["id"], "work_date": today.isoformat()}))
        again = ok(client.post("/daily-time-results/calculate",
                               json={"employee_id": employee["id"], "work_date": today.isoformat()}))
        assert again["id"] == result["id"]
        ok(client.post("/daily-time-results/recalculate-period", json={"period_id": period["id"]}))
        ok(client.post(f"/daily-time-results/{result['id']}/validate"))
        ok(client.post(f"/periods/{period['id']}/lock"))
        ok(client.post(f"/periods/{period['id']}/close"))
        eventually(lambda: client.get(f"/periods/{period['id']}"), lambda body: body["status"] == "CLOSED")
        eventually(lambda: client.get(f"/daily-time-results/{result['id']}"),
                   lambda body: body["status"] == "VALIDATED")
        eventually(lambda: client.get(f"/time-profiles/{profile['id']}"), lambda body: len(body["versions"]) == 2)
