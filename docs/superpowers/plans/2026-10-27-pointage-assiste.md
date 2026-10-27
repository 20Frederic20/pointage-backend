# Pointage assisté et pointage manager — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two new ways to punch.
- An employee can punch with a colleague's phone (matricule + selfie). That punch creates an anomaly a manager or above validates or rejects, and it does not count before validation.
- A manager or above can punch for an employee directly ("Faire pointer"). That punch counts immediately.

**Architecture:**
- `TimeEntry` (punch) gains a `validation_status` and decision events.
- `Anomaly` (adjustements) gains an employee, an assistant and a decision. A decision updates the anomaly and its time entry in the same transaction, then triggers a recalculation of the day.
- `TimeCalculationService` ignores entries that are not `COUNTED`.
- Selfies go to MinIO behind an `IPhotoStorage` port.
- The Flutter mobile app gets the assisted flow and an employees screen for managers. The web back-office gets "Faire pointer" and an "Anomalies" screen.

**Tech Stack:**
- Backend: Python 3.14, FastAPI, SQLAlchemy async, event store in Postgres, pytest. New dependency `minio`.
- Frontend: Flutter, Riverpod 3, `http`. New dependency `image_picker`.

**Spec:** `backend/docs/superpowers/specs/2026-10-26-pointage-assiste-design.md`

**Repos:** `backend/` and `frontend/` are two separate git repositories. Each commit step names its repo. Backend tests run from `backend/` with `.venv/bin/pytest`. Frontend tests run from `frontend/` with `flutter test`.

## Global Constraints

- **Responsible roles:** `Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN`. Every guarded route uses `require_role(...)` with exactly these four, and the handler re-checks `Role(actor_role).at_least(Role.MANAGER)`.
- **Assisted punch:**
  - Anomaly `type=ASSISTED_POINTING`, `severity=BLOCKING`, `status=OPEN`, created in the same transaction as the time entry.
  - The 500 m rule (`MAX_DISTANCE_METERS = 500`) is applied to the **punched employee's** site.
  - The selfie is mandatory: JPEG or PNG, max 5 MB (`5 * 1024 * 1024` bytes).
- **Manager punch:**
  - `source=MANAGER_ASSISTED`, `validation_status=COUNTED`.
  - No location: `location=None`, `location_confidence=LOW`.
  - Timestamp = server time at the request. The client never sends a time.
- **Shared rules for both new punches:**
  - Entry or exit is always resolved by the server from the punched employee's history. Entries with status `REJECTED` are skipped.
  - Nobody can use either path on themselves. Assisted: matricule = caller's own. Manager: target = caller's own employee.
- **Decisions:**
  - Nobody decides an anomaly where they are the punched employee or the assistant.
  - Reject requires a non-blank comment (max 512 characters). Validate takes an optional comment.
  - After a rejection, the entry or exit type of later punches is **never** recomputed (user decision).
  - A recalculation failure after a decision (no period, closed period, no rule version, day already validated) never fails the decision. It is logged with `audit.warning`.
- **Compatibility:**
  - Old `punchs.time_entry.created` / `imported` and `adjustments.anomaly.*` payloads must replay. Missing keys default to `None`, and `validation_status` defaults to `COUNTED`.
  - Read-model changes go in `src/sql/read_model.sql` **and** in a new idempotent migration `src/sql/migrations/2026-10-27-assisted-punch.sql` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `ALTER COLUMN location DROP NOT NULL`) for existing read databases.
- **Copy:** UI text is in French, in the tone of `frontend/lib/core/api_client.dart`.
- **Known baseline failure:** `tests/test_sites.py::test_punch_on_a_deactivated_site_is_refused` fails before any change. Do not count it as a regression, and do not fix it in this plan.

## Review Focus

1. **Double tap or network retry on either new punch.** The same `idempotency_key` sent twice must give one time entry (and one anomaly), and the second call gets `409 PUNCH_ALREADY_EXISTS`. Test in Task 5 and Task 7.
2. **Two managers deciding the same anomaly at once, or re-deciding.** The second decision gets `409`, and the time entry receives only one decision event. Test in Task 3 (domain) and Task 6 (API).
3. **The recalculation after a decision hits a closed period, a missing period or a validated day.** The decision still returns 200 and is persisted. Test in Task 6.
4. **The upload is not an image or is too large.** The response is `422 INVALID_PHOTO` and nothing is written (no event, no object stored). Test in Task 5.
5. **Lookup of a deactivated employee, or of the caller's own matricule.** Both get `404` / `409`, and no name is leaked for an inactive employee. Test in Task 5.

---

### Task 1: TimeEntry gets a validation status, an assistant, a photo and an optional location

**Files:**
- Create: `backend/src/punch/domain/value_objects/validation_status.py`
- Modify:
  - `backend/src/punch/domain/value_objects/entry_source.py`
  - `backend/src/punch/domain/value_objects/__init__.py`
  - `backend/src/punch/domain/events/time_entry_events.py`
  - `backend/src/punch/domain/events/__init__.py`
  - `backend/src/punch/domain/entities/time_entry.py`
  - `backend/src/punch/domain/errors/errors.py`
  - `backend/src/punch/domain/services/entry_type_resolver.py`
  - `backend/src/punch/application/dtos/time_entry_dtos.py`
  - `backend/src/punch/interface/schemas.py` (`TimeEntryResponse`)
  - `backend/src/punch/infrastructure/persistence/event_sourced_time_entry_repository.py`
  - `backend/src/punch/infrastructure/persistence/models.py`
  - `backend/src/punch/infrastructure/persistence/time_entry_repository.py`
  - `backend/src/sql/read_model.sql` (`time_entries`)
- Create: `backend/src/sql/migrations/2026-10-27-assisted-punch.sql` (time_entries part)
- Test: `backend/tests/test_punch_validation.py`

