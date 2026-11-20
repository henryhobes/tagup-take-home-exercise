from datetime import UTC, date, datetime

from app import service
from app.models import Aircraft
from app.rules import Severity, Status

NOW = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)


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
