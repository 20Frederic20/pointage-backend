from datetime import UTC, datetime, timedelta

from identity.domain import DirectoryId, EmployeeId, Role, UserId
from identity.domain.entities import Employee


def _employee(api, role=Role.EMPLOYEE):
    api.side.employees.add(Employee(EmployeeId("emp1"), user_id=UserId("usr1"), employee_number="EMP0000001",
                                    is_active=True, role=role, company_directory_id=DirectoryId("dir1")))


def _body(start=None):
    start = start or datetime.now(UTC).date()
    return {"employee_id": "emp1", "directory_id": "dir2", "site_id": "site2", "start_date": start.isoformat()}


def test_assign_is_for_responsible_roles(identity_write_api):
    _employee(identity_write_api)
    identity_write_api.as_("EMPLOYEE")
    assert identity_write_api.client.post("/employee-assignments", json=_body()).status_code == 403
    identity_write_api.as_("HR")
    assert identity_write_api.client.post("/employee-assignments", json=_body()).status_code == 201


def test_end_is_for_responsible_roles(identity_write_api):
    _employee(identity_write_api)
    created = identity_write_api.client.post("/employee-assignments", json=_body()).json()
    identity_write_api.as_("EMPLOYEE")
    end = (datetime.now(UTC).date() + timedelta(days=5)).isoformat()
    res = identity_write_api.client.post(f"/employee-assignments/{created['id']}/end", json={"end_date": end})
    assert res.status_code == 403


def test_list_items_carry_site_and_directory_names(identity_write_api):
    _employee(identity_write_api)
    identity_write_api.client.post("/employee-assignments", json=_body())
    items = identity_write_api.client.get("/employee-assignments", params={"employee_id": "emp1"}).json()
    assert [(i["siteName"], i["directoryName"]) for i in items] == [("Site 2", "Agence Nord")]


def test_ceiling_refusal_is_403_role_ceiling(identity_write_api):
    _employee(identity_write_api, role=Role.ADMIN)
    identity_write_api.as_("MANAGER")
    res = identity_write_api.client.post("/employee-assignments", json=_body())
    assert (res.status_code, res.json()["code"]) == (403, "ROLE_CEILING")