**Interfaces:**
- Produces:
  - **Value objects**
    - `TimeEntryValidationStatus(StrEnum)` with `COUNTED`, `PENDING`, `REJECTED`, exported from `punch.domain`.
    - `EntrySource.ASSISTED = "ASSISTED"`.
  - **`TimeEntry.create`** gains the keywords `assisted_by_user_id: UserId | None = None`, `photo_key: str | None = None`, `validation_status: TimeEntryValidationStatus = COUNTED`. `location` becomes `Location | None`.
  - **Methods**
    - `TimeEntry.validate(*, decided_by: UserId, decided_at: datetime) -> None` raises `TimeEntryValidated`.
    - `TimeEntry.reject(*, decided_by: UserId, decided_at: datetime) -> None` raises `TimeEntryRejected`.
    - Both raise `TimeEntryNotPendingError` (code `TIME_ENTRY_NOT_PENDING`, 409) unless the status is `PENDING`.
  - **Properties:** `assisted_by_user_id`, `photo_key`, `validation_status`, `counts: bool` (`validation_status == COUNTED`).
  - **Events:** `TimeEntryValidated` (`"punchs.time_entry.validated"`, payload `time_entry_id, decided_by, decided_at`) and `TimeEntryRejected` (`"punchs.time_entry.rejected"`, same payload), both registered in `TIME_ENTRY_EVENT_TYPES`.
  - **`ITimeEntryRepository.find_last_by_employee_id`** now returns the last entry whose status is not `REJECTED`. The event-sourced implementation loads candidates newest first and skips rejected ones.
  - **`TimeEntryDTO`** and **`TimeEntryResponse`** gain `assisted_by_user_id: str | None`, `photo_key` (DTO only, never on the wire) and `validation_status: str`. `location` becomes optional.

- [ ] **Step 1: Write the failing tests** in `tests/test_punch_validation.py`, reusing the `replay` helper pattern of `tests/test_adjustements_event_sourcing.py`:
  - `test_pending_entry_validates_and_counts`:
    - create with `validation_status=PENDING`, `source=ASSISTED`, `assisted_by_user_id=UserId("usr2")`, `photo_key="time-entries/x.jpg"`;
    - check `not entry.counts`;
    - `validate(...)`, then check `entry.validation_status == COUNTED` and `entry.counts`;
    - replay through the JSON round-trip and check the same properties.
  - `test_pending_entry_rejects_and_never_counts`: `reject(...)`, then status is `REJECTED`, and the replay matches.
  - `test_decision_on_counted_or_decided_entry_is_refused`: `pytest.raises(TimeEntryNotPendingError)` for validate on a `COUNTED` entry, and for reject after a reject.
  - `test_entry_without_location_replays`: `location=None`, `source=MANAGER_ASSISTED`, `location_confidence=LOW`. The replay gives `location is None`.
  - `test_legacy_created_payload_replays_as_counted`:
    - take a `TimeEntryCreated.to_payload()` dict;
    - delete the keys `assisted_by_user_id`, `photo_key`, `validation_status`;
    - `from_payload` and apply it;
    - check `validation_status == COUNTED` and `assisted_by_user_id is None`.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_punch_validation.py -v`. Expected: FAIL (ImportError on `TimeEntryValidationStatus`).

- [ ] **Step 3: Implement the domain part.**
  - Add the three new fields to `TimeEntryCreated` and `TimeEntryImported`. In `from_payload`, use `payload.get(...)` with the defaults. When the location is `None`, write `latitude` / `longitude` as `None`.
  - Add the new slots to `TimeEntry`, and remove the dead `_is_active` / `is_active` (never set).
  - `_apply`: `TimeEntryValidated` sets `COUNTED`, `TimeEntryRejected` sets `REJECTED`.
  - `EntryTypeResolver` is unchanged: rejected entries are filtered by the repository.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_punch_validation.py tests/test_punch.py -v`. Expected: PASS.

- [ ] **Step 5: Update the read model.**
  - `TimeEntryModel` gains three columns: `location` nullable, `assisted_by_user_id String(32) nullable`, `photo_key String(255) nullable`, `validation_status String(16) NOT NULL default 'COUNTED'`.
  - `TimeEntryRepository`:
    - `_to_aggregate` maps them (`Location.from_wkt` only when `row.location` is not None);
    - `_insert` writes them;
    - `save` gets an `_update` path for `version > 0`. It updates `validation_status`, `updated_at` and `version_id` with an optimistic `version_id == version` guard, and raises `ConflictError` on 0 rows, the same way `AnomalyRepository._update` does.
  - In `read_model.sql` and the migration file:
    - `time_entries.location` nullable;
    - add `assisted_by_user_id varchar(32)`, `photo_key varchar(255)`, `validation_status varchar(16) DEFAULT 'COUNTED' NOT NULL`.
    - `source varchar(16)` is kept: `MANAGER_ASSISTED` is exactly 16 characters.

- [ ] **Step 6: Run** `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py`. Expected: only the known baseline failure. If a Postgres is reachable (`docker compose up -d pointage_db pointage_read_db`), also run `.venv/bin/pytest tests/test_event_sourcing_postgres.py -q`. Expected: PASS.

- [ ] **Step 7: Commit (backend):**
  ```bash
  git -C backend add -A src/punch src/sql tests/test_punch_validation.py
  git -C backend commit -m "feat(punch): validation status, assistant, photo and optional location on time entries"
  ```

---

### Task 2: The time calculation counts only `COUNTED` entries

**Files:**
- Modify: `backend/src/time_calculation/application/services/time_calculation_service.py:69-72`
- Test: `backend/tests/test_time_calculation_event_sourcing.py` (add a test next to the existing `calculate_day` tests, reusing their fakes)

**Interfaces:**
- Consumes: `TimeEntry.counts` (Task 1).

