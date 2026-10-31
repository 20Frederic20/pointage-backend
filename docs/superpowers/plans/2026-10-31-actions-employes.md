# Actions sur les employés — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Responsible roles can edit, deactivate/reactivate and assign employees (including future transfers). One person can hold employee records in several companies, and login asks which company to use.

**Architecture:**
- New Employee and EmployeeAssignment events: role change, activation, company, assignment cancel.
- Identity commands enforce a role ceiling.
- Assignment creation becomes a transfer that ends or cancels the current assignment in the same unit of work.
- Auth tokens carry `employee_id` and the record's role, with a short "selection" token when several companies are active.
- The Flutter back-office and mobile apps get the actions and a company-choice step at login.

**Tech Stack:**
- Backend: Python 3.14, FastAPI, SQLAlchemy async, event store (Postgres), pytest.
- Frontend: Flutter, Riverpod 3, `http`.

**Spec:** `backend/docs/superpowers/specs/2026-10-31-actions-employes-design.md`

**Repos:** `backend/` and `frontend/` are separate git repos, both on base `feature/employee-screens`.
- Backend tests: `.venv/bin/pytest -q --ignore=tests/test_event_sourcing_postgres.py` from `backend/`.
- Frontend tests: `flutter test` + `flutter analyze` from `frontend/`.

## Global Constraints

- **Responsible roles:** `Role.MANAGER, Role.HR, Role.PAYROLL, Role.ADMIN`. Every new or changed mutating route uses `require_role(...)` with exactly these four. Handlers re-check with `Role(actor_role).at_least(Role.MANAGER)`.
- **Role ceiling** (rank `EMPLOYEE < MANAGER < HR < PAYROLL < ADMIN`). Each violation → 403 `ROLE_CEILING`.
  - An actor never changes the role of any of their own records (same `user_id`).
  - An actor never grants a role above their own.
  - An actor never edits, deactivates or reactivates a record whose role is above their own.
- **Self-deactivation:** an actor never deactivates a record that belongs to them (same `user_id`) → 403 `SELF_DEACTIVATION`.
- **Company:**
  - A company is a **root directory** (`parent_directory_id is None`).
  - Every Employee stores `company_directory_id`, which is the root of the directory chosen at onboarding.
  - An assignment's directory must be that root or one of its descendants → 422 `DIRECTORY_OUTSIDE_COMPANY`.
  - A person has **at most one active employee record per company**, at onboarding and at reactivation → 409 `ALREADY_ACTIVE_IN_COMPANY`.
- **Transfer.** When assigning with `start_date` S:
  - S < today (UTC date) → 422 `ASSIGNMENT_IN_PAST`.
  - An assignment starting **after** S exists and is not cancelled → 409 `FUTURE_ASSIGNMENT_EXISTS`.
  - The assignment covering S that starts **before** S is ended at S − 1 day.
  - The assignment starting **on** S is cancelled (`EmployeeAssignmentCancelled`).
  - All of this happens in one unit of work with the new assignment.
- **Deactivation:**
  - It is employee-level (`Employee.is_active`). The User account is untouched.
  - An inactive record cannot punch through any path: normal, assisted or manager. Code `EMPLOYEE_INACTIVE` (409).
  - Past entries and assignments are untouched.
- **Login.** Inactive records never count.
  - **By matricule:** the record is that matricule's. Inactive → `InvalidCredentialsError` (same 401 as a bad password).
  - **By email:**
    - 0 active records but ≥ 1 record → `NO_ACTIVE_EMPLOYMENT` (403);
    - no record at all → current behaviour, with the User's role and `employee_id = null`;
    - 1 active record → tokens for that record;
    - ≥ 2 active records → `selection_required` with a 5-minute selection token (`typ: "employee_selection"`).
  - **Access token claims:** `sub`, `role` (the record's role, or the User's when there is no record), `employee_id` (string or null), `typ: "access"`.
  - **Refresh:** it keeps the session's `employee_id`. If that record is now inactive → the refresh is revoked, giving 401 `INVALID_REFRESH_TOKEN`.
- **Existing data:** a one-off script activates every existing Employee and backfills `company_directory_id`. Onboarding defaults to `is_active = true` (API and form).
- **Compatibility:**
  - Old `users.employee.*`, `users.employee_assignment.*` and refresh-token rows must load. New payload keys are read with `.get(..., default)`.
  - Read-model changes go in `src/sql/read_model.sql` and `src/sql/migrations/2026-10-31-employee-actions.sql`.
  - Write-DB changes go in `src/sql/event_store.sql` and the same migration file, in a clearly separated "write database" section.
  - All SQL is idempotent: `ADD COLUMN IF NOT EXISTS`.
- **Copy:** UI text is in French, in the tone of `frontend/lib/core/api_client.dart`. New error codes get `_messages` entries (Task 11).
- **Known baseline failure:** `tests/test_sites.py::test_punch_on_a_deactivated_site_is_refused` already fails before any change. It is not a regression.

## Review Focus

1. **A transfer scheduled today for a future date, while the employee keeps punching today.** Punches must still use today's site until S. Test in Task 3.
2. **A person active in two companies, deactivated in one.** Email login must go straight into the other company, with no choice screen. Test in Task 8.
3. **A refresh token issued before this change has no `employee_id`.** For an account with records, it must still refresh, binding the single active record if there is exactly one, else 401 to force a new login. Test in Task 8.
4. **An actor holding records in two companies with different roles.** The ceiling uses the **token's** role (the record they logged in with), not their highest role. Test in Task 4.
5. **Two quick taps on « Désactiver » or « Affecter ».** One mutation only, and the second gets a clear message rather than a crash. Test in Task 12.

