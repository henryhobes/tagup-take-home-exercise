from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select

from app import rules
from app.models import Aircraft, EventKind, Writeup, WriteupEvent
from app.rules import OPEN_STATUSES, Severity, Status, require_name, require_text


@dataclass
class AircraftStatus:
    aircraft: Aircraft
    open_writeups: list[Writeup]

    @property
    def cleared(self):
        return rules.is_cleared(self.open_writeups)

    @property
    def grounding(self):
        return rules.grounding(self.open_writeups)

    @property
    def needs_scheduling(self):
        return any(w.status == Status.unscheduled for w in self.open_writeups)

    @property
    def next_date(self):
        return min((w.scheduled_date for w in self.open_writeups if w.scheduled_date), default=None)

    def is_overdue(self, today):
        return any(rules.is_overdue(w, today) for w in self.open_writeups)


def fleet_status(session):
    aircraft = session.scalars(select(Aircraft).order_by(Aircraft.tail_number)).all()
    open_writeups = session.scalars(select(Writeup).where(Writeup.status.in_(OPEN_STATUSES))).all()
    by_aircraft = {plane.id: [] for plane in aircraft}
    for writeup in open_writeups:
        by_aircraft[writeup.aircraft_id].append(writeup)
    return [AircraftStatus(plane, by_severity(by_aircraft[plane.id])) for plane in aircraft]


@dataclass
class Board:
    grounded: list[AircraftStatus]
    cleared: list[AircraftStatus]
    fleet_size: int
    grounded_count: int


def board(session, today, query=""):
    fleet = fleet_status(session)
    query = query.strip().lower()
    shown = [s for s in fleet if query in s.aircraft.tail_number.lower()]
    shown.sort(key=lambda s: (
        not s.is_overdue(today), not s.needs_scheduling, s.next_date or date.max, s.aircraft.tail_number,
    ))
    return Board(
        grounded=[s for s in shown if not s.cleared],
        cleared=[s for s in shown if s.cleared],
        fleet_size=len(fleet),
        grounded_count=sum(not s.cleared for s in fleet),
    )


@dataclass
class TimelineEntry:
    at: datetime
    actor: str
    writeup: Writeup
    event: WriteupEvent | None  # None is the filing itself, which lives on the write-up row (A9).


def timeline(aircraft):
    entries = []
    for writeup in aircraft.writeups:
        entries.append(TimelineEntry(writeup.reported_at, writeup.reported_by, writeup, None))
        entries += [TimelineEntry(event.at, event.actor, writeup, event) for event in writeup.events]
    # Reversing a stable sort, rather than sorting descending, puts same-instant entries newest first too.
    return sorted(entries, key=lambda entry: entry.at)[::-1]


def filed_severity(writeup):
    # Filing isn't an audit-log row (A9), so the severity at filing is whatever the first change replaced.
    changes = [event for event in writeup.events if event.kind == EventKind.severity_changed]
    return changes[0].from_value if changes else writeup.severity


def open_writeups(aircraft):
    return by_severity(w for w in aircraft.writeups if w.status in OPEN_STATUSES)


def by_severity(writeups):
    severity_rank = list(Severity).index
    return sorted(writeups, key=lambda w: (severity_rank(w.severity), w.id))


def file_writeup(session, aircraft_id, reported_by, description, severity, now, scheduled_date=None):
    writeup = Writeup(
        aircraft_id=aircraft_id,
        reported_by=require_name(reported_by),
        description=require_text(description, "Description"),
        severity=severity,
        status=Status.unscheduled,
        reported_at=_utc(now),
    )
    session.add(writeup)
    session.flush()
    if scheduled_date is not None:
        schedule(session, writeup, reported_by, scheduled_date, now)
    return writeup


def schedule(session, writeup, actor, new_date, now):
    actor = require_name(actor)
    old_date = writeup.scheduled_date
    kind = EventKind.scheduled if old_date is None else EventKind.rescheduled
    writeup.status = rules.schedule(writeup.status, old_date, new_date, today(now))
    writeup.scheduled_date = new_date
    _log(session, writeup, kind, actor, now, from_value=None if old_date is None else old_date.isoformat(), to_value=new_date.isoformat())


def unschedule(session, writeup, actor, now):
    actor = require_name(actor)
    writeup.status = rules.unschedule(writeup.status)
    old_date = writeup.scheduled_date
    writeup.scheduled_date = None
    _log(session, writeup, EventKind.unscheduled, actor, now, from_value=old_date.isoformat())


def start(session, writeup, actor, now):
    actor = require_name(actor)
    writeup.status = rules.start(writeup.status)
    _log(session, writeup, EventKind.started, actor, now)


def resolve(session, writeup, actor, note, now):
    actor = require_name(actor)
    note = require_text(note, "What was done")
    writeup.status = rules.resolve(writeup.status)
    _log(session, writeup, EventKind.resolved, actor, now, note=note)


def cancel(session, writeup, actor, note, now):
    actor = require_name(actor)
    note = require_text(note, "Reason")
    writeup.status = rules.cancel(writeup.status)
    _log(session, writeup, EventKind.canceled, actor, now, note=note)


def change_severity(session, writeup, actor, severity, note, now):
    actor = require_name(actor)
    note = require_text(note, "Reason")
    old = writeup.severity
    rules.change_severity(writeup.status, old, severity)
    writeup.severity = severity
    _log(session, writeup, EventKind.severity_changed, actor, now, from_value=old, to_value=severity, note=note)


def edit_description(session, writeup, actor, description, now):
    actor = require_name(actor)
    description = require_text(description, "Description")
    old = writeup.description
    rules.edit_description(writeup.status, old, description)
    writeup.description = description
    _log(session, writeup, EventKind.description_edited, actor, now, from_value=old, to_value=description)


def today(now):
    return now.date()


def _log(session, writeup, kind, actor, now, from_value=None, to_value=None, note=None):
    session.add(
        WriteupEvent(
            writeup_id=writeup.id,
            at=_utc(now),
            actor=actor,
            kind=kind,
            from_value=from_value,
            to_value=to_value,
            note=note,
        )
    )


def _utc(now):
    return now.astimezone(UTC).replace(tzinfo=None)

