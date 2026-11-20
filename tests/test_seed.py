from datetime import datetime

import pytest
from sqlalchemy import select

from app import rules, service
from app.models import EventKind, Writeup, WriteupEvent
from app.rules import OPEN_STATUSES, Severity, Status
from app.seed import seed
from tests.common import ZONE


# The seed runs at whatever time the app first starts, so try several local times of day,
# including either side of midnight.
@pytest.fixture(params=[0, 1, 6, 12, 18, 23])
def now(request, session):
    now = datetime(2026, 6, 15, request.param, 30, tzinfo=ZONE)
    seed(session, now)
    return now


@pytest.fixture
def writeups(session, now):
    return session.scalars(select(Writeup)).all()


def test_fleet_size(session, now):
    assert len(service.fleet_status(session)) == 30


def test_every_status_and_severity(writeups):
    assert {w.status for w in writeups} == set(Status)
    assert {w.severity for w in writeups} == set(Severity)


def test_high_in_every_status(writeups):
    assert {w.status for w in writeups if w.severity == Severity.high} == set(Status)


def test_overdue_and_due_today(writeups, now):
    today = service.today(now)
    assert {w.status for w in writeups if rules.is_overdue(w, today)} == {Status.scheduled, Status.in_progress}
    assert any(w.status in OPEN_STATUSES and w.scheduled_date == today for w in writeups)


def test_canceled_with_and_without_date(writeups):
    canceled_dates = {w.scheduled_date is None for w in writeups if w.status == Status.canceled}
    assert canceled_dates == {True, False}


def test_every_audit_event_kind(session, now):
    assert set(session.scalars(select(WriteupEvent.kind))) == set(EventKind)


def test_every_aircraft_situation(session, now):
    today = service.today(now)
    fleet = service.fleet_status(session)

    grounded = [s for s in fleet if not s.cleared]
    cleared = [s for s in fleet if s.cleared]
    assert any(len(s.grounding) == 1 for s in grounded)
    assert any(len(s.grounding) > 1 for s in grounded)
    assert any(not s.aircraft.writeups for s in cleared)
    assert any(s.open_writeups for s in cleared)
    assert any(rules.is_overdue(w, today) for s in cleared for w in s.open_writeups)
    assert any(
        any(w.severity == Severity.high for w in s.aircraft.writeups) and not s.grounding for s in cleared
    )