---

### Task 1: Employee domain — role change, activation, company

**Files:**
- Modify:
  - `backend/src/identity/domain/entities/employee.py`
  - `backend/src/identity/domain/events/employee_events.py`
  - `backend/src/identity/domain/events/__init__.py`
  - `backend/src/identity/infrastructure/persistence/event_sourced_employee_repository.py`
  - `backend/src/identity/application/notifications.py`
  - `backend/src/identity/infrastructure/persistence/models.py`
  - `backend/src/identity/infrastructure/persistence/employee_repository.py`
  - `backend/src/identity/application/dtos/employee_dtos.py`
  - `backend/src/sql/read_model.sql`
- Create: `backend/src/sql/migrations/2026-10-31-employee-actions.sql`
- Test: `backend/tests/test_identity_event_sourcing.py` (add tests)

**Interfaces — produces:**
- **`Employee.create(...)`** gains `company_directory_id: DirectoryId | None = None`, carried on `EmployeeCreated` (payload key `company_directory_id`, read with `.get`) and on `EmployeeImported`.
- **Methods**
  - `Employee.change_role(role: Role) -> None` raises `EmployeeRoleChanged` (`"users.employee.role_changed"`, payload `employee_id, role`). It records nothing if the role is unchanged.
  - `Employee.change_phone(phone: str | None) -> None` reuses `update(employee_number=None, is_active=None, phone=phone)`.
  - `Employee.deactivate() -> None` raises `EmployeeDeactivated` (`"users.employee.deactivated"`). On an already inactive record, it raises `ConflictError` with code `EMPLOYEE_ALREADY_INACTIVE` (409).
  - `Employee.activate() -> None` raises `EmployeeActivated` (`"users.employee.activated"`). On an already active record, it raises `ConflictError` with code `EMPLOYEE_ALREADY_ACTIVE` (409).
  - `Employee.set_company(directory_id: DirectoryId) -> None` raises `EmployeeCompanySet` (`"users.employee.company_set"`, payload `employee_id, company_directory_id`). It is used only by the backfill script.
- **Property:** `company_directory_id: DirectoryId | None`.
- **Wiring:** all four events are registered in `EMPLOYEE_EVENT_TYPES`, in `events.__all__` and in the notification mappers (map to `None` if unpublished, as `EmployeeImported` does).
- **Read model:** the `employees.company_directory_id varchar(32)` column is nullable. `EmployeeModel` and `EmployeeRepository._insert` / `_update` / `_to_aggregate` read and write it, and `_update` also writes `role`.
- **DTO:** `EmployeeDTO` gains `company_directory_id: str | None`.

- [ ] **Step 1: Write the failing tests:**
  - `test_employee_role_change_activation_and_company_replay`:
    - create with `company_directory_id=DirectoryId("dir1")`;
    - `change_role(Role.HR)`, `deactivate()`, `activate()`, `set_company(DirectoryId("dir2"))`;
    - after the JSON round-trip replay, check role HR, active, company `dir2`.
  - `test_deactivate_twice_or_activate_active_is_conflict`.
  - `test_change_role_to_same_role_records_nothing`.
  - `test_legacy_employee_created_payload_has_no_company`: drop `company_directory_id` from the payload, then check `company_directory_id is None`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_identity_event_sourcing.py -v`. Expected: FAIL (`AttributeError` on `change_role`).
- [ ] **Step 3: Implement the domain.**
- [ ] **Step 4: Implement the read model.** Add the column in `read_model.sql` and in the migration, whose header comment marks the read-database section: `ALTER TABLE employees ADD COLUMN IF NOT EXISTS company_directory_id varchar(32);`.
- [ ] **Step 5: Run the full backend suite.** Expected: only the baseline failure.
- [ ] **Step 6: Commit (backend):** `feat(identity): employee role change, activation and company`.

---

### Task 2: Assignment cancel and company tree helper

**Files:**
- Modify:
  - `backend/src/identity/domain/entities/employee_assignment.py`
  - the events file and `__init__` that define `EmployeeAssigned`
  - `backend/src/identity/infrastructure/persistence/event_sourced_employee_assignment_repository.py`
  - the state assignment repository and model (`employee_assignment_repository.py`, `models.py`)
  - `backend/src/identity/application/notifications.py`
  - `backend/src/sql/read_model.sql` + the migration
- Create: `backend/src/identity/application/services/company_service.py`
- Test:
  - `backend/tests/test_identity_event_sourcing.py`
  - `backend/tests/identity/unit/test_company_service.py`

**Interfaces — produces:**
- **`EmployeeAssignment.cancel() -> None`** raises `EmployeeAssignmentCancelled` (`"users.employee_assignment.cancelled"`, payload `employee_assignment_id`). It is valid only while not already cancelled, else `ConflictError`.
- **Cancelled state:** the property `is_cancelled: bool`. `is_active_on(day)` returns `False` when cancelled.
- **Repositories:** both assignment repositories exclude cancelled assignments from `find_active`, `exists_overlapping` and `find_by_employee`. The read model gets the column `employee_assignments.cancelled boolean DEFAULT false NOT NULL`, also in the migration.
- **`CompanyService(directory_repository)`**
  - `async root_of(directory_id: DirectoryId) -> DirectoryId` walks `parent_directory_id` up to the root.
  - `async is_within(company_id: DirectoryId, directory_id: DirectoryId) -> bool` is true when `root_of(directory_id) == company_id`.
  - Guard: stop after 32 levels and raise `ConflictError` (a cycle guard).

- [ ] **Step 1: Write the failing tests:**
  - `test_cancelled_assignment_replays_and_is_never_active`.
  - `test_cancel_twice_is_conflict`.
  - `test_root_of_walks_to_root`: a root `R`, a child `C`, a grandchild `G` → `root_of(G) == R`, `is_within(R, G)`, and `not is_within(R, other_root)`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement** them. The event-sourced repository filters in Python, so add `if a.is_cancelled: continue` wherever it iterates.
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(identity): cancellable assignments and company tree helper`.