- [ ] **Step 1: Write the failing test** `test_pending_and_rejected_entries_are_not_worked_time`. The day has these entries:
  - IN at 08:00, `COUNTED`;
  - OUT at 12:00, `COUNTED`;
  - IN at 13:00, `PENDING`;
  - OUT at 17:00, `COUNTED`;
  - IN at 18:00 then OUT at 19:00, both `REJECTED`.

  Expected:
  - the result's worked time is exactly 4 h;
  - with the IN at 13:00 switched to `COUNTED` (validated), the worked time is 8 h.

  Find the property name for worked time by reading `DailyTimeResult`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_time_calculation_event_sourcing.py -k pending -v`. Expected: FAIL (12 h or 9 h counted).
- [ ] **Step 3: Implement.** Filter the `clockings` comprehension with `if entry.counts`.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_time_calculation_event_sourcing.py -v`. Expected: PASS.
- [ ] **Step 5: Commit (backend):** `feat(time-calculation): ignore time entries not validated`.

---

### Task 3: Anomaly carries its employee, its assistant and a decision

**Files:**
- Modify:
  - `backend/src/adjustements/domain/value_objects/anomaly_status.py`
  - `backend/src/adjustements/domain/events/anomaly_events.py`
  - `backend/src/adjustements/domain/events/__init__.py`
  - `backend/src/adjustements/domain/entities/anomaly.py`
  - `backend/src/adjustements/domain/errors/errors.py`
  - `backend/src/adjustements/domain/errors/__init__.py`
  - `backend/src/adjustements/infrastructure/persistence/event_sourced_anomaly_repository.py` (`ANOMALY_EVENT_TYPES`)
  - `backend/src/adjustements/infrastructure/persistence/models.py`
  - `backend/src/adjustements/infrastructure/persistence/anomaly_repository.py`
  - `backend/src/adjustements/application/dtos/anomaly_dtos.py`
  - `backend/src/sql/read_model.sql` (`anomalies`)
  - `backend/src/sql/migrations/2026-10-27-assisted-punch.sql` (anomalies part)
- Test: `backend/tests/test_adjustements_event_sourcing.py` (add the tests below; extend `ANOMALY_PROPS`)

**Interfaces:**
- Produces:
  - **`AnomalyStatus`** gains `VALIDATED` and `REJECTED`.
  - **`Anomaly.create`** gains the keywords `employee_id: EmployeeId | None = None` and `assisted_by_user_id: UserId | None = None`.
  - **Methods**
    - `Anomaly.validate(*, decided_by: UserId, decided_at: datetime, comment: str | None = None) -> None` raises `AnomalyValidated`.
    - `Anomaly.reject(*, decided_by: UserId, decided_at: datetime, comment: str) -> None` raises `AnomalyRejected`.
    - Both raise `AnomalyAlreadyDecidedError` (code `ANOMALY_ALREADY_DECIDED`, 409) unless the status is `OPEN` / `IN_PROGRESS`.
    - `reject` raises `DecisionCommentRequiredError` (code `DECISION_COMMENT_REQUIRED`, 422) when the comment is blank.
  - **Decision state:** `decided_by: UserId | None`, `decided_at: datetime | None`, `decision_comment: str | None`. A decision also sets `resolved_at = decided_at`.
  - **Properties:** `employee_id`, `assisted_by_user_id`.
  - **Events:** `AnomalyValidated` (`"adjustments.anomaly.validated"`) and `AnomalyRejected` (`"adjustments.anomaly.rejected"`), payload `anomaly_id, decided_by, decided_at, comment`.
  - **`AnomalyDTO`** gains `employee_id`, `assisted_by_user_id`, `decided_by`, `decided_at`, `decision_comment`.

- [ ] **Step 1: Write the failing tests:**
  - `test_assisted_anomaly_validates_and_replays`: create an anomaly with `employee_id` and `assisted_by_user_id`, validate it with a comment, then check `status == VALIDATED`, the decision fields, and that the replay matches.
  - `test_assisted_anomaly_rejects_with_comment_and_replays`.
  - `test_reject_without_comment_is_refused`: with `"  "` → `DecisionCommentRequiredError`.
  - `test_decided_anomaly_cannot_be_decided_again`: validate then reject → `AnomalyAlreadyDecidedError`, and reject then validate → same error.
  - `test_legacy_anomaly_payload_replays_without_employee`: drop the new keys from the created payload, then check `employee_id is None`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_adjustements_event_sourcing.py -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement the domain.** `find_open_by_employee_between` keeps its time-entry join (legacy rows have no `employee_id`). `VALIDATED` and `REJECTED` are not in `_OPEN_STATUSES`, so decided anomalies stop blocking.
- [ ] **Step 4: Update the read model.**
  - `AnomalyModel` gets the five nullable columns: `employee_id`, `assisted_by_user_id`, `decided_by` (varchar 32), `decided_at` (timestamptz), `decision_comment` (varchar 512).
  - `AnomalyRepository` maps them in `_to_aggregate` and `_insert`, and `_update` writes the decision fields.
  - Add the same columns to the SQL file and to the migration.
- [ ] **Step 5: Run** `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py`. Expected: only the baseline failure.
- [ ] **Step 6: Commit (backend):** `feat(adjustements): anomaly employee, assistant and validate/reject decision`.

---

### Task 4: Selfie storage (MinIO behind a port)

**Files:**
- Create:
  - `backend/src/punch/application/ports.py`
  - `backend/src/punch/infrastructure/photo_storage.py`
  - `backend/src/core/settings/storage_settings.py`
  - `backend/tests/punch/__init__.py` (empty, only if the test layout needs it)
  - `backend/tests/punch/conftest.py` (holds `InMemoryPhotoStorage`)
