"""Anomalies back-office API: list, detail, photo, and the validate / reject
decision, which updates the anomaly and its time entry, then recalculates the day."""

import asyncio
import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from adjustements.application.commands import DecideAnomalyCommand
from adjustements.domain.value_objects import AnomalyStatus
from identity.domain import UserId
from identity.domain.errors.errors import RolePermissionDeniedError
from punch.domain import TimeEntryValidationStatus
from punch.domain.entities import time_entry as time_entry_module
from punch.domain.events import TimeEntryRejected, TimeEntryValidated
from time_calculation.application.commands import CalculateDailyTimeCommand
from time_calculation.domain.errors import NoPeriodForDateError

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"  # what the conftest stores for a seeded selfie


def stored(api, anomaly_id):
    anomaly = api.anomalies.current(anomaly_id)
    return anomaly, api.time_entries.current(anomaly.time_entry_id.value)


def decision_events(api, anomaly_id):
    _, entry = stored(api, anomaly_id)
    return [
        e for e in api.time_entries.streams[entry.id.value] if isinstance(e, (TimeEntryValidated, TimeEntryRejected))
    ]


# ---- GET /anomalies ----------------------------------------------------------


def test_list_requires_responsible_role(anomalies_api):
    anomalies_api.add_assisted_punch()
    anomalies_api.act_as("usr2", "EMPLOYEE")
    res = anomalies_api.client.get("/anomalies")
    assert res.status_code == 403
    assert res.json()["code"] == "ACCESS_DENIED"

    for role in ("MANAGER", "HR", "PAYROLL", "ADMIN"):
        anomalies_api.act_as("usr9", role)
        res = anomalies_api.client.get("/anomalies")
        assert res.status_code == 200, role
        assert res.json()["total"] == 1, role