---

### Task 3: Transfer — assign with automatic end or cancel, role-guarded routes

**Files:**
- Modify:
  - `backend/src/identity/application/handlers/assign_employee_handler.py`
  - `backend/src/identity/application/handlers/end_employee_assignment_handler.py`
  - `backend/src/identity/application/commands/assign_employee.py`
  - `backend/src/identity/application/commands/end_employee_assignment.py`
  - `backend/src/identity/domain/errors/errors.py`
  - `backend/src/identity/interface/routers/employee_assignments_router.py`
  - `backend/src/identity/interface/schemas.py` (`EmployeeAssignmentResponse` + names)
  - `backend/src/identity/infrastructure/container.py`
  - `backend/src/identity/application/handlers/get_employee_assignments_handler.py`
- Test: `backend/tests/identity/unit/test_transfer_employee.py`, `backend/tests/identity/api/test_assignments_api.py`

**Interfaces:**
- Consumes: `cancel`, `is_cancelled` and `CompanyService` (Task 2); `Employee.company_directory_id` (Task 1).
- Produces:
  - **Commands:** `AssignEmployeeCommand` gains `actor_user_id: str` and `actor_role: str`, and so does `EndEmployeeAssignmentCommand`.
  - **`AssignEmployeeHandler` order:**
    1. role check and target ceiling;
    2. employee active (inactive → `EMPLOYEE_INACTIVE`);
    3. `start_date >= today_utc` (`ASSIGNMENT_IN_PAST`);
    4. `CompanyService.is_within(employee.company_directory_id, directory_id)`, skipped when the company is None (a legacy record before the backfill);
    5. site resolution, as today;
    6. among the employee's non-cancelled assignments: a start > S → `FUTURE_ASSIGNMENT_EXISTS`; one covering S with start < S → `end(S - 1 day)`; one with start == S → `cancel()`;
    7. create the new assignment.

    It returns `EmployeeAssignmentDTO`. The aggregates are the new assignment plus the ended or cancelled one.
  - **Error classes:** `AssignmentInPastError` (422 `ASSIGNMENT_IN_PAST`), `FutureAssignmentExistsError` (409 `FUTURE_ASSIGNMENT_EXISTS`), `DirectoryOutsideCompanyError` (422 `DIRECTORY_OUTSIDE_COMPANY`), `EmployeeInactiveError` (409 `EMPLOYEE_INACTIVE`, defined in `identity.domain.errors` and reused by punch in Task 9), `RoleCeilingError` (403 `ROLE_CEILING`) and `SelfDeactivationError` (403 `SELF_DEACTIVATION`).
  - **Routes:** `POST /employee-assignments` and `POST /employee-assignments/{id}/end` get `require_role(...)`.
  - **Responses:** `GET /employee-assignments?employee_id=` items gain `siteName`, `directoryName` and `cancelled`. The list excludes cancelled items by default.
  - **Shared helper** `identity/application/services/responsible_rules.py`:
    - `ensure_responsible(actor_role: str) -> Role`
    - `ensure_can_manage(actor_role: Role, target_role: Role) -> None` (target above actor → `RoleCeilingError`)
    - `ensure_can_grant(actor_role: Role, new_role: Role) -> None`

    Tasks 4 and 5 reuse it.

- [ ] **Step 1: Write the failing unit tests**, with handler + in-memory repos in the `tests/test_auth.py` style. Freeze "today" by injecting a `clock: Callable[[], date]` into the handler, defaulting to the UTC date.
  - `test_transfer_ends_current_assignment_the_day_before`: current from 2026-10-01 open-ended, new S = 2026-11-03 → current `end_date == 2026-11-02`, new from 2026-11-03.
  - `test_transfer_on_same_start_day_cancels_current`.
  - `test_future_assignment_conflict_is_409`.
  - `test_start_in_past_is_422`.
  - `test_directory_outside_company_is_422`; a sub-directory of the company passes.
  - `test_inactive_employee_cannot_be_assigned`.
  - `test_manager_cannot_assign_an_admin`, which returns `ROLE_CEILING`.
  - `test_punch_site_today_unchanged_by_future_transfer` (Review Focus 1): after scheduling S = today + 7, `find_active(employee, today)` still returns the old site.
- [ ] **Step 2: Write the failing API tests:** EMPLOYEE → 403 on both POST routes; the list items carry `siteName` / `directoryName`.
- [ ] **Step 3: Run** them. Expected: FAIL.
- [ ] **Step 4: Implement.**
- [ ] **Step 5: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 6: Commit (backend):** `feat(identity): transfers end or cancel the current assignment`.