- Modify:
  - `backend/src/core/settings/__init__.py`
  - `backend/src/main.py` (`storage_settings` param → `app.state.storage_settings`)
  - `backend/src/lifespan.py`
  - `backend/src/composition.py` (`AppContainer.photo_storage`)
  - `backend/pyproject.toml` (+ `minio>=7.2`)
  - `backend/.env` (MinIO keys for the docker-compose instance: endpoint `localhost:9010`, `minioadmin` / `minioadmin`, bucket `punch-photos`, secure false)
- Test: `backend/tests/test_photo_storage.py`

**Interfaces:**
- Produces:
  - **The port**, in `punch.application.ports`:
    ```python
    class IPhotoStorage(Protocol):
        async def put(self, key: str, content: bytes, content_type: str) -> None: ...
        async def get(self, key: str) -> tuple[bytes, str]: ...  # (content, content_type); raises NotFoundError
    ```
  - **`MinioPhotoStorage(settings: StorageSettings)`**
    - It wraps the synchronous `minio.Minio` calls in `asyncio.to_thread`.
    - It creates the bucket when it is missing, on the first `put`.
  - **`StorageSettings(BaseSettings)`** with `s3_endpoint: str`, `s3_access_key: str`, `s3_secret_key: str`, `s3_bucket: str = "punch-photos"`, `s3_secure: bool = False` (same `.env` config as the other settings).
  - **The key helper** `photo_key_for(time_entry_id: TimeEntryId, content_type: str) -> str` returns `time-entries/{id}.jpg` or `time-entries/{id}.png`.
  - **`InMemoryPhotoStorage`** (test double, a dict).
  - **Wiring:** `request.app.state.container.photo_storage` is available to the routers (Tasks 5 and 6).

- [ ] **Step 1: Write the failing tests:**
  - `test_photo_key_for_jpeg_and_png`;
  - `test_in_memory_storage_round_trip`;
  - `test_in_memory_storage_missing_key_raises_not_found`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_photo_storage.py -v`. Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** the port, the key helper, the settings and the MinIO adapter, and wire them in lifespan and composition. Then run `uv sync` in `backend/` to install `minio`.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_photo_storage.py -v`. Expected: PASS. Then run `.venv/bin/python -c "import main"` from `src/`. Expected: no error.
- [ ] **Step 5: Commit (backend):** `feat(punch): selfie storage port with a MinIO adapter`.

---

### Task 5: Assisted punch: employee lookup and `POST /time-entries/assisted`

**Files:**
- Create:
  - `backend/src/punch/application/commands/create_assisted_time_entry.py`
  - `backend/src/punch/application/queries/lookup_employee.py`
  - `backend/src/punch/application/handlers/create_assisted_time_entry_handler.py`
  - `backend/src/punch/application/handlers/lookup_employee_handler.py`
  - `backend/src/punch/application/services/punch_rules.py`
- Modify:
  - `backend/src/punch/application/handlers/create_time_entry_handler.py` (use `punch_rules`)
  - `backend/src/punch/application/commands/__init__.py`
  - `backend/src/punch/application/dtos/time_entry_dtos.py` (`EmployeeLookupDTO`)
  - `backend/src/punch/domain/errors/errors.py`
  - `backend/src/identity/infrastructure/persistence/event_sourced_employee_repository.py`, add `find_by_employee_number`
  - `backend/src/punch/infrastructure/container.py`: add `user_repository`, `anomaly_repository`, `photo_storage` and the two bindings; the outbox mappers become `PUNCHES_EVENT_MAPPERS + ADJUSTMENTS_EVENT_MAPPERS`
  - `backend/src/punch/interface/dependancies.py`
  - `backend/src/punch/interface/schemas.py`
  - `backend/src/punch/interface/routers/time_entries_router.py`
- Test:
  - `backend/tests/punch/api/test_assisted_punch_api.py`
  - `backend/tests/punch/conftest.py` (in-memory repositories + TestClient over the real router and the real `PunchesContainer`, following the pattern of `tests/identity/conftest.py`)

**Interfaces:**
- Consumes:
  - `TimeEntry.create(... source=EntrySource.ASSISTED, validation_status=PENDING, assisted_by_user_id, photo_key)` (Task 1);
  - `Anomaly.create(... employee_id, assisted_by_user_id)` (Task 3);
  - `IPhotoStorage`, `photo_key_for` (Task 4).
- Produces:
  - **`punch_rules.py`**
    - `async def resolve_today_site(employee, assignment_repo, site_repo) -> Site` raises `EmployeeNotAssignedError`.
    - `def ensure_within_site(location: Location, site: Site) -> float` raises `TooFarFromWorkplaceError` and returns the distance.
    - `async def next_entry_type(employee_id, time_entry_repo, now) -> EntryType`.
    - `CreateTimeEntryHandler` and the two new handlers all use them.
  - **Commands and queries**
    - `CreateAssistedTimeEntryCommand(actor_user_id: str, employee_number: str, location: Location, photo: bytes, photo_content_type: str, idempotency_key: str, wifi_identifier: str | None = None)` returns `TimeEntryDTO`.
    - `LookupEmployeeQuery(actor_user_id: str, employee_number: str)` returns `EmployeeLookupDTO(employee_number: str, first_name: str | None, last_name: str | None)`.
  - **Errors**
    - `SelfAssistedPunchError` (`SELF_ASSISTED_PUNCH`, 409);
    - `InvalidPhotoError` (`INVALID_PHOTO`, 422);
    - `PunchAlreadyExistsError` (existing, 409) for a reused idempotency key.
  - **Routes**
    - `GET /time-entries/assisted/employees/{employee_number}`: any authenticated user. 200 returns `{employeeNumber, firstName, lastName}`. 404 when unknown **or inactive**. 409 for the caller's own matricule.
    - `POST /time-entries/assisted`: `multipart/form-data` with the fields `employee_number`, `latitude`, `longitude`, `idempotency_key`, `wifi_identifier?` and the file `photo`. 201 returns `TimeEntryResponse` with `validationStatus = "PENDING"`.

