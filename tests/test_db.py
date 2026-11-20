import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

WRITEUP = dict(
    aircraft_id=1,
    description="Cracked window",
    severity="high",
    status="unscheduled",
    scheduled_date=None,
    reported_by="Dana Ruiz",
    reported_at="2026-06-15 12:00:00",
)
EVENT = dict(
    writeup_id=1,
    at="2026-06-15 12:00:00",
    actor="Sam Okafor",
    kind="started",
    from_value=None,
    to_value=None,
    note=None,
)


def insert(session, table, row):
    columns = ", ".join(row)
    params = ", ".join(f":{c}" for c in row)
    session.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), row)
    session.flush()


@pytest.fixture
def aircraft(session):
    insert(session, "aircraft", {"tail_number": "N101TG"})


@pytest.fixture
def writeup(session, aircraft):
    insert(session, "writeup", WRITEUP)


def assert_rejected(session, table, row):
    with pytest.raises(IntegrityError):
        insert(session, table, row)


class TestForeignKeys:
    def test_writeup_needs_existing_aircraft(self, session):
        assert_rejected(session, "writeup", WRITEUP | {"aircraft_id": 999})

    def test_event_needs_existing_writeup(self, session, aircraft):
        assert_rejected(session, "writeup_event", EVENT | {"writeup_id": 999})


class TestAircraft:
    def test_blank_tail_number_is_rejected(self, session):
        assert_rejected(session, "aircraft", {"tail_number": "  "})

    def test_tail_number_is_unique(self, session, aircraft):
        assert_rejected(session, "aircraft", {"tail_number": "N101TG"})


class TestWriteup:
    def test_valid_row_is_accepted(self, session, aircraft):
        insert(session, "writeup", WRITEUP)

    @pytest.mark.parametrize("column", ["severity", "status"])
    def test_unknown_enum_value_is_rejected(self, session, aircraft, column):
        assert_rejected(session, "writeup", WRITEUP | {column: "bogus"})

    @pytest.mark.parametrize("column", ["description", "reported_by"])
    def test_blank_text_is_rejected(self, session, aircraft, column):
        assert_rejected(session, "writeup", WRITEUP | {column: " "})

    def test_unscheduled_with_date_is_rejected(self, session, aircraft):
        assert_rejected(session, "writeup", WRITEUP | {"scheduled_date": "2026-06-20"})

    @pytest.mark.parametrize("status", ["scheduled", "in_progress", "resolved"])
    def test_date_required_once_scheduled(self, session, aircraft, status):
        assert_rejected(session, "writeup", WRITEUP | {"status": status})

    @pytest.mark.parametrize("scheduled_date", [None, "2026-06-20"])
    def test_canceled_with_or_without_date_is_accepted(self, session, aircraft, scheduled_date):
        insert(session, "writeup", WRITEUP | {"status": "canceled", "scheduled_date": scheduled_date})


class TestEvent:
    def test_valid_row_is_accepted(self, session, writeup):
        insert(session, "writeup_event", EVENT)

    def test_unknown_kind_is_rejected(self, session, writeup):
        assert_rejected(session, "writeup_event", EVENT | {"kind": "bogus"})

    def test_blank_actor_is_rejected(self, session, writeup):
        assert_rejected(session, "writeup_event", EVENT | {"actor": ""})

    @pytest.mark.parametrize("kind", ["resolved", "canceled", "severity_changed"])
    @pytest.mark.parametrize("note", [None, "  "])
    def test_note_required(self, session, writeup, kind, note):
        assert_rejected(session, "writeup_event", EVENT | {"kind": kind, "note": note})

    @pytest.mark.parametrize("kind", ["resolved", "canceled", "severity_changed"])
    def test_note_accepted(self, session, writeup, kind):
        insert(session, "writeup_event", EVENT | {"kind": kind, "note": "Replaced the pane"})