---

### Task 4: Edit, deactivate and reactivate an employee

**Files:**
- Create:
  - `backend/src/identity/application/commands/edit_employee.py`
  - `backend/src/identity/application/commands/set_employee_active.py`
  - `backend/src/identity/application/handlers/edit_employee_handler.py`
  - `backend/src/identity/application/handlers/set_employee_active_handler.py`
- Modify:
  - `backend/src/identity/interface/routers/employees_router.py` (replace the PATCH stub)
  - `backend/src/identity/interface/schemas.py` (`UpdateEmployeeRequest`)
  - `backend/src/identity/infrastructure/container.py`
  - `backend/src/identity/domain/repositories/employee_repository.py` + the event-sourced implementation (`find_all_by_user_id`)
- Test:
  - `backend/tests/identity/unit/test_edit_employee_handler.py`
  - `backend/tests/identity/unit/test_set_employee_active_handler.py`
  - `backend/tests/identity/api/test_employees_api.py`

**Interfaces:**
- Consumes: Task 1 methods; `responsible_rules` and the error classes (Task 3).
- Produces:
  - **`EditEmployeeCommand(actor_user_id, actor_role, employee_id, first_name: str | None, last_name: str | None, phone: str | None, role: Role | None)`** returns `EmployeeDTO`.
    - The handler loads the Employee and its User.
    - It runs the ceiling checks: the actor can manage the target; a new role must not exceed the actor's; a role change on the actor's own record → `ROLE_CEILING`.
    - It then calls `User.update_profile(first_name=, last_name=)`, `Employee.change_phone`, `Employee.change_role`, and persists `[user, employee]`.
  - **`SetEmployeeActiveCommand(actor_user_id, actor_role, employee_id, active: bool)`** returns `EmployeeDTO`.
    - Checks: ceiling; self → `SelfDeactivationError`, for deactivation only.
    - On activation, a person already active in the same company (`find_all_by_user_id` filtered by `company_directory_id`) → `ALREADY_ACTIVE_IN_COMPANY` (`AlreadyActiveInCompanyError`, 409).
  - **`IEmployeeWriteRepository.find_all_by_user_id(user_id: UserId) -> list[Employee]`**, also used in Tasks 5, 8 and 9.
  - **Routes**, all with `require_role(...)`:
    - `PATCH /employees/{employee_id}` with body `{firstName?, lastName?, phone?, role?}` (camelCase aliases).
    - `POST /employees/{employee_id}/deactivate` and `POST /employees/{employee_id}/activate`.
    - They return `EmployeeResponse`.

- [ ] **Step 1: Write the failing tests:**
  - `test_edit_updates_user_names_and_employee_phone_and_role`.
  - `test_manager_cannot_grant_hr`.
  - `test_cannot_change_own_role`.
  - `test_manager_cannot_edit_or_deactivate_admin`.
  - `test_ceiling_uses_token_role_not_highest_record` (Review Focus 4): the actor's token role is MANAGER while they also hold an ADMIN record elsewhere → granting HR is refused.
  - `test_cannot_deactivate_self`.
  - `test_reactivate_refused_when_active_elsewhere_in_same_company`.
  - `test_deactivate_keeps_assignments_and_user_account_active`.
  - API: EMPLOYEE → 403 on all three routes; PATCH returns the new phone and role.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(identity): edit, deactivate and reactivate employees`.

---

### Task 5: Onboarding reuses an existing account; company stored; active by default

**Files:**
- Modify:
  - `backend/src/identity/application/handlers/onboard_employee_handler.py`
  - `backend/src/identity/application/commands/onboard_employee.py`
  - `backend/src/identity/interface/schemas.py` (`OnboardEmployeeRequest.is_active` default `True`; response flag)
  - `backend/src/identity/interface/routers/employees_router.py`
- Test: `backend/tests/identity/unit/test_onboard_employee_handler.py` (extend)

**Interfaces:**
- Consumes: `CompanyService.root_of` (Task 2); `find_all_by_user_id` (Task 4); `Employee.create(company_directory_id=)` (Task 1).
- Produces:
  - **Existing email:** when the email exists, the handler reuses that User. It ignores `first_name`, `last_name` and `password`, and does not change the User's role. It then creates the Employee and the assignment as today.
  - **Company:** `company_directory_id = root_of(directory_id)` is always set.
  - **One active record per company:** a person already active in that company → `ALREADY_ACTIVE_IN_COMPANY`.
  - **Defaults:** `is_active` defaults to `True` (command and request).
  - **Responses:** the onboard route keeps `require_role(Role.ADMIN)`. It now also accepts MANAGER, HR and PAYROLL, with the ceiling `ensure_can_grant(actor, request.role)`; the command gains `actor_user_id` and `actor_role`. The response is `EmployeeResponse` plus `accountReused: bool`.

- [ ] **Step 1: Write the failing tests:**
  - `test_onboard_with_existing_email_reuses_account_and_creates_second_record`: same `user_id`, new matricule, `company_directory_id` = the root, `account_reused`.
  - `test_onboard_same_company_twice_is_409`.
  - `test_onboard_defaults_to_active`.
  - `test_onboard_stores_company_root_for_subdirectory`.
  - `test_manager_cannot_onboard_an_admin`.
  - Also update the existing tests that assumed `EMAIL_ALREADY_REGISTERED`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(identity): onboarding reuses an existing account per company`.