- **Handler order** (`CreateAssistedTimeEntryHandler._execute`):
  1. validate the photo (content type `image/jpeg` | `image/png`, size ≤ 5 MB, non-empty);
  2. resolve the employee by number (active only, else `NotFoundError`), then refuse if `employee.user_id == actor`;
  3. resolve the site and check the distance;
  4. reserve the idempotency key with `event_store.reserve("punch.idempotency_key", key)` (read `EventStore.reserve` for its exact signature and its conflict behaviour, and map the conflict to `PunchAlreadyExistsError`);
  5. resolve the entry type;
  6. create the `TimeEntry` (PENDING) and the `Anomaly` (description `f"Pointage assisté depuis le compte {actor_user_id}"`);
  7. `photo_storage.put(...)`;
  8. return both aggregates.
- The audit line follows the existing `action=PUNCH_ASSISTED ...` style.

- [ ] **Step 1: Write the failing API tests:**
  - `test_assisted_punch_creates_pending_entry_and_open_anomaly`: response 201, `validationStatus == "PENDING"`, one anomaly `ASSISTED_POINTING` / `BLOCKING` / `OPEN` with `employee_id` = the punched employee and `assisted_by_user_id` = the caller; the photo is stored under `time-entries/<id>.jpg`.
  - `test_assisted_punch_without_photo_is_422`.
  - `test_assisted_punch_with_non_image_or_too_large_photo_is_invalid_photo`: `text/plain`, and 5 MB + 1 byte. Both return 422 `INVALID_PHOTO`, with no entry, no anomaly and no stored object.
  - `test_assisted_punch_for_own_matricule_is_409`.
  - `test_assisted_punch_for_unknown_or_inactive_matricule_is_404`.
  - `test_assisted_punch_far_from_punched_employee_site_is_422`: the caller's own site is close and the target's site is far → `TOO_FAR_FROM_WORKPLACE`.
  - `test_assisted_punch_same_idempotency_key_twice_is_409_and_single_entry`.
  - `test_second_assisted_punch_is_out_and_rejected_entries_are_skipped`: a pending IN, then a second assisted punch → OUT; with the first one rejected, the next punch → IN.
  - `test_lookup_returns_names_only`: the response keys are exactly `{"employeeNumber", "firstName", "lastName"}`.
  - `test_lookup_inactive_or_own_matricule`: 404 / 409.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/punch -v`. Expected: FAIL (404 on the routes).
- [ ] **Step 3: Implement** the handlers, the routes and the container wiring. Keep `CreateTimeEntryHandler`'s behaviour identical by running `tests/test_punch.py` and `tests/test_sites.py`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py`. Expected: the new tests PASS, and only the baseline failure remains.
- [ ] **Step 5: Commit (backend):** `feat(punch): assisted punch with selfie and anomaly`.

---

### Task 6: Anomalies API: list, detail, photo, validate, reject, then recalculation

**Files:**
- Create:
  - `backend/src/adjustements/application/commands/decide_anomaly_command.py`
  - `backend/src/adjustements/application/handlers/decide_anomaly_handler.py`
  - `backend/src/adjustements/application/handlers/get_anomalies_handler.py`
  - `backend/src/adjustements/application/handlers/get_anomaly_by_id_handler.py`
  - `backend/src/adjustements/application/queries/get_anomalies_query.py` (if `GetAnomalyByIdQuery` already exists, reuse it)
  - `backend/src/adjustements/infrastructure/persistence/anomaly_read_repository.py`
  - `backend/src/adjustements/interface/routers/anomalies_router.py`
- Fill in (currently empty):
  - `backend/src/adjustements/infrastructure/container.py`
  - `backend/src/adjustements/interface/dependancies.py`
  - `backend/src/adjustements/interface/schemas.py`
  - `backend/src/adjustements/interface/routers/__init__.py`
  - `backend/src/adjustements/application/handlers/__init__.py`
- Modify: `backend/src/main.py` (include `anomalies_router`)
- Test:
  - `backend/tests/adjustements/api/test_anomalies_api.py`
  - `backend/tests/adjustements/conftest.py`

**Interfaces:**
- Consumes: `Anomaly.validate/reject` (Task 3), `TimeEntry.validate/reject` (Task 1), `IPhotoStorage` (Task 4), `CalculateDailyTimeCommand` + `build_time_calculation_container` (the existing time_calculation container).
- Produces:
  - **`DecideAnomalyCommand`**
    - Signature: `DecideAnomalyCommand(actor_user_id: str, actor_role: str, anomaly_id: str, decision: Literal["VALIDATE", "REJECT"], comment: str | None)` returns `AnomalyDecisionDTO(anomaly: AnomalyDTO, employee_id: str, occured_at: datetime)`.
    - The handler loads the anomaly and its time entry (by `anomaly.time_entry_id`), checks the role, refuses self-decision, applies the decision to both, and returns both aggregates.
    - **Self-decision check:** the actor's employee is found with `find_by_user_id`. The decision is refused when `actor_user_id == anomaly.assisted_by_user_id`, or when the actor's employee id equals `anomaly.employee_id`. The error is `SelfDecisionError` (`SELF_DECISION`, 403).
  - **`GetAnomaliesQuery(status: AnomalyStatus | None, type: AnomalyType | None, limit: int = 20, offset: int = 0)`** returns `AnomalyListPageDTO`.
    - It reads the read DB.
    - Each item joins:
      - the time entry (`occured_at`, `entry_type`, `photo_key is not null`);
      - the punched employee (`employee_number`) and their user (`first_name`, `last_name`);
      - the assistant user (`first_name`, `last_name`).
    - Order: `detected_at desc`.
  - **`GetAnomalyByIdQuery`** returns the same item shape.
  - **Routes** (all with `require_role(MANAGER, HR, PAYROLL, ADMIN)`):
    - `GET /anomalies?status=&type=&limit=&offset=` returns `{items, total}`, camelCase. Item fields: `id, type, severity, status, detectedAt, employeeId, employeeNumber, employeeFirstName, employeeLastName, assistedByFirstName, assistedByLastName, occuredAt, entryType, hasPhoto, decidedAt, decisionComment`.
    - `GET /anomalies/{id}`: the same item.
    - `GET /anomalies/{id}/photo` returns the image bytes as a `Response` with the stored content type. 404 when the anomaly or the photo is missing.
    - `POST /anomalies/{id}/validate` (body `{comment?}`) and `POST /anomalies/{id}/reject` (body `{comment}`) return the item.
  - **Recalculation**, in the router, after the decision command returns: send `CalculateDailyTimeCommand(employee_id, work_date=occured_at.astimezone(UTC).date())` through a time_calculation container built on the same request sessions.
    - Catch `DomainError`, then `audit.warning("action=RECALC_AFTER_DECISION anomaly=%s status=SKIPPED reason=%s", ...)`.
    - ponytail: UTC date; punches near local midnight may recalc the neighbouring day.

