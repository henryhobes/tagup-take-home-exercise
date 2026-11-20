from datetime import timedelta

from app import service
from app.models import Aircraft
from app.rules import Severity

PILOT = "Capt. Dana Ruiz"
FIRST_OFFICER = "F/O Marcus Hale"
MECHANIC = "Sam Okafor"
LEAD_MECHANIC = "Lee Park"
CONTROLLER = "Jordan Bell"


def seed(session, now):
    """Builds the demo fleet through the same actions the app uses, with backdated clocks,
    so every seeded write-up and audit entry is one the app could have produced."""

    def ago(days, hours=0):
        return now - timedelta(days=days, hours=hours)

    def day(offset):
        return service.today(now) + timedelta(days=offset)

    planes = {}
    for number in range(401, 431):
        plane = Aircraft(tail_number=f"N{number}TG")
        session.add(plane)
        planes[number] = plane
    session.flush()

    def file(number, severity, description, when, reporter=PILOT):
        return service.file_writeup(session, planes[number].id, reporter, description, severity, when)

    # N401: grounded by a fresh High nobody has scheduled yet.
    file(401, Severity.high, "Cracked outer pane on the left windshield", ago(0, 2))

    # N402: grounded by a High scheduled for tomorrow; an open Low alongside.
    w = file(402, Severity.high, "Hydraulic system B pressure fluctuating in cruise", ago(1))
    service.schedule(session, w, CONTROLLER, day(1), ago(1, -1))
    file(402, Severity.low, "Reading light at seat 14C flickers", ago(3), FIRST_OFFICER)

    # N403: grounded by an overdue High repair in progress that was already rescheduled once.
    w = file(403, Severity.high, "Engine 2 oil pressure warning light comes on intermittently", ago(6))
    service.schedule(session, w, CONTROLLER, day(-4), ago(6, -1))
    service.start(session, w, MECHANIC, ago(4))
    service.schedule(session, w, CONTROLLER, day(-1), ago(3))

    # N404: grounded by two Highs; resolving one isn't enough.
    w = file(404, Severity.high, "Left main gear tire worn to the cords", ago(2))
    service.schedule(session, w, CONTROLLER, day(0), ago(2, -1))
    service.start(session, w, MECHANIC, ago(0, 3))
    file(404, Severity.high, "Smoke detector in the aft lavatory fails self-test", ago(0, 5), FIRST_OFFICER)

    # N405: cleared once its High was fixed.
    w = file(405, Severity.high, "Pitot heat inoperative on the captain's side", ago(5))
    service.schedule(session, w, CONTROLLER, day(-3), ago(5, -1))
    service.start(session, w, LEAD_MECHANIC, ago(3, 1))
    service.resolve(session, w, LEAD_MECHANIC, "Replaced the pitot heater element; tested OK on the ground.", ago(3))

    # N406: cleared after a High was downgraded on inspection.
    w = file(406, Severity.high, "Dent on the leading edge of the right wing", ago(4))
    service.change_severity(
        session, w, LEAD_MECHANIC, Severity.medium,
        "Measured at 2 mm, within structural repair manual limits.", ago(3, 20),
    )
    service.schedule(session, w, CONTROLLER, day(10), ago(3, 18))

    # N407: cleared after a High turned out to be no fault.
    w = file(407, Severity.high, "Fuel quantity indication jumps between readings", ago(3))
    service.schedule(session, w, CONTROLLER, day(2), ago(3, -1))
    service.cancel(
        session, w, LEAD_MECHANIC,
        "No fault found: ran a full gauge test with no discrepancies.", ago(1),
    )

    # N408: cleared despite an overdue Medium; only Highs ground.
    w = file(408, Severity.medium, "Cabin temperature runs hot in the forward zone", ago(9), FIRST_OFFICER)
    service.schedule(session, w, CONTROLLER, day(-2), ago(9, -1))

    # N409: cleared with an unscheduled Low and a duplicate that was canceled before scheduling.
    file(409, Severity.low, "Galley cart latch sticks", ago(2), MECHANIC)
    w = file(409, Severity.low, "Galley cart latch hard to close", ago(1), FIRST_OFFICER)
    service.cancel(session, w, CONTROLLER, "Duplicate of the earlier galley cart write-up.", ago(0, 20))

    # N410: cleared; a Medium that lost its slot and had its description clarified.
    w = file(410, Severity.medium, "Cargo door seal worn", ago(4), MECHANIC)
    service.schedule(session, w, CONTROLLER, day(1), ago(4, -1))
    service.edit_description(session, w, MECHANIC, "Forward cargo door seal worn along the bottom edge", ago(3))
    service.unschedule(session, w, CONTROLLER, ago(1))

    # N411: cleared with a Medium repair in progress and on time.
    w = file(411, Severity.medium, "Autopilot disconnect warning tone is faint", ago(2))
    service.schedule(session, w, CONTROLLER, day(3), ago(2, -1))
    service.start(session, w, MECHANIC, ago(0, 4))

    # N412: cleared; a Low fixed earlier, for history.
    w = file(412, Severity.low, "Tray table at seat 22A won't latch", ago(8), FIRST_OFFICER)
    service.schedule(session, w, CONTROLLER, day(-6), ago(8, -1))
    service.start(session, w, MECHANIC, ago(6, 2))
    service.resolve(session, w, MECHANIC, "Replaced the latch assembly.", ago(6))

    session.commit()