---

### Task 6: Employee read enrichment (names, company, current site)

**Files:**
- Modify:
  - `backend/src/identity/application/dtos/employee_dtos.py`
  - `backend/src/identity/application/handlers/get_employees_handler.py`
  - `backend/src/identity/application/handlers/get_employee_by_id_handler.py`
  - `backend/src/identity/interface/schemas.py` (`EmployeeResponse`)
  - `backend/src/identity/infrastructure/container.py`
- Test: `backend/tests/identity/api/test_employees_api.py`, `backend/tests/identity/conftest.py` (fakes)

**Interfaces — produces:** `EmployeeResponse` gains these nullable fields: `firstName`, `lastName`, `companyDirectoryId`, `companyName`, `currentSiteId`, `currentSiteName`, `currentAssignmentEndDate`.
- The query handlers enrich each item from the read repositories: user by `user_id`, directory by `company_directory_id`, and the active assignment today plus its site.
- ponytail: one lookup per item on a 20-item page. Batch it if pages grow.
- The `identity_api` fixture gets in-memory user, directory, site and assignment read fakes.

- [ ] **Step 1: Write the failing test** `test_list_and_detail_include_names_company_and_current_site`, with one record that has no assignment, whose site fields are null.
- [ ] **Step 2: Run** it. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(identity): employee responses carry names, company and current site`.

---

### Task 7: One-off backfill script

**Files:**
- Create: `backend/src/scripts/activate_and_backfill_employees.py`
- Test: `backend/tests/identity/unit/test_backfill_employees.py`

**Interfaces:**
- Consumes: `Employee.activate()`, `Employee.set_company()` (Task 1); `CompanyService` (Task 2); assignment `find_by_employee`.
- Produces: `async def backfill(employee_repository, assignment_repository, company_service, unit_of_work) -> tuple[int, int]`, which returns `(activated, companies_set)`.
  - For each employee: if inactive → `activate()`; if `company_directory_id` is None → `set_company(root_of(earliest assignment's directory))`, skipped when there is no assignment.
  - Re-running it changes nothing.
  - The `main()` entry point follows the style of `scripts/import_state_to_event_store.py`. Its docstring gives the run command: `uv run python -m scripts.activate_and_backfill_employees` from `src/`.
  - It lists employees through the event store (`find_stream_ids` / `load_streams` on the employee stream).

- [ ] **Step 1: Write the failing tests:**
  - `test_backfill_activates_inactive_and_sets_company`;
  - `test_backfill_is_idempotent` (second run returns `(0, 0)`);
  - `test_backfill_skips_company_without_assignment`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** them. Expected: PASS.
- [ ] **Step 5: Commit (backend):** `feat(scripts): activate existing employees and backfill their company`.

---

### Task 8: Auth — record-bound tokens, company selection, refresh

**Files:**
- Modify:
  - `backend/src/auth/application/ports.py`
  - `backend/src/auth/infrastructure/jwt_token_issuer.py`
  - `backend/src/auth/application/dtos/*` (`PrincipalDTO`, `AccountCredentialsDTO`, new DTOs)
  - `backend/src/auth/application/handlers/login_handler.py`
  - `backend/src/auth/application/handlers/verify_login_code_handler.py`
  - `backend/src/auth/application/handlers/refresh_session_handler.py`
  - `backend/src/auth/domain/entities/refresh_token.py`
  - `backend/src/auth/infrastructure/persistence/models.py` + the refresh-token repository
  - `backend/src/auth/infrastructure/identity_user_accounts.py`
  - `backend/src/auth/infrastructure/container.py`
  - `backend/src/auth/interface/routers/auth_router.py`
  - `backend/src/auth/interface/schemas.py`
  - `backend/src/sql/event_store.sql` + the migration (write-DB section)
  - identity: a `GetEmployeesByUserIdQuery` and its handler (read side), plus wiring
- Create:
  - `backend/src/auth/application/commands/select_employee.py`
  - `backend/src/auth/application/handlers/select_employee_handler.py`
  - `backend/src/auth/application/services/employment_resolver.py`
- Test: `backend/tests/test_auth.py` (extend `FakeUserAccounts` and the `env` fixture)

**Interfaces:**
- Consumes: the employee records of a user, through `UserAccounts.employments(user_id) -> list[EmploymentDTO]`.
- Produces:
  - **DTOs**
    - `EmploymentDTO(employee_id: str, company_name: str | None, role: str, is_active: bool)`.
    - `AccountCredentialsDTO` gains `employee_id: str | None`, set only when the identifier was a matricule.
    - `PrincipalDTO` gains `employee_id: str | None = None`.
    - `SelectionRequiredDTO(selection_token: str, employments: tuple[EmploymentDTO, ...])`.
  - **Tokens**
    - `TokenIssuer.issue_access_token(*, user_id, role, employee_id: str | None)`. The claim `employee_id` is decoded into `PrincipalDTO`; old tokens without the claim give `None`.
    - `TokenIssuer.issue_selection_token(*, user_id) -> str`, with `typ "employee_selection"`, exp 300 s.
    - `TokenIssuer.decode_selection_token(token) -> str`, which returns `user_id` or raises `InvalidAccessTokenError`.
  - **`EmploymentResolver.resolve(account, employments, matricule_employee_id) -> ResolvedEmployment | SelectionRequired | NoActiveEmployment`.** It implements the login rules of the Global Constraints. `NO_ACTIVE_EMPLOYMENT` is `NoActiveEmploymentError` (403).
  - **Handlers:** `LoginHandler` and `VerifyLoginCodeHandler` return `TokenPairDTO | SelectionRequiredDTO`.
  - **`SelectEmployeeCommand(selection_token, employee_id)`** returns `TokenPairDTO`.
    - The employee must be one of the user's **active** records, else 403 `NO_ACTIVE_EMPLOYMENT`.
    - It starts the session exactly like login.
  - **Refresh tokens**
    - `RefreshToken.start_session(..., employee_id: str | None)` and `rotate` carry `employee_id`.
    - The column `refresh_tokens.employee_id varchar(32)` is nullable.
  - **`RefreshSessionHandler`**
    - If the session's `employee_id` is set and that record is inactive or missing → revoke and return `None`, which gives 401.
    - If the session's `employee_id` is None and the account has records: exactly 1 active → bind it (`token.rotate` carries the new id); otherwise → revoke, which gives 401 (Review Focus 3).
    - The role comes from the bound record.
  - **Routes**
    - `POST /auth/login` and `POST /auth/otp/verify` return either `TokenPairResponse` or `SelectionRequiredResponse{status: "selection_required", selectionToken, employments: [{employeeId, companyName, role}]}`. A token pair carries `status: "authenticated"`.
    - `POST /auth/select-employee` with body `{selectionToken, employeeId}` returns `TokenPairResponse`.
    - `GET /auth/me` adds `employeeId`.

- [ ] **Step 1: Write the failing tests** in `tests/test_auth.py`:
  - `test_login_by_matricule_binds_that_record`: the token carries `employee_id` and that record's role.
  - `test_login_by_matricule_of_inactive_record_is_invalid_credentials`.
  - `test_login_by_email_single_active_record_returns_tokens`.
  - `test_login_by_email_two_active_records_requires_selection_then_select_issues_bound_token`.
  - `test_deactivated_in_one_company_logs_straight_into_the_other` (Review Focus 2).
  - `test_all_records_inactive_is_no_active_employment`.
  - `test_account_without_records_keeps_user_role`.
  - `test_selection_token_expired_or_forged_is_401`.
  - `test_select_employee_not_owned_or_inactive_is_403`.
  - `test_refresh_after_deactivation_is_401`.
  - `test_legacy_refresh_without_employee_binds_single_active_record` and `test_legacy_refresh_with_two_active_records_is_401`.
  - `test_otp_login_follows_same_selection_rules`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_auth.py -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.** Add the write-DB migration: `ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS employee_id varchar(32);`.
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(auth): company selection and record-bound sessions`.

---

### Task 9: Punch and decisions use the session's record; inactive records cannot punch

**Files:**
- Modify:
  - `backend/src/punch/interface/routers/time_entries_router.py`
  - `backend/src/punch/application/commands/create_time_entry.py`
  - `backend/src/punch/application/handlers/create_time_entry_handler.py`
  - `backend/src/punch/application/handlers/create_assisted_time_entry_handler.py`
  - `backend/src/punch/application/handlers/create_manager_time_entry_handler.py`
  - `backend/src/punch/application/handlers/lookup_employee_handler.py`
  - `backend/src/adjustements/application/handlers/decide_anomaly_handler.py`
- Test:
  - `backend/tests/punch/api/test_assisted_punch_api.py`
  - `backend/tests/punch/api/test_manager_punch_api.py`
  - `backend/tests/punch/api/test_punch_api.py` (create if missing)
  - `backend/tests/adjustements/api/test_anomalies_api.py`

**Interfaces:**
- Consumes: `PrincipalDTO.employee_id` (Task 8), `find_all_by_user_id` (Task 4), `EmployeeInactiveError` (Task 3).
- Produces:
  - **`CreateTimeEntryCommand`** gains `employee_id: str | None`. When it is set, the handler loads that record and checks it belongs to `user_id`, else `NotFoundError`. When it is None, the handler falls back to `find_by_user_id`.
  - **Inactive records:**
    - the normal punch on an inactive record → `EmployeeInactiveError` (409 `EMPLOYEE_INACTIVE`);
    - the assisted punch, the manager punch and the lookup keep their 404 for unknown employees and **switch inactive to `EMPLOYEE_INACTIVE`**. The lookup still returns no name.
  - **Self-decision:** `DecideAnomalyHandler` compares `{anomaly.employee_id, time_entry.employee_id}` against **all** of the actor's records (`find_all_by_user_id`).

- [ ] **Step 1: Write the failing tests:**
  - `test_normal_punch_uses_token_employee_id`;
  - `test_normal_punch_inactive_record_is_409`;
  - `test_assisted_and_manager_punch_inactive_is_409_employee_inactive`;
  - `test_actor_cannot_decide_anomaly_of_any_of_their_records`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite.** Expected: only the baseline failure.
- [ ] **Step 5: Commit (backend):** `feat(punch): session-bound employee and inactive records cannot punch`.

---

### Task 10: Frontend — login company selection and session company

**Files:**
- Modify:
  - `frontend/lib/features/auth/auth_repository.dart`
  - `frontend/lib/features/auth/session_provider.dart`
  - `frontend/lib/features/auth/login_screen.dart`
- Create: `frontend/lib/features/auth/company_choice_screen.dart`
- Test:
  - `frontend/test/features/auth/unit/auth_repository_test.dart`
  - `frontend/test/features/auth/widget/company_choice_screen_test.dart`
  - `frontend/test/features/auth/unit/session_role_test.dart` (extend)

**Interfaces:**
- Consumes: the Task 8 routes.
- Produces:
  - **`sealed class LoginResult`**, with `LoginAuthenticated(TokenPair)` and `LoginSelectionRequired(String selectionToken, List<Employment> employments)`, where `Employment(employeeId, companyName?, role)`.
    - `AuthRepository.loginWithPassword` and `verifyCode` return `LoginResult`.
    - New `AuthRepository.selectEmployee(selectionToken, employeeId) -> Future<TokenPair>`.
  - **Session**
    - `Session.employeeId` (a getter decoded from the JWT `employee_id` claim, nullable).
    - `Session.companyName`: stored, nullable, persisted in `toJson`/`fromJson`, kept across `_refresh`, and set from the chosen `Employment`.
    - `SessionNotifier.signIn(TokenPair, identifier, {String? companyName})`.
  - **`CompanyChoiceScreen`**
    - Title « Dans quelle entreprise voulez-vous vous connecter ? ».
    - One `ListTile` per employment: the company name (or « Entreprise inconnue ») and the role label.
    - Tapping a tile calls `selectEmployee`, then `signIn`.
    - A back button returns to login.
  - **Header:** `PunchScreen` and the `AdminShell` header show `session.companyName` when it is not null.
  - **Error message:** `_messages['NO_ACTIVE_EMPLOYMENT']` = « Aucun accès actif : contactez votre responsable. ».

- [ ] **Step 1: Write the failing tests:**
  - parsing of both login responses;
  - `selectEmployee` posts `{selectionToken, employeeId}`;
  - the choice screen lists two companies, and a tap signs in with the chosen company name;
  - the session JSON round-trips `companyName`;
  - `employeeId` is decoded from a JWT.
- [ ] **Step 2: Run** `flutter test test/features/auth`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS, no issues.
- [ ] **Step 5: Commit (frontend):** `feat(auth): choose the company at login`.

---

### Task 11: Frontend — employee data and API methods

**Files:**
- Modify:
  - `frontend/lib/core/api_client.dart` (`patch`, messages)
  - `frontend/lib/features/employee/employee_model.dart`
  - `frontend/lib/features/employee/employee_repository.dart`
  - `frontend/lib/features/directory/directory_model.dart` (`parentDirectoryId`)
- Create: `frontend/lib/features/employee/assignment_model.dart`
- Test:
  - `frontend/test/core/unit/api_client_test.dart`
  - `frontend/test/features/employee/unit/employee_model_test.dart`
  - `frontend/test/features/employee/unit/employee_repository_test.dart`

**Interfaces — produces:**
- **`ApiClient.patch(String path, Map<String, dynamic> body, {String? accessToken}) -> Future<Map<String, dynamic>>`**, with the same error handling as `post`.
- **`Employee`** gains `firstName?`, `lastName?`, `companyDirectoryId?`, `companyName?`, `currentSiteId?`, `currentSiteName?`, `currentAssignmentEndDate?` (`DateTime?`), plus `String get displayName` (« Prénom Nom », or the matricule).
- **`EmployeeDraft.isActive`** defaults to `true`.
- **`Assignment(id, directoryId, directoryName?, siteId, siteName?, startDate, endDate?)`** with `.fromJson`.
- **`EmployeeRepository` methods:**
  - `update(token, id, {firstName, lastName, phone, Role? role}) -> Employee` (PATCH, sending only non-null keys);
  - `deactivate(token, id) -> Employee`;
  - `activate(token, id) -> Employee`;
  - `assignments(token, employeeId) -> List<Assignment>`;
  - `assign(token, {employeeId, directoryId, siteId, startDate, endDate?}) -> Assignment` (snake_case body, as the backend expects);
  - `endAssignment(token, assignmentId, endDate) -> Assignment`.
- **`create(...)`** returns `({Employee employee, bool accountReused})`.
- **`Directory`** gains `parentDirectoryId?` and `bool get isCompany` (`parentDirectoryId == null`).
- **`_messages` entries:**
  - `ROLE_CEILING`: « Vous ne pouvez pas attribuer ou modifier un rôle supérieur au vôtre. »
  - `SELF_DEACTIVATION`: « Vous ne pouvez pas vous désactiver vous-même. »
  - `EMPLOYEE_INACTIVE`: « Cet employé est désactivé. »
  - `EMPLOYEE_ALREADY_INACTIVE`: « Cet employé est déjà désactivé. »
  - `EMPLOYEE_ALREADY_ACTIVE`: « Cet employé est déjà actif. »
  - `ALREADY_ACTIVE_IN_COMPANY`: « Cette personne a déjà une fiche active dans cette entreprise. »
  - `ASSIGNMENT_IN_PAST`: « La date de début ne peut pas être dans le passé. »
  - `FUTURE_ASSIGNMENT_EXISTS`: « Une affectation future existe déjà : terminez-la d'abord. »
  - `DIRECTORY_OUTSIDE_COMPANY`: « Ce service n'appartient pas à l'entreprise de l'employé. »
  - `OVERLAPPING_EMPLOYEE_ASSIGNMENT`: « Cette affectation chevauche une autre affectation. » (only if not already mapped)

- [ ] **Step 1: Write the failing tests:**
  - the `patch` method, error codes included;
  - `Employee.fromJson` with and without the new fields;
  - each repository method's path, method and body;
  - `create` reads `accountReused`.
- [ ] **Step 2: Run** them. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS.
- [ ] **Step 5: Commit (frontend):** `feat(employee): edit, activation and assignment API methods`.

---

### Task 12: Frontend — actions on the employee detail (back-office and mobile)

**Files:**
- Create:
  - `frontend/lib/features/employee/widgets/employee_actions.dart`
  - `frontend/lib/features/employee/widgets/edit_employee_dialog.dart`
  - `frontend/lib/features/employee/widgets/assign_employee_dialog.dart`
  - `frontend/lib/features/employee/widgets/assignment_history.dart`
  - `frontend/lib/features/employee/employee_actions_controller.dart`
- Modify:
  - `frontend/lib/features/employee/widgets/employee_detail_view.dart`
  - `frontend/lib/features/employee/widgets/employee_table.dart`
  - `frontend/lib/features/employee/widgets/employee_card.dart`
  - `frontend/lib/features/employee/widgets/employee_form.dart`
  - `frontend/lib/features/employee/employee_controller.dart` (create flow: `accountReused` message)
- Test:
  - `frontend/test/features/employee/widget/employee_actions_test.dart`
  - `frontend/test/features/employee/widget/assign_employee_dialog_test.dart`
  - `frontend/test/features/employee/unit/employee_actions_controller_test.dart`

**Interfaces:**
- Consumes: the Task 11 repository and model; `Session.role` (to hide roles above the actor's in the role picker).
- Produces:
  - **Detail view.** The detail shows the name, the company and the current site, then `EmployeeActions(employee)`:
    - **« Modifier »** opens a dialog with « Prénom », « Nom », « Téléphone » (10–20 characters when filled) and a « Rôle » dropdown. The dropdown offers only roles ≤ the session's role, and is disabled on the actor's own record (matched by `employee.userId` against the session's user id from the JWT `sub`).
    - **« Désactiver »** asks « Désactiver {nom} ? Il ne pourra plus pointer. ». **« Réactiver »** asks « Réactiver {nom} ? ». Either is shown, depending on `isActive`.
    - **« Affecter à un site »** opens a dialog:
      - company sub-directories (from `allDirectoriesProvider`, filtered to those under `companyDirectoryId`, root included; all of them when the company is null);
      - a site from `directorySitesProvider`;
      - « Date de début » (default today, `firstDate` today);
      - an optional « Date de fin »;
      - when a current site exists, the warning « L'affectation actuelle à {site} se terminera le {veille JJ/MM/AAAA}. ».
    - Below the actions, `AssignmentHistory(employeeId)` lists the assignments, most recent first, with « Terminer » on current or future ones (end date picker, default today).
  - **`EmployeeActionsController`** (autoDispose family by employee id).
    - It runs one mutation at a time: a second call while busy is ignored.
    - After success it invalidates `employeeDetailProvider(id)`, refreshes the list, and shows a SnackBar (« Employé modifié. », « Employé désactivé. », « Employé réactivé. », « Affectation enregistrée. »).
    - On error, it shows the `ApiException` message.
  - **Table and card:** they show `displayName`, `companyName` and `currentSiteName`.
  - **Create form:** the « Actif » switch defaults to on. After creation with `accountReused`, the SnackBar says « Ce compte existait déjà : une nouvelle fiche a été créée dans cette entreprise. ».

- [ ] **Step 1: Write the failing tests:**
  - « Modifier » sends only the changed fields;
  - the role dropdown hides roles above the session's role;
  - the role dropdown is disabled on own record;
  - deactivate confirm → one call, even on a double tap (Review Focus 5); cancel → no call;
  - « Réactiver » shows for an inactive employee;
  - the assign dialog shows the « se terminera le » warning with the right date;
  - the assign dialog cannot pick a past start date;
  - history « Terminer » calls `endAssignment`;
  - an `ApiException` is shown in a SnackBar;
  - the create form's « Actif » is on by default.
- [ ] **Step 2: Run** `flutter test test/features/employee`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `flutter test` and `flutter analyze`. Expected: PASS.
- [ ] **Step 5: Commit (frontend):** `feat(employee): edit, deactivate, reactivate and assign from the employee detail`.

---

### Task 13: End-to-end check (needs Docker)

- [ ] **Step 1: Prepare the stack.**
  - Run `docker compose up -d` in `backend/`.
  - Apply `src/sql/migrations/2026-10-27-assisted-punch.sql` and `2026-10-31-employee-actions.sql`: the read sections on port 7434, the write section on port 7433.
  - Run `uv run python -m scripts.activate_and_backfill_employees` from `src/`.
- [ ] **Step 2: Walk the scenario.**
  1. Onboard a person in company A.
  2. Onboard the same email in company B, which returns `accountReused`.
  3. Log in by email → the company choice appears.
  4. Choose A, then punch.
  5. Deactivate the person in A → the next refresh logs them out → logging in by email goes straight into B.
  6. Schedule a transfer for tomorrow → today's punch still uses the old site.
  7. Check the edit and role-ceiling refusals as a MANAGER.
- [ ] **Step 3: Report.** Report what passed and what did not, with the output.