- [ ] **Step 1: Write the failing API tests:**
  - `test_list_requires_responsible_role`: EMPLOYEE gets 403; MANAGER, HR, PAYROLL and ADMIN get 200.
  - `test_list_items_carry_names_and_photo_flag`.
  - `test_validate_marks_anomaly_validated_and_entry_counted`: assert on the stored aggregates.
  - `test_reject_requires_comment_and_marks_entry_rejected`: without a comment → 422 `DECISION_COMMENT_REQUIRED`; with a comment → entry `REJECTED`.
  - `test_second_decision_is_409_and_entry_gets_one_decision_event`.
  - `test_assistant_or_punched_employee_cannot_decide`: 403 `SELF_DECISION`.
  - `test_decision_succeeds_when_recalculation_fails`: the fake time_calculation raises `NoPeriodForDateError` → still 200, and the anomaly is `VALIDATED`.
  - `test_photo_route_returns_image_bytes_and_content_type`: also 404 when no photo is stored.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/adjustements -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** The container follows `punch/infrastructure/container.py`. The write side uses the event-sourced anomaly and time-entry repositories. The outbox mappers are `ADJUSTMENTS_EVENT_MAPPERS + PUNCHES_EVENT_MAPPERS`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py`. Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(adjustements): anomalies API with validate/reject and day recalculation`.

---

### Task 7: Manager punch: `POST /employees/{employee_id}/time-entries`

**Files:**
- Create:
  - `backend/src/punch/application/commands/create_manager_time_entry.py`
  - `backend/src/punch/application/handlers/create_manager_time_entry_handler.py`
  - `backend/src/punch/interface/routers/manager_time_entries_router.py`
- Modify:
  - `backend/src/punch/infrastructure/container.py`
  - `backend/src/punch/interface/routers/__init__.py`
  - `backend/src/punch/interface/schemas.py`
  - `backend/src/main.py`
- Test: `backend/tests/punch/api/test_manager_punch_api.py`

**Interfaces:**
- Consumes: `punch_rules.resolve_today_site`, `punch_rules.next_entry_type` (Task 5); `TimeEntry.create(location=None, ...)` (Task 1).
- Produces:
  - **`CreateManagerTimeEntryCommand(actor_user_id: str, actor_role: str, employee_id: str, idempotency_key: str)`** returns `TimeEntryDTO`.
    - `source=MANAGER_ASSISTED`, `location=None`, `location_confidence=LOW`, `assisted_by_user_id=actor`, `validation_status=COUNTED`.
    - The idempotency key is reserved as in Task 5.
  - **Route** `POST /employees/{employee_id}/time-entries` with body `{idempotencyKey}`, guarded by `require_role(MANAGER, HR, PAYROLL, ADMIN)`.
    - It is a separate router file, so identity's router is untouched.
    - 201 returns `TimeEntryResponse` (with `entryType`, `occuredAt`).
  - **Errors:** `SelfManagerPunchError` (`SELF_MANAGER_PUNCH`, 409); an inactive or unknown employee → 404; no assignment → `EMPLOYEE_NOT_ASSIGNED`.

- [ ] **Step 1: Write the failing API tests:**
  - `test_manager_punch_is_counted_immediately`: 201, `validationStatus == "COUNTED"`, `source == "MANAGER_ASSISTED"`, `location` null, no anomaly created.
  - `test_manager_punch_alternates_in_out`.
  - `test_employee_role_gets_403`.
  - `test_manager_cannot_punch_for_self`.
  - `test_unassigned_employee_is_409`.
  - `test_same_idempotency_key_twice_is_409_and_single_entry`.
  - `test_client_cannot_choose_time`: an extra `occuredAt` in the body is ignored, and the stored time is within 5 s of now.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/punch/api/test_manager_punch_api.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py`. Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(punch): manager punch for an employee`.

---

### Task 8: Frontend foundations: role in the session, multipart upload, error messages

**Files:**
- Modify:
  - `frontend/lib/features/auth/session_provider.dart` (`Session.role`)
  - `frontend/lib/core/api_client.dart`
- Test:
  - `frontend/test/core/unit/api_client_test.dart` (create it, or extend it if it exists)
  - `frontend/test/features/auth/unit/session_role_test.dart`

