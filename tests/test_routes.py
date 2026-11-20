from datetime import UTC, date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.main import create_app
from app.models import Aircraft, EventKind, Writeup
from app.rules import Severity, Status
from tests.common import FILING, NOW, TOMORROW, YESTERDAY, act, current_version, file

NEXT_WEEK = date(2026, 6, 22)


@pytest.fixture
def client(engine, session):
    session.add(Aircraft(tail_number="N101TG"))
    session.commit()
    return TestClient(create_app(engine, clock=lambda: NOW), follow_redirects=False)


def scheduled(client, when=TOMORROW):
    writeup_id = file(client)
    act(client, writeup_id, "schedule", scheduled_date=when.isoformat())
    return writeup_id


def in_progress(client):
    writeup_id = scheduled(client)
    act(client, writeup_id, "start")
    return writeup_id


def load(session, writeup_id):
    session.expire_all()
    return session.get(Writeup, writeup_id)


def events(session, writeup_id):
    return load(session, writeup_id).events


class TestFile:
    def test_creates_unscheduled_writeup(self, client, session):
        writeup_id = file(client, description="  Flickering warning light ")
        writeup = load(session, writeup_id)
        assert writeup.status == Status.unscheduled
        assert writeup.severity == Severity.high
        assert writeup.description == "Flickering warning light"
        assert writeup.reported_by == "Dana Ruiz"
        assert writeup.reported_at == NOW.astimezone(UTC).replace(tzinfo=None)
        assert events(session, writeup_id) == []

    def test_redirects_to_writeup_in_aircraft_panel(self, client):
        response = client.post("/aircraft/1/writeups", data=FILING)
        assert response.headers["location"] == "/?aircraft=N101TG#writeup-1"

    @pytest.mark.parametrize("field", ["description", "reported_by"])
    @pytest.mark.parametrize("value", ["", " "])
    def test_blank_field_is_rejected(self, client, session, field, value):
        assert client.post("/aircraft/1/writeups", data=FILING | {field: value}).status_code == 400
        assert session.scalars(select(Writeup)).all() == []

    def test_unknown_severity_is_rejected(self, client):
        response = client.post("/aircraft/1/writeups", data=FILING | {"severity": "critical"})
        assert response.status_code == 400
        assert "Severity is invalid." in response.text

    def test_with_date_files_it_scheduled_by_the_reporter(self, client, session):
        writeup_id = file(client, scheduled_date=TOMORROW.isoformat())
        writeup = load(session, writeup_id)
        assert (writeup.status, writeup.scheduled_date) == (Status.scheduled, TOMORROW)
        [event] = events(session, writeup_id)
        assert (event.kind, event.actor, event.to_value) == (EventKind.scheduled, "Dana Ruiz", TOMORROW.isoformat())

    def test_with_past_date_files_nothing(self, client, session):
        response = client.post("/aircraft/1/writeups", data=FILING | {"scheduled_date": YESTERDAY.isoformat()})
        assert response.status_code == 400
        assert session.scalars(select(Writeup)).all() == []

    def test_unknown_aircraft_is_404(self, client):
        assert client.post("/aircraft/999/writeups", data=FILING).status_code == 404


class TestSchedule:
    def test_schedules_and_logs(self, client, session):
        writeup_id = scheduled(client, TOMORROW)
        writeup = load(session, writeup_id)
        assert writeup.status == Status.scheduled
        assert writeup.scheduled_date == TOMORROW
        [event] = events(session, writeup_id)
        assert (event.kind, event.actor, event.from_value, event.to_value) == (
            EventKind.scheduled, "Sam Okafor", None, TOMORROW.isoformat()
        )
        assert event.at == NOW.astimezone(UTC).replace(tzinfo=None)

    def test_missing_date_is_rejected(self, client, session):
        writeup_id = file(client)
        act(client, writeup_id, "schedule", expected=400, scheduled_date="")
        assert load(session, writeup_id).status == Status.unscheduled

    def test_reschedule_logs_old_and_new_date(self, client, session):
        writeup_id = scheduled(client, TOMORROW)
        act(client, writeup_id, "schedule", scheduled_date=NEXT_WEEK.isoformat())
        assert load(session, writeup_id).scheduled_date == NEXT_WEEK
        event = events(session, writeup_id)[-1]
        assert (event.kind, event.from_value, event.to_value) == (
            EventKind.rescheduled, TOMORROW.isoformat(), NEXT_WEEK.isoformat()
        )

    def test_reschedule_while_in_progress_stays_in_progress(self, client, session):
        writeup_id = in_progress(client)
        act(client, writeup_id, "schedule", scheduled_date=NEXT_WEEK.isoformat())
        assert load(session, writeup_id).status == Status.in_progress

    def test_past_date_is_rejected_without_changes(self, client, session):
        writeup_id = file(client)
        act(client, writeup_id, "schedule", expected=400, scheduled_date=YESTERDAY.isoformat())
        assert load(session, writeup_id).status == Status.unscheduled
        assert events(session, writeup_id) == []


def test_unschedule_clears_date_and_logs_it(client, session):
    writeup_id = scheduled(client, TOMORROW)
    act(client, writeup_id, "unschedule")
    writeup = load(session, writeup_id)
    assert (writeup.status, writeup.scheduled_date) == (Status.unscheduled, None)
    event = events(session, writeup_id)[-1]
    assert (event.kind, event.from_value) == (EventKind.unscheduled, TOMORROW.isoformat())


