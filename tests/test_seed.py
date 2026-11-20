from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app import rules, service
from app.models import EventKind, Writeup, WriteupEvent
from app.rules import OPEN_STATUSES, Severity, Status
from app.seed import seed

# Several times of day, so day boundaries in the server's time zone can't break the seed.
NOWS = [datetime(2026, 6, 15, hour, 30, tzinfo=UTC) for hour in (0, 6, 12, 18, 23)]


@pytest.fixture(params=NOWS)
def seeded(request, session):
    seed(session, request.param)
    today = service.today(request.param)
    writeups = session.scalars(select(Writeup)).all()
    return session, today, writeups


def test_fleet_size(seeded):
    session, _, _ = seeded
    assert len(service.fleet_status(session)) == 30


def test_every_status_and_severity(seeded):
    _, _, writeups = seeded
    assert {w.status for w in writeups} == set(Status)
    assert {w.severity for w in writeups} == set(Severity)


def test_high_in_every_status(seeded):
    _, _, writeups = seeded
    assert {w.status for w in writeups if w.severity == Severity.high} == set(Status)


def test_overdue_and_due_today(seeded):
    _, today, writeups = seeded
    assert {w.status for w in writeups if rules.is_overdue(w, today)} == {Status.scheduled, Status.in_progress}
    assert any(w.status in OPEN_STATUSES and w.scheduled_date == today for w in writeups)


def test_canceled_with_and_without_date(seeded):
    _, _, writeups = seeded
    canceled_dates = {w.scheduled_date is None for w in writeups if w.status == Status.canceled}
    assert canceled_dates == {True, False}


def test_every_audit_event_kind(seeded):
    session, _, _ = seeded
    assert set(session.scalars(select(WriteupEvent.kind))) == set(EventKind)


def test_every_aircraft_situation(seeded):
    session, today, _ = seeded
    fleet = service.fleet_status(session)

    def open_highs(status):
        return [w for w in status.open_writeups if w.severity == Severity.high]

    grounded = [s for s in fleet if not s.cleared]
    cleared = [s for s in fleet if s.cleared]
    assert any(len(open_highs(s)) == 1 for s in grounded)
    assert any(len(open_highs(s)) > 1 for s in grounded)
    assert any(not s.aircraft.writeups for s in cleared)
    assert any(s.open_writeups for s in cleared)
    assert any(rules.is_overdue(w, today) for s in cleared for w in s.open_writeups)
    assert any(
        any(w.severity == Severity.high for w in s.aircraft.writeups) and not open_highs(s) for s in cleared
    )