**Interfaces:**
- Produces:
  - **`Role get role` on `Session`.** It decodes the `role` claim of the JWT access token (base64url payload, no signature check) with `Role.fromWire`, and falls back to `Role.employee` when the claim is unreadable.
  - **`bool get isResponsible`**: `role != Role.employee`.
  - **`ApiClient.postMultipart(String path, Map<String, String> fields, {required String fileField, required List<int> bytes, required String filename, required String contentType, String? accessToken}) -> Future<Map<String, dynamic>>`**, using `http.MultipartRequest`. It does not send `Content-Type: application/json`.
  - **`ApiClient.getBytes(String path, {String? accessToken}) -> Future<Uint8List>`**, which shares the same error handling.
  - **New `_messages` entries:**
    - `SELF_ASSISTED_PUNCH`: « Saisissez le matricule du collègue qui pointe, pas le vôtre. »
    - `INVALID_PHOTO`: « La photo est invalide (JPEG ou PNG, 5 Mo maximum). »
    - `SELF_MANAGER_PUNCH`: « Utilisez votre propre pointage pour vous-même. »
    - `ANOMALY_ALREADY_DECIDED`: « Cette anomalie a déjà été traitée. »
    - `DECISION_COMMENT_REQUIRED`: « Un commentaire est obligatoire pour rejeter. »
    - `SELF_DECISION`: « Vous ne pouvez pas traiter une anomalie qui vous concerne. »
  - Also fix the existing `TOO_FAR_FROM_WORKPLACE` text, from « (100 m maximum) » to « (500 m maximum) ».

- [ ] **Step 1: Write the failing tests:**
  - `session.role` from a hand-built JWT with `{"role":"HR"}` → `Role.hr`; a garbage token → `Role.employee`.
  - `postMultipart` sends a multipart request with the file part and the bearer token, checked with a `MockClient` from `package:http/testing.dart`.
  - `postMultipart` maps the `INVALID_PHOTO` error code to its message.