def test_every_route_requires_responsible_role(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    anomalies_api.act_as("usr2", "EMPLOYEE")
    client = anomalies_api.client
    for res in (
        client.get(f"/anomalies/{anomaly_id}"),
        client.get(f"/anomalies/{anomaly_id}/photo"),
        client.post(f"/anomalies/{anomaly_id}/validate", json={}),
        client.post(f"/anomalies/{anomaly_id}/reject", json={"comment": "non"}),
    ):
        assert res.status_code == 403, res.request.url
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.OPEN
    assert entry.validation_status == TimeEntryValidationStatus.PENDING


def test_list_items_carry_names_and_photo_flag(anomalies_api):
    anomalies_api.assign("emp2", "Ancien site", start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
    anomalies_api.assign("emp2", "Siège Cotonou", start_date=date(2021, 1, 1))
    late_id = anomalies_api.add_late_anomaly()
    assisted_id = anomalies_api.add_assisted_punch()
    _, entry = stored(anomalies_api, assisted_id)

    res = anomalies_api.client.get("/anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 2
    newest, oldest = body["items"]  # detected_at desc
    assert newest == {
        "id": assisted_id,
        "type": "ASSISTED_POINTING",
        "severity": "BLOCKING",
        "status": "OPEN",
        "detectedAt": newest["detectedAt"],
        "employeeId": "emp2",
        "employeeNumber": "EMP0000002",
        "employeeFirstName": "Paul",
        "employeeLastName": "Houngbo",
        "assistedByFirstName": "Marie",
        "assistedByLastName": "Agossou",
        "occuredAt": newest["occuredAt"],
        "entryType": "IN",
        "hasPhoto": True,
        "decidedAt": None,
        "decisionComment": None,
        "siteName": "Siège Cotonou",
    }
    assert newest["occuredAt"].startswith(entry.occured_at.isoformat()[:19])
    assert oldest["id"] == late_id
    assert oldest["hasPhoto"] is False
    assert oldest["assistedByFirstName"] is None
    assert oldest["employeeFirstName"] == "Paul"

    res = anomalies_api.client.get("/anomalies", params={"type": "ASSISTED_POINTING", "status": "OPEN"})
    assert [i["id"] for i in res.json()["items"]] == [assisted_id]
    assert res.json()["total"] == 1

    res = anomalies_api.client.get("/anomalies", params={"limit": 1, "offset": 1})
    assert [i["id"] for i in res.json()["items"]] == [late_id]
    assert res.json()["total"] == 2

    assert anomalies_api.client.get("/anomalies", params={"status": "NOPE"}).status_code == 422


def test_detail_returns_the_item_or_404(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    res = anomalies_api.client.get(f"/anomalies/{anomaly_id}")
    assert res.status_code == 200, res.text
    assert res.json()["id"] == anomaly_id
    assert res.json()["employeeLastName"] == "Houngbo"
    assert res.json()["hasPhoto"] is True
    assert res.json()["siteName"] is None  # no assignment on the punch date

    assert anomalies_api.client.get("/anomalies/unknown").status_code == 404


# ---- GET /anomalies/{id}/photo ----------------------------------------------


def test_photo_route_returns_image_bytes_and_content_type(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    res = anomalies_api.client.get(f"/anomalies/{anomaly_id}/photo")
    assert res.status_code == 200
    assert res.content == JPEG
    assert res.headers["content-type"] == "image/jpeg"
    assert res.headers["x-content-type-options"] == "nosniff"

    without_photo = anomalies_api.add_assisted_punch(photo=False)
    assert anomalies_api.client.get(f"/anomalies/{without_photo}/photo").status_code == 404
    assert anomalies_api.client.get("/anomalies/unknown/photo").status_code == 404

    # The key is on the entry but the object is gone from the storage.
    anomalies_api.photos.objects.clear()
    assert anomalies_api.client.get(f"/anomalies/{anomaly_id}/photo").status_code == 404


# ---- POST /anomalies/{id}/validate | reject ----------------------------------


def test_validate_marks_anomaly_validated_and_entry_counted(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate", json={"comment": "C'est bien lui"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == anomaly_id
    assert body["status"] == "VALIDATED"
    assert body["decisionComment"] == "C'est bien lui"
    assert body["decidedAt"] is not None
    assert body["employeeFirstName"] == "Paul"

    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.VALIDATED
    assert anomaly.decided_by == UserId("usr3")
    assert anomaly.decision_comment == "C'est bien lui"
    assert entry.validation_status == TimeEntryValidationStatus.COUNTED

    assert anomalies_api.time_calculation.sent == [
        CalculateDailyTimeCommand(employee_id="emp2", work_date=entry.occured_at.astimezone(UTC).date())
    ]


def test_recalculation_uses_the_local_work_date(anomalies_api, monkeypatch):
    # 23:30 UTC on the 7th is 00:30 on the 8th in Porto-Novo (UTC+1): the day to recalc is the 8th.
    monkeypatch.setattr(time_entry_module, "_utcnow", lambda: datetime(2026, 10, 7, 23, 30, tzinfo=UTC))
    anomalies_api.time_calculation.zone = ZoneInfo("Africa/Porto-Novo")
    anomaly_id = anomalies_api.add_assisted_punch()

    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate", json={})

    assert res.status_code == 200, res.text
    assert anomalies_api.time_calculation.sent == [
        CalculateDailyTimeCommand(employee_id="emp2", work_date=date(2026, 10, 8))
    ]


def test_validate_without_body_or_comment(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate")
    assert res.status_code == 200, res.text
    assert res.json()["decisionComment"] is None


def test_reject_requires_comment_and_marks_entry_rejected(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    for payload in ({}, {"comment": None}, {"comment": "   "}):
        res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/reject", json=payload)
        assert res.status_code == 422, payload
        assert res.json()["code"] == "DECISION_COMMENT_REQUIRED", payload
    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/reject", json={"comment": "x" * 513})
    assert res.status_code == 422
    assert res.json()["code"] == "DECISION_COMMENT_TOO_LONG"
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.OPEN
    assert entry.validation_status == TimeEntryValidationStatus.PENDING
    assert anomalies_api.time_calculation.sent == []

    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/reject", json={"comment": "Ce n'est pas lui"})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "REJECTED"
    assert res.json()["decisionComment"] == "Ce n'est pas lui"
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.REJECTED
    assert anomaly.decided_by == UserId("usr3")
    assert entry.validation_status == TimeEntryValidationStatus.REJECTED
    assert len(anomalies_api.time_calculation.sent) == 1


def test_second_decision_is_409_and_entry_gets_one_decision_event(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    client = anomalies_api.client
    assert client.post(f"/anomalies/{anomaly_id}/validate", json={}).status_code == 200

    anomalies_api.act_as("usr9", "ADMIN")
    for res in (
        client.post(f"/anomalies/{anomaly_id}/validate", json={}),
        client.post(f"/anomalies/{anomaly_id}/reject", json={"comment": "Trop tard"}),
    ):
        assert res.status_code == 409
        assert res.json()["code"] == "ANOMALY_ALREADY_DECIDED"

    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.VALIDATED
    assert anomaly.decided_by == UserId("usr3")
    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert [type(e) for e in decision_events(anomalies_api, anomaly_id)] == [TimeEntryValidated]
    assert len(anomalies_api.time_calculation.sent) == 1


def test_assistant_or_punched_employee_cannot_decide(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch(employee="emp2", assistant="usr1")
    client = anomalies_api.client
    for user_id in ("usr1", "usr2"):  # the assistant, then the punched employee
        anomalies_api.act_as(user_id, "MANAGER")
        for res in (
            client.post(f"/anomalies/{anomaly_id}/validate", json={}),
            client.post(f"/anomalies/{anomaly_id}/reject", json={"comment": "non"}),
        ):
            assert res.status_code == 403, user_id
            assert res.json()["code"] == "SELF_DECISION", user_id

    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.OPEN
    assert entry.validation_status == TimeEntryValidationStatus.PENDING
    assert decision_events(anomalies_api, anomaly_id) == []
    assert anomalies_api.time_calculation.sent == []


def test_decision_on_unknown_anomaly_is_404(anomalies_api):
    res = anomalies_api.client.post("/anomalies/unknown/validate", json={})
    assert res.status_code == 404


def test_decision_succeeds_when_recalculation_fails(anomalies_api, caplog):
    anomaly_id = anomalies_api.add_assisted_punch()
    anomalies_api.time_calculation.error = NoPeriodForDateError("No period covers the day")

    with caplog.at_level(logging.WARNING, logger="audit"):
        res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate", json={})

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "VALIDATED"
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.VALIDATED
    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert len(anomalies_api.time_calculation.sent) == 1
    assert any(
        "action=RECALC_AFTER_DECISION" in r.getMessage()
        and anomaly_id in r.getMessage()
        and "status=SKIPPED" in r.getMessage()
        and "NO_PERIOD_FOR_DATE" in r.getMessage()
        for r in caplog.records
    )


def test_decision_succeeds_when_recalculation_crashes(anomalies_api, caplog):
    anomaly_id = anomalies_api.add_assisted_punch()
    anomalies_api.time_calculation.error = RuntimeError("database went away")

    with caplog.at_level(logging.WARNING, logger="audit"):
        res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate", json={})

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "VALIDATED"
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.VALIDATED
    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert any(
        "action=RECALC_AFTER_DECISION" in r.getMessage()
        and anomaly_id in r.getMessage()
        and "status=FAILED" in r.getMessage()
        and "RuntimeError" in r.getMessage()
        for r in caplog.records
    )


def test_validating_an_anomaly_on_a_counted_entry_leaves_the_entry_untouched(anomalies_api):
    anomaly_id = anomalies_api.add_late_anomaly()
    _, before = stored(anomalies_api, anomaly_id)
    events_before = list(anomalies_api.time_entries.streams[before.id.value])

    res = anomalies_api.client.post(f"/anomalies/{anomaly_id}/validate", json={})

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "VALIDATED"
    anomaly, entry = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.VALIDATED
    assert entry.validation_status == TimeEntryValidationStatus.COUNTED
    assert anomalies_api.time_entries.streams[entry.id.value] == events_before
    assert decision_events(anomalies_api, anomaly_id) == []
    assert len(anomalies_api.time_calculation.sent) == 1


# ---- handler -----------------------------------------------------------------


def test_handler_rechecks_the_role(anomalies_api):
    anomaly_id = anomalies_api.add_assisted_punch()
    for role in ("EMPLOYEE", "NOT_A_ROLE"):
        with pytest.raises(RolePermissionDeniedError):
            asyncio.run(
                anomalies_api.container.send(
                    DecideAnomalyCommand(
                        actor_user_id="usr9",
                        actor_role=role,
                        anomaly_id=anomaly_id,
                        decision="VALIDATE",
                        comment=None,
                    )
                )
            )
    anomaly, _ = stored(anomalies_api, anomaly_id)
    assert anomaly.status == AnomalyStatus.OPEN
