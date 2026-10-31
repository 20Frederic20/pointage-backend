from identity.domain import Role


def test_get_employee_returns_the_camel_case_contract(identity_api, make_employee):
    identity_api.employees.items.append(make_employee(1, role=Role.MANAGER))
    res = identity_api.client.get("/employees/emp1")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "emp1"
    assert body["employeeNumber"] == "EMP0000001"
    assert body["userId"] == "usr1"
    assert body["role"] == "MANAGER"
    assert body["isActive"] is True
    assert body["phone"] == "0102030405"


def test_get_employee_unknown_id_returns_404(identity_api):
    assert identity_api.client.get("/employees/emp999").status_code == 404


def test_get_employee_malformed_id_returns_404(identity_api):
    assert identity_api.client.get("/employees/NOT-AN-ID").status_code == 404


def test_list_employees_filters_by_role_and_pages(identity_api, make_employee):
    # emp1, emp3, emp5, emp7 are managers.
    identity_api.employees.items.extend(
        make_employee(n, role=Role.MANAGER if n % 2 else Role.EMPLOYEE) for n in range(1, 9)
    )
    res = identity_api.client.get("/employees", params={"role": "MANAGER", "limit": 2, "offset": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 4
    assert [e["id"] for e in body["items"]] == ["emp5", "emp7"]


def test_list_employees_filters_by_status(identity_api, make_employee):
    identity_api.employees.items.extend([make_employee(1), make_employee(2, is_active=False)])
    body = identity_api.client.get("/employees", params={"is_active": "false"}).json()
    assert [e["id"] for e in body["items"]] == ["emp2"]


def test_list_employees_rejects_an_unknown_role(identity_api):
    assert identity_api.client.get("/employees", params={"role": "BOSS"}).status_code == 422


def _as(identity_api, role):
    from auth.application.dtos import PrincipalDTO
    from auth.interface import get_current_principal

    identity_api.client.app.dependency_overrides[get_current_principal] = lambda: PrincipalDTO(
        user_id="usr1", role=role
    )


ONBOARD = {
    "email": "ana@pointage.bj",
    "first_name": "Ana",
    "last_name": "Dossou",
    "directory_id": "dir1",
    "employee_number": "EMP0000001",
    "role": "MANAGER",
}


def test_onboard_is_for_responsible_roles(identity_api):
    _as(identity_api, "EMPLOYEE")
    assert identity_api.client.post("/employees/onboard", json=ONBOARD).status_code == 403


def test_onboard_validates_the_whole_form(identity_api):
    _as(identity_api, "ADMIN")
    for field, value in (("email", "not-an-email"), ("employee_number", "EMP1"), ("password", "short")):
        res = identity_api.client.post("/employees/onboard", json=ONBOARD | {field: value})
        assert res.status_code == 422, field


def _seed_record(api, role=Role.EMPLOYEE):
    from identity.domain import DirectoryId, EmployeeId, UserId
    from identity.domain.entities import Employee, User

    api.side.users.add(User(UserId("usr1"), email="a@pointage.bj", password_hash=None, role=role,
                            first_name="Ana", last_name="Dossou", is_active=True))
    api.side.employees.add(Employee(EmployeeId("emp1"), user_id=UserId("usr1"), employee_number="EMP0000001",
                                    is_active=True, role=role, company_directory_id=DirectoryId("dir1")))


def test_employee_actions_are_for_responsible_roles(identity_write_api):
    _seed_record(identity_write_api)
    identity_write_api.as_("EMPLOYEE")
    client = identity_write_api.client
    assert client.patch("/employees/emp1", json={"phone": "0197000000"}).status_code == 403
    assert client.post("/employees/emp1/deactivate").status_code == 403
    assert client.post("/employees/emp1/activate").status_code == 403


def test_patch_returns_new_phone_and_role(identity_write_api):
    _seed_record(identity_write_api)
    res = identity_write_api.client.patch("/employees/emp1", json={"phone": "0197000000", "role": "MANAGER",
                                                                    "firstName": "Awa"})
    assert res.status_code == 200
    assert (res.json()["phone"], res.json()["role"]) == ("0197000000", "MANAGER")


def test_deactivate_then_activate_routes(identity_write_api):
    _seed_record(identity_write_api)
    assert identity_write_api.client.post("/employees/emp1/deactivate").json()["isActive"] is False
    res = identity_write_api.client.post("/employees/emp1/deactivate")
    assert (res.status_code, res.json()["code"]) == (409, "EMPLOYEE_ALREADY_INACTIVE")
    assert identity_write_api.client.post("/employees/emp1/activate").json()["isActive"] is True


def test_onboard_response_says_whether_the_account_was_reused(identity_write_api):
    from datetime import UTC, datetime

    body = ONBOARD | {"directory_id": "dir1", "assignment_start_date": datetime.now(UTC).date().isoformat()}
    first = identity_write_api.client.post("/employees/onboard", json=body)
    assert (first.status_code, first.json()["accountReused"]) == (201, False)


def test_list_and_detail_include_names_company_and_current_site(identity_write_api):
    from datetime import UTC, datetime

    from identity.domain import DirectoryId, EmployeeAssignmentId, EmployeeId, SiteId, UserId
    from identity.domain.entities import Employee, EmployeeAssignment

    _seed_record(identity_write_api)
    side = identity_write_api.side
    side.assignments.add(EmployeeAssignment(EmployeeAssignmentId("asg1"), employee_id=EmployeeId("emp1"),
                                            directory_id=DirectoryId("dir2"), site_id=SiteId("site2"),
                                            start_date=datetime.now(UTC).date()))
    side.employees.add(Employee(EmployeeId("emp2"), user_id=UserId("usr1"), employee_number="EMP0000002",
                                is_active=True, company_directory_id=None))

    detail = identity_write_api.client.get("/employees/emp1").json()
    assert (detail["firstName"], detail["lastName"], detail["companyName"]) == ("Ana", "Dossou", "Société R")
    assert (detail["currentSiteId"], detail["currentSiteName"], detail["currentAssignmentEndDate"]) == (
        "site2", "Site 2", None)

    bare = identity_write_api.client.get("/employees/emp2").json()
    assert (bare["companyName"], bare["currentSiteName"]) == (None, None)
    assert identity_write_api.client.get("/employees").status_code == 200


CREATE = {"user_id": "usr1", "directory_id": "dir2", "employee_number": "EMP0000007", "role": "ADMIN",
          "is_active": True}


def test_create_employee_is_for_responsible_roles_under_the_ceiling(identity_write_api):
    _seed_record(identity_write_api)
    identity_write_api.as_("EMPLOYEE", user_id="usr1")  # an employee granting themself ADMIN
    assert identity_write_api.client.post("/employees", json=CREATE).status_code == 403
    identity_write_api.as_("MANAGER")
    res = identity_write_api.client.post("/employees", json=CREATE)
    assert (res.status_code, res.json()["code"]) == (403, "ROLE_CEILING")


def test_create_employee_keeps_one_active_record_per_company_and_stores_it(identity_write_api):
    _seed_record(identity_write_api)  # usr1 already active in company dir1
    identity_write_api.as_("ADMIN")
    res = identity_write_api.client.post("/employees", json=CREATE | {"role": "EMPLOYEE"})
    assert (res.status_code, res.json()["code"]) == (409, "ALREADY_ACTIVE_IN_COMPANY")
    res = identity_write_api.client.post("/employees", json=CREATE | {"role": "EMPLOYEE", "directory_id": "dir9"})
    assert (res.status_code, res.json()["companyDirectoryId"]) == (201, "dir9")