- [ ] **Step 2: Run** `flutter test test/core test/features/auth`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test`. Expected: PASS.
- [ ] **Step 5: Commit (frontend):** `feat: session role and multipart upload`.

---

### Task 9: Mobile: « Pointer pour un collègue »

**Files:**
- Create:
  - `frontend/lib/features/punch/assisted_punch_controller.dart`
  - `frontend/lib/features/punch/assisted_punch_screen.dart`
- Modify:
  - `frontend/lib/features/punch/punch_repository.dart`
  - `frontend/lib/features/punch/punch_screen.dart` (secondary `TextButton.icon` « Pointer pour un collègue » under `_PunchButton`)
  - `frontend/pubspec.yaml` (`image_picker`)
  - `frontend/android/app/src/main/AndroidManifest.xml` (camera permission)
  - `frontend/ios/Runner/Info.plist` (`NSCameraUsageDescription`: « Le selfie confirme l'identité de la personne qui pointe. »)
- Test:
  - `frontend/test/features/punch/unit/assisted_punch_controller_test.dart`
  - `frontend/test/features/punch/widget/assisted_punch_screen_test.dart`

**Interfaces:**
- Consumes: `ApiClient.postMultipart` (Task 8); the backend routes of Task 5.
- Produces:
  - **`PunchRepository.lookupColleague(String token, String employeeNumber) -> Future<Colleague>`**, with `Colleague(employeeNumber, firstName?, lastName?)` and `String get displayName`.
  - **`PunchRepository.punchFor(String token, {required String employeeNumber, required List<int> photo, required String contentType}) -> Future<TimeEntry>`**. It takes the GPS fix exactly like `punch` and generates a fresh idempotency key **once per attempt** (kept on retry of the same attempt).
  - **`TimeEntry.validationStatus`** (`String`, default `'COUNTED'`).
  - **`AssistedPunchController extends Notifier<AssistedPunchState>`.**
    - Steps: `enterNumber`, `confirm(Colleague)`, `selfie(bytes)`, `sending`, `done(TimeEntry)`, `error(String)`.
    - Methods: `lookup(String)`, `confirm()`, `setSelfie(List<int>, String contentType)`, `send()`, `reset()`.
  - **Selfie capture** behind a provider `selfiePickerProvider` returning `Future<(List<int>, String)?> Function()`, implemented with `ImagePicker().pickImage(source: ImageSource.camera, preferredCameraDevice: CameraDevice.front, maxWidth: 1080, imageQuality: 80)`. It is overridable in tests. The gallery is never offered.
  - **The flow screen:**
    - the matricule field, then « Vérifier »;
    - the name card, then « C'est moi », or « Modifier » to go back;
    - « Prendre le selfie »: a preview with « Reprendre » and « Pointer »;
    - the confirmation « Pointage enregistré pour {nom} — en attente de validation » (with « Entrée » / « Sortie » and the time), with « Terminer » returning to `PunchScreen`;
    - the logged-in user's own `PunchState` is not touched.

- [ ] **Step 1: Write the failing tests** with a fake repository:
  - `lookup` on success moves to `confirm`, and an `ApiException(status: 404)` gives the error « Matricule introuvable. »;
  - `send` without a selfie is impossible (the button is disabled in the widget test);
  - a successful `send` moves to `done` with `validationStatus == 'PENDING'`;
  - a retry after a network error reuses the same idempotency key (fake repository records the keys);
  - the widget test walks the whole flow with an overridden `selfiePickerProvider`, and checks that the « Pointer pour un collègue » button is present on `PunchScreen`.
- [ ] **Step 2: Run** `flutter test test/features/punch`. Expected: FAIL.
- [ ] **Step 3: Implement**, then run `flutter pub get`.
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS, no new issues.
- [ ] **Step 5: Commit (frontend):** `feat(mobile): punch for a colleague with a selfie`.

---

### Task 10: « Faire pointer »: back-office Employés and mobile access for responsible roles

**Files:**
- Create:
  - `frontend/lib/features/employee/widgets/punch_for_employee_button.dart`
  - `frontend/lib/features/employee/screens/employee_mobile_screen.dart`
- Modify:
  - `frontend/lib/features/employee/employee_repository.dart`
  - `frontend/lib/features/employee/widgets/employee_table.dart` (action column)
  - `frontend/lib/features/employee/widgets/employee_card.dart` (trailing action)
  - `frontend/lib/features/employee/widgets/employee_detail_view.dart`
  - `frontend/lib/features/punch/punch_screen.dart` (AppBar action « Employés » when `session.isResponsible`)
- Test:
  - `frontend/test/features/employee/widget/punch_for_employee_button_test.dart`
  - extend `frontend/test/features/employee/widget/employee_web_screen_test.dart`

**Interfaces:**
- Consumes: `Session.isResponsible` (Task 8); the backend route of Task 7.
- Produces:
  - **`EmployeeRepository.punchFor(String token, String employeeId) -> Future<TimeEntry>`**, with a fresh idempotency key per confirmed click.
  - **`PunchForEmployeeButton(employee: Employee)`**:
    - it shows the dialog « Faire pointer {matricule} maintenant ? » with « Annuler » / « Faire pointer »;
    - on success, the SnackBar « Entrée enregistrée pour {matricule} à HH:mm » (or « Sortie … »);
    - on error, a SnackBar with the `ApiException` message;
    - the button is disabled while the request is running;
    - it is hidden for inactive employees.
  - **`EmployeeMobileScreen`**: a searchable list (matricule search, the same `employeeControllerProvider`), built from `EmployeeCard` with the button. It is reached from `PunchScreen` by the « Employés » action. The manager's own « POINTER » stays unchanged.

- [ ] **Step 1: Write the failing tests:**
  - confirm → `punchFor` is called exactly once, even on a double tap;
  - cancel → it is not called;
  - the success SnackBar text;
  - the button is absent for an inactive employee;
  - on `PunchScreen`, the « Employés » action is visible with an HR session and absent with an EMPLOYEE session. Extend `FakeSession` with a `role` parameter that builds a token carrying it.
- [ ] **Step 2: Run** `flutter test test/features/employee test/features/punch`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS.
- [ ] **Step 5: Commit (frontend):** `feat: manager can punch for an employee`.

---

### Task 11: Back-office « Anomalies » screen

**Files:**
- Create:
  - `frontend/lib/features/anomaly/anomaly_model.dart`
  - `frontend/lib/features/anomaly/anomaly_repository.dart`
  - `frontend/lib/features/anomaly/anomaly_controller.dart`
  - `frontend/lib/features/anomaly/screens/anomaly_web_screen.dart`
  - `frontend/lib/features/anomaly/widgets/anomaly_table.dart`
  - `frontend/lib/features/anomaly/widgets/anomaly_card.dart`
  - `frontend/lib/features/anomaly/widgets/anomaly_detail_view.dart`
- Modify: `frontend/lib/main_admin.dart` (`NavItem(label: 'Anomalies', icon: Icons.report_problem_outlined, ...)`)
- Test:
  - `frontend/test/features/anomaly/unit/anomaly_controller_test.dart`
  - `frontend/test/features/anomaly/unit/anomaly_model_test.dart`
  - `frontend/test/features/anomaly/widget/anomaly_web_screen_test.dart`

**Interfaces:**
- Consumes: the routes of Task 6; `ApiClient.getBytes` (Task 8); `Paged`; the responsive patterns of the employee screens (`core/layout/breakpoints.dart`, table vs cards).
- Produces:
  - **`Anomaly.fromJson`** with the fields of Task 6's item. The status filter defaults to `OPEN`.
  - **`AnomalyRepository`** methods: `list(token, {status, limit, offset})`, `photo(token, id) -> Uint8List`, `validate(token, id, {comment})`, `reject(token, id, comment)`.
  - **The list columns:** « Employé » (name + matricule), « Pointé depuis le téléphone de », « Date / heure », « Entrée/Sortie », « Statut ».
  - **The detail view:**
    - the selfie, large, through `Image.memory`, with a placeholder when there is none;
    - the punch information;
    - « Valider » (optional comment);
    - « Rejeter », which opens a dialog where the comment is mandatory and the « Rejeter » button stays disabled while the field is blank.
  - After a decision, the list is refreshed, and the decided anomaly leaves the `OPEN` filter.

- [ ] **Step 1: Write the failing tests:**
  - model parsing;
  - the controller loads `OPEN` by default;
  - after `reject`, the controller refreshes and the item is gone;
  - the widget test: the reject dialog button is disabled with an empty comment and enabled with text;
  - an `ApiException('Cette anomalie a déjà été traitée.')` is shown in a SnackBar.
- [ ] **Step 2: Run** `flutter test test/features/anomaly`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS.
- [ ] **Step 5: Commit (frontend):** `feat(admin): anomalies screen to validate or reject assisted punches`.

---

### Task 12: End-to-end check on the real stack

- [ ] **Step 1: Start the stack.** Run `docker compose up -d` in `backend/`, apply `src/sql/migrations/2026-10-27-assisted-punch.sql` to the read database (port 7434), then start the API.
- [ ] **Step 2: Run the backend scenario.** Using `curl` with real tokens (an EMPLOYEE A, an EMPLOYEE B and a MANAGER from seed or onboarding data):
  1. B does an assisted punch for A with a JPEG → 201 `PENDING`;
  2. the MANAGER sees it in `GET /anomalies`;
  3. `GET /anomalies/{id}/photo` returns the image;
  4. the MANAGER validates it → `GET /daily-time-results` for A shows the punch counted;
  5. a second assisted punch rejected with a comment does not change the worked time;
  6. the MANAGER punches for A → `COUNTED` immediately.
- [ ] **Step 3: Check the apps.** Run `flutter run -d chrome -t lib/main_admin.dart` and walk « Anomalies » and « Faire pointer ». Run the mobile flow on a device or emulator with the camera.
- [ ] **Step 4: Report.** Report what passed and anything that did not, with its output.
