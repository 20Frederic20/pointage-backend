"""Manager punch: a responsible punches for an employee, counted immediately."""

from datetime import UTC, datetime, timedelta


def manager_punch(api, employee_id="emp2", *, key="k1", **extra):
    return api.client.post(f"/employees/{employee_id}/time-entries", json={"idempotencyKey": key, **extra})


def as_manager(api, role="MANAGER"):
    api.act_as("usr9", role)


def test_manager_punch_is_counted_immediately(punch_api):
    as_manager(punch_api)
    res = manager_punch(punch_api)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["validation_status"] == "COUNTED"
    assert body["source"] == "MANAGER_ASSISTED"
    assert body["entry_type"] == "IN"
    assert body["employee_id"] == "emp2"
    assert body["assisted_by_user_id"] == "usr9"
    assert body["location_confidence"] == "LOW"
    assert body["idempotency_key"] == "k1"
    # TimeEntryResponse has no location field: assert on the stored aggregate.
    (entry,) = punch_api.time_entries.items
    assert entry.location is None
    assert entry.photo_key is None
    assert punch_api.anomalies.items == []
    assert punch_api.photos.objects == {}


def test_manager_punch_alternates_in_out(punch_api):
    as_manager(punch_api)
    types = [manager_punch(punch_api, key=f"k{i}").json()["entry_type"] for i in range(3)]
    assert types == ["IN", "OUT", "IN"]


def test_responsible_roles_are_allowed(punch_api):
    for i, role in enumerate(["HR", "PAYROLL", "ADMIN"]):
        as_manager(punch_api, role)
        assert manager_punch(punch_api, key=f"k{i}").status_code == 201


def test_employee_role_gets_403(punch_api):
    punch_api.act_as("usr1", "EMPLOYEE")
    res = manager_punch(punch_api)
    assert res.status_code == 403
    assert punch_api.time_entries.items == []


def test_manager_cannot_punch_for_self(punch_api):
    punch_api.act_as("usr1", "MANAGER")  # usr1 is employee emp1
    res = manager_punch(punch_api, "emp1")
    assert res.status_code == 409
    assert res.json()["code"] == "SELF_MANAGER_PUNCH"
    assert punch_api.time_entries.items == []


def test_unassigned_employee_is_409(punch_api):
    punch_api.add_employee(3, first_name="Jean", last_name="Dossou", assigned=False)
    as_manager(punch_api)
    res = manager_punch(punch_api, "emp3")
    assert res.status_code == 409
    assert res.json()["code"] == "EMPLOYEE_NOT_ASSIGNED"
    assert punch_api.time_entries.items == []


def test_unknown_or_inactive_employee_is_404(punch_api):
    punch_api.add_employee(3, first_name="Jean", last_name="Dossou", is_active=False)
    as_manager(punch_api)
    assert manager_punch(punch_api, "emp3").status_code == 404
    assert manager_punch(punch_api, "nope", key="k2").status_code == 404
    assert punch_api.time_entries.items == []


def test_same_idempotency_key_twice_is_409_and_single_entry(punch_api):
    as_manager(punch_api)
    assert manager_punch(punch_api).status_code == 201
    res = manager_punch(punch_api)
    assert res.status_code == 409
    assert res.json()["code"] == "PUNCH_ALREADY_EXISTS"
    assert len(punch_api.time_entries.items) == 1


def test_client_cannot_choose_time(punch_api):
    as_manager(punch_api)
    res = manager_punch(punch_api, occuredAt="2020-01-01T00:00:00Z")
    assert res.status_code == 201, res.text
    (entry,) = punch_api.time_entries.items
    assert abs(entry.occured_at - datetime.now(UTC)) < timedelta(seconds=5)