def test_start(client, session):
    writeup_id = in_progress(client)
    assert load(session, writeup_id).status == Status.in_progress
    assert events(session, writeup_id)[-1].kind == EventKind.started


class TestResolve:
    def test_resolve_records_fixer_and_work(self, client, session):
        writeup_id = in_progress(client)
        act(client, writeup_id, "resolve", actor="Lee Park", note="Replaced the pane")
        assert load(session, writeup_id).status == Status.resolved
        event = events(session, writeup_id)[-1]
        assert (event.kind, event.actor, event.note) == (EventKind.resolved, "Lee Park", "Replaced the pane")

    def test_note_is_required(self, client):
        act(client, in_progress(client), "resolve", expected=400, note=" ")

    def test_must_be_in_progress(self, client):
        act(client, scheduled(client), "resolve", expected=400, note="Replaced the pane")


class TestCancel:
    def test_cancel_unscheduled_writeup(self, client, session):
        writeup_id = file(client)
        act(client, writeup_id, "cancel", note="Duplicate of another write-up")
        writeup = load(session, writeup_id)
        assert (writeup.status, writeup.scheduled_date) == (Status.canceled, None)
        assert events(session, writeup_id)[-1].note == "Duplicate of another write-up"

    def test_note_is_required(self, client):
        act(client, file(client), "cancel", expected=400, note="")

    def test_closed_writeup_cannot_be_canceled(self, client):
        writeup_id = file(client)
        act(client, writeup_id, "cancel", note="Duplicate")
        act(client, writeup_id, "cancel", expected=400, note="Duplicate")


class TestSeverity:
    def test_change_logs_old_new_and_reason(self, client, session):
        writeup_id = file(client, severity="high")
        act(client, writeup_id, "severity", severity="low", note="Cosmetic only")
        assert load(session, writeup_id).severity == Severity.low
        event = events(session, writeup_id)[-1]
        assert (event.kind, event.from_value, event.to_value, event.note) == (
            EventKind.severity_changed, "high", "low", "Cosmetic only"
        )

    def test_reason_is_required(self, client):
        act(client, file(client), "severity", expected=400, severity="low", note="")

    def test_same_severity_is_rejected(self, client):
        act(client, file(client, severity="high"), "severity", expected=400, severity="high", note="Why")


def test_edit_description_logs_old_and_new(client, session):
    writeup_id = file(client, description="Cracked window")
    act(client, writeup_id, "description", description="Cracked left cockpit window")
    assert load(session, writeup_id).description == "Cracked left cockpit window"
    event = events(session, writeup_id)[-1]
    assert (event.kind, event.from_value, event.to_value) == (
        EventKind.description_edited, "Cracked window", "Cracked left cockpit window"
    )


@pytest.mark.parametrize("action", ["unschedule", "start"])
def test_blank_actor_is_rejected(client, session, action):
    writeup_id = scheduled(client)
    act(client, writeup_id, action, expected=400, actor="  ")
    assert load(session, writeup_id).status == Status.scheduled


def test_redirect_keeps_search_and_hidden_groups(client):
    writeup_id = scheduled(client)
    form = {"actor": "Sam Okafor", "version": current_version(client, writeup_id)}
    response = client.post(f"/writeups/{writeup_id}/start?q=N1&hide=cleared", data=form)
    assert response.headers["location"] == f"/?q=N1&hide=cleared&aircraft=N101TG#writeup-{writeup_id}"


def test_unknown_writeup_is_404(client):
    act(client, 999, "start", expected=404)


def test_file_sent_as_a_text_field_is_rejected(client):
    writeup_id = scheduled(client)
    response = client.post(
        f"/writeups/{writeup_id}/start",
        data={"version": current_version(client, writeup_id)},
        files={"actor": ("name.txt", b"Sam Okafor")},
    )
    assert response.status_code == 400
    assert "Name is invalid." in response.text


def test_change_made_while_a_request_is_in_flight_is_not_overwritten(client, engine, session):
    writeup_id = in_progress(client)

    # The clock is read after the write-up is loaded, so this lands between the read and the write.
    def cancel_meanwhile():
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE writeup SET status = 'canceled', version = version + 1 WHERE id = :id"),
                {"id": writeup_id},
            )
        return NOW

    client.app.state.clock = cancel_meanwhile
    response = act(client, writeup_id, "resolve", expected=400, note="Replaced the pane")
    assert f"Write-up #{writeup_id} has changed since this page loaded. Nothing was saved." in response.text
    assert load(session, writeup_id).status == Status.canceled
    assert events(session, writeup_id)[-1].kind == EventKind.started


def test_action_from_a_page_loaded_before_another_change_is_rejected(client, session):
    writeup_id = scheduled(client)
    loaded = current_version(client, writeup_id)
    act(client, writeup_id, "description", description="Cracked left cockpit window")
    response = act(client, writeup_id, "start", expected=400, version=loaded)
    assert f"Write-up #{writeup_id} has changed since this page loaded. Nothing was saved." in response.text
    assert load(session, writeup_id).status == Status.scheduled
    assert events(session, writeup_id)[-1].kind == EventKind.description_edited


def test_action_without_a_version_is_rejected(client, session):
    writeup_id = scheduled(client)
    response = client.post(f"/writeups/{writeup_id}/start", data={"actor": "Sam Okafor"})
    assert response.status_code == 400
    assert "Page version is required." in response.text
    assert load(session, writeup_id).status == Status.scheduled


def test_unknown_writeup_without_a_version_is_404(client):
    assert client.post("/writeups/999/start", data={"actor": "Sam Okafor"}).status_code == 404
