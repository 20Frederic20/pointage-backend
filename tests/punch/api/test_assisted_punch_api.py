"""Assisted punch: an employee punches for themself from a colleague's phone
(the caller), with their matricule and a selfie."""

from datetime import UTC, datetime

from adjustements.domain.value_objects import AnomalyStatus, AnomalyType, Severity
from identity.domain import EmployeeId, UserId
from identity.domain.value_objects.location import Location

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PORTO_NOVO = Location(6.4969, 2.6289)  # ~27 km from Cotonou, where the caller stands


def assisted(api, *, employee_number="EMP0000002", key="k1", photo=("selfie.jpg", JPEG, "image/jpeg"), **extra):
    data = {
        "employee_number": employee_number,
        "latitude": "6.3654",
        "longitude": "2.4183",
        "idempotency_key": key,
        **extra,
    }
    files = {"photo": photo} if photo is not None else None
    return api.client.post("/time-entries/assisted", data=data, files=files)


def assert_nothing_written(api):
    assert api.time_entries.items == []
    assert api.anomalies.items == []
    assert api.photos.objects == {}


# ---- POST /time-entries/assisted ---------------------------------------------


def test_assisted_punch_creates_pending_entry_and_open_anomaly(punch_api):
    res = assisted(punch_api)
    assert res.status_code == 201, res.text
    body = res.json()
    # TimeEntryResponse keeps its existing snake_case wire contract.
    assert body["validation_status"] == "PENDING"
    assert body["employee_id"] == "emp2"
    assert body["source"] == "ASSISTED"
    assert body["entry_type"] == "IN"
    assert body["assisted_by_user_id"] == "usr1"

    [entry] = punch_api.time_entries.items
    assert entry.id.value == body["id"]
    assert entry.photo_key == f"time-entries/{body['id']}.jpg"
    assert entry.idempotency_key == "k1"

    [anomaly] = punch_api.anomalies.items
    assert anomaly.type == AnomalyType.ASSISTED_POINTING
    assert anomaly.severity == Severity.BLOCKING
    assert anomaly.status == AnomalyStatus.OPEN
    assert anomaly.time_entry_id == entry.id
    assert anomaly.employee_id == EmployeeId("emp2")
    assert anomaly.assisted_by_user_id == UserId("usr1")
    assert anomaly.description == "Pointage assisté depuis le compte usr1"

    assert punch_api.photos.objects == {f"time-entries/{body['id']}.jpg": (JPEG, "image/jpeg")}


def test_assisted_punch_without_photo_is_422(punch_api):
    res = assisted(punch_api, photo=None)
    assert res.status_code == 422
    assert_nothing_written(punch_api)


def test_assisted_punch_with_non_image_or_too_large_photo_is_invalid_photo(punch_api):
    for photo in (
        ("note.txt", b"hello", "text/plain"),
        ("big.jpg", b"\xff" * (MAX_PHOTO_BYTES + 1), "image/jpeg"),
        ("empty.png", b"", "image/png"),
    ):
        res = assisted(punch_api, photo=photo)
        assert res.status_code == 422, photo[0]
        assert res.json()["code"] == "INVALID_PHOTO", photo[0]
        assert_nothing_written(punch_api)


def test_assisted_punch_accepts_png_at_the_size_limit(punch_api):
    res = assisted(punch_api, photo=("selfie.png", b"\x89" * MAX_PHOTO_BYTES, "image/png"))
    assert res.status_code == 201, res.text
    assert list(punch_api.photos.objects) == [f"time-entries/{res.json()['id']}.png"]


def test_assisted_punch_for_own_matricule_is_409(punch_api):
    res = assisted(punch_api, employee_number="EMP0000001")
    assert res.status_code == 409
    assert res.json()["code"] == "SELF_ASSISTED_PUNCH"
    assert_nothing_written(punch_api)


def test_assisted_punch_for_unknown_or_inactive_matricule_is_404(punch_api):
    punch_api.add_employee(3, first_name="Ines", last_name="Zinsou", is_active=False)
    for number in ("EMP9999999", "EMP0000003"):
        res = assisted(punch_api, employee_number=number)
        assert res.status_code == 404, number
    assert_nothing_written(punch_api)


def test_assisted_punch_far_from_punched_employee_site_is_422(punch_api):
    # The caller (emp1) is at their own site in Cotonou; emp3 works in Porto-Novo.
    punch_api.add_employee(3, first_name="Ines", last_name="Zinsou", site_location=PORTO_NOVO)
    res = assisted(punch_api, employee_number="EMP0000003")
    assert res.status_code == 422
    assert res.json()["code"] == "TOO_FAR_FROM_WORKPLACE"
    assert_nothing_written(punch_api)


def test_assisted_punch_without_assignment_is_409(punch_api):
    punch_api.add_employee(3, first_name="Ines", last_name="Zinsou", assigned=False)
    res = assisted(punch_api, employee_number="EMP0000003")
    assert res.status_code == 409
    assert res.json()["code"] == "EMPLOYEE_NOT_ASSIGNED"
    assert_nothing_written(punch_api)


def test_assisted_punch_same_idempotency_key_twice_is_409_and_single_entry(punch_api):
    first = assisted(punch_api, key="same")
    assert first.status_code == 201
    second = assisted(punch_api, key="same")
    assert second.status_code == 409
    assert second.json()["code"] == "PUNCH_ALREADY_EXISTS"
    assert len(punch_api.time_entries.items) == 1
    assert len(punch_api.anomalies.items) == 1
    assert len(punch_api.photos.objects) == 1


def test_second_assisted_punch_is_out_and_rejected_entries_are_skipped(punch_api):
    first = assisted(punch_api, key="a")
    second = assisted(punch_api, key="b")
    assert (first.json()["entry_type"], second.json()["entry_type"]) == ("IN", "OUT")

    # Reject the OUT: the next punch follows the pending IN, so it is an OUT again.
    out = punch_api.time_entries.items[1]
    out.reject(decided_by=UserId("usr9"), decided_at=datetime.now(UTC))
    third = assisted(punch_api, key="c")
    assert third.json()["entry_type"] == "OUT"

    # With every earlier entry rejected, the next punch is an IN.
    for entry in punch_api.time_entries.items:
        if entry.validation_status.value == "PENDING":
            entry.reject(decided_by=UserId("usr9"), decided_at=datetime.now(UTC))
    fourth = assisted(punch_api, key="d")
    assert fourth.json()["entry_type"] == "IN"


# ---- GET /time-entries/assisted/employees/{employee_number} ------------------


def test_lookup_returns_names_only(punch_api):
    res = punch_api.client.get("/time-entries/assisted/employees/EMP0000002")
    assert res.status_code == 200
    assert res.json() == {"employeeNumber": "EMP0000002", "firstName": "Paul", "lastName": "Houngbo"}


def test_lookup_inactive_or_own_matricule(punch_api):
    punch_api.add_employee(3, first_name="Ines", last_name="Zinsou", is_active=False)
    inactive = punch_api.client.get("/time-entries/assisted/employees/EMP0000003")
    assert inactive.status_code == 404
    assert "Ines" not in inactive.text and "Zinsou" not in inactive.text
    assert punch_api.client.get("/time-entries/assisted/employees/EMP9999999").status_code == 404

    own = punch_api.client.get("/time-entries/assisted/employees/EMP0000001")
    assert own.status_code == 409
    assert own.json()["code"] == "SELF_ASSISTED_PUNCH"
