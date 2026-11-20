from datetime import date, timedelta

from app import service
from app.models import Aircraft, EventKind
from app.rules import Severity, Status
from tests.common import NOW, TODAY, YESTERDAY


def add_aircraft(session, *tails):
    planes = [Aircraft(tail_number=tail) for tail in tails]
    session.add_all(planes)
    session.commit()
    return planes


def file(session, plane, severity):
    return service.file_writeup(session, plane.id, "Dana Ruiz", "Something wrong", severity, NOW)


def statuses(session):
    return {s.aircraft.tail_number: s for s in service.fleet_status(session)}


def test_fleet_is_sorted_by_tail_number(session):
    add_aircraft(session, "N300TG", "N100TG", "N200TG")
    assert [s.aircraft.tail_number for s in service.fleet_status(session)] == ["N100TG", "N200TG", "N300TG"]


def test_each_aircraft_is_judged_on_its_own_writeups(session):
    grounded, cleared = add_aircraft(session, "N100TG", "N200TG")
    file(session, grounded, Severity.high)
    file(session, cleared, Severity.medium)
    fleet = statuses(session)
    assert not fleet["N100TG"].cleared
    assert fleet["N200TG"].cleared


def test_lists_only_open_writeups(session):
    [plane] = add_aircraft(session, "N100TG")
    still_open = file(session, plane, Severity.low)
    canceled = file(session, plane, Severity.low)
    service.cancel(session, canceled, "Sam Okafor", "Duplicate", NOW)
    assert statuses(session)["N100TG"].open_writeups == [still_open]


def test_resolving_the_last_high_clears_the_aircraft(session):
    [plane] = add_aircraft(session, "N100TG")
    writeup = file(session, plane, Severity.high)
    service.schedule(session, writeup, "Sam Okafor", date(2026, 6, 20), NOW)
    service.start(session, writeup, "Sam Okafor", NOW)
    assert not statuses(session)["N100TG"].cleared
    service.resolve(session, writeup, "Lee Park", "Replaced the pane", NOW)
    assert statuses(session)["N100TG"].cleared
    assert writeup.status == Status.resolved


def test_downgrading_severity_clears_immediately(session):
    [plane] = add_aircraft(session, "N100TG")
    writeup = file(session, plane, Severity.high)
    service.change_severity(session, writeup, "Sam Okafor", Severity.low, "Cosmetic only", NOW)
    assert statuses(session)["N100TG"].cleared


def board_tails(rows):
    return [row.aircraft.tail_number for row in rows]


def schedule(session, writeup, offset_days):
    service.schedule(session, writeup, "Jordan Bell", TODAY + timedelta(days=offset_days), NOW)


class TestBoard:
    def test_splits_fleet_into_grounded_and_cleared(self, session):
        grounded, cleared = add_aircraft(session, "N100TG", "N200TG")
        file(session, grounded, Severity.high)
        board = service.board(session, TODAY)
        assert board_tails(board.grounded) == ["N100TG"]
        assert board_tails(board.cleared) == ["N200TG"]
        assert (board.fleet_size, board.grounded_count) == (2, 1)

    def test_sorts_overdue_then_needs_scheduling_then_earliest_date_then_tail(self, session):
        planes = add_aircraft(session, "N600TG", "N500TG", "N400TG", "N300TG", "N200TG", "N100TG")
        late, unscheduled, soon, later, quiet_b, quiet_a = planes
        overdue = file(session, late, Severity.low)
        schedule(session, overdue, 0)
        overdue.scheduled_date = YESTERDAY
        file(session, unscheduled, Severity.low)
        schedule(session, file(session, soon, Severity.low), 1)
        schedule(session, file(session, later, Severity.low), 5)
        board = service.board(session, TODAY)
        assert board_tails(board.cleared) == ["N600TG", "N500TG", "N400TG", "N300TG", "N100TG", "N200TG"]

    def test_flags_overdue_and_needs_scheduling(self, session):
        [plane] = add_aircraft(session, "N100TG")
        file(session, plane, Severity.medium)
        writeup = file(session, plane, Severity.low)
        schedule(session, writeup, 0)
        writeup.scheduled_date = YESTERDAY
        [row] = service.board(session, TODAY).cleared
        assert row.needs_scheduling
        assert row.is_overdue(TODAY)

    def test_grounding_lists_only_open_highs(self, session):
        [plane] = add_aircraft(session, "N100TG")
        high = file(session, plane, Severity.high)
        file(session, plane, Severity.low)
        [row] = service.board(session, TODAY).grounded
        assert row.grounding == [high]

    def test_search_matches_part_of_tail_ignoring_case(self, session):
        add_aircraft(session, "N401TG", "N402TG", "N510TG")
        board = service.board(session, TODAY, "n40")
        assert board_tails(board.cleared) == ["N401TG", "N402TG"]
        assert board.fleet_size == 3


def test_timeline_lists_filing_and_events_newest_first(session):
    [plane] = add_aircraft(session, "N100TG")
    first = file(session, plane, Severity.high)
    schedule(session, first, 1)
    second = file(session, plane, Severity.low)
    entries = service.timeline(plane)
    assert [(entry.writeup, entry.event.kind if entry.event else "filed") for entry in entries] == [
        (second, "filed"),
        (first, EventKind.scheduled),
        (first, "filed"),
    ]


def test_filed_severity_is_the_one_before_any_change(session):
    [plane] = add_aircraft(session, "N100TG")
    writeup = file(session, plane, Severity.high)
    service.change_severity(session, writeup, "Sam Okafor", Severity.medium, "Within limits", NOW)
    service.change_severity(session, writeup, "Sam Okafor", Severity.low, "Cosmetic only", NOW)
    assert service.filed_severity(writeup) == Severity.high
    assert service.filed_severity(file(session, plane, Severity.low)) == Severity.low
