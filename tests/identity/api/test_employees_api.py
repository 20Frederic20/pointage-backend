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
