"""The ordinary punch: the session's employee record, never an inactive one."""

from identity.domain import EmployeeId, Role, UserId
from identity.domain.entities import Employee


def punch(api, key="k1"):
    return api.client.post("/time-entries", json={"latitude": 6.3654, "longitude": 2.4183, "source": "MOBILE",
                                                  "idempotency_key": key})


def test_normal_punch_uses_token_employee_id(punch_api):
    # usr1 also works for a second company: record emp3, assigned to the same site.
    second = Employee(EmployeeId("emp3"), user_id=UserId("usr1"), employee_number="EMP0000003", is_active=True,
                      role=Role.EMPLOYEE)
    punch_api.employees.items.append(second)
    punch_api.assignments.by_employee[second.id] = punch_api.assignments.by_employee[EmployeeId("emp1")]
    punch_api.act_as("usr1", employee_id="emp3")
    res = punch(punch_api)
    assert res.status_code == 201, res.text
    assert res.json()["employee_id"] == "emp3"


def test_normal_punch_on_a_record_of_someone_else_is_404(punch_api):
    punch_api.act_as("usr1", employee_id="emp2")
    assert punch(punch_api).status_code == 404
    assert punch_api.time_entries.items == []


def test_normal_punch_inactive_record_is_409(punch_api):
    punch_api.employees.items[0].deactivate()
    punch_api.act_as("usr1", employee_id="emp1")
    res = punch(punch_api)
    assert (res.status_code, res.json()["code"]) == (409, "EMPLOYEE_INACTIVE")
    punch_api.act_as("usr1")  # an old token without employee_id: same refusal
    assert punch(punch_api, key="k2").status_code == 409
    assert punch_api.time_entries.items == []
