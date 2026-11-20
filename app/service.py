from dataclasses import dataclass
from datetime import UTC

from sqlalchemy import select

from app import rules
from app.models import Aircraft, EventKind, Writeup, WriteupEvent
from app.rules import OPEN_STATUSES, require_text


@dataclass
class AircraftStatus:
    aircraft: Aircraft
    open_writeups: list[Writeup]

    @property
    def cleared(self):
        return rules.is_cleared(self.open_writeups)


def fleet_status(session):
    aircraft = session.scalars(select(Aircraft).order_by(Aircraft.tail_number)).all()
    open_writeups = session.scalars(
        select(Writeup).where(Writeup.status.in_(OPEN_STATUSES)).order_by(Writeup.id)
    ).all()
    by_aircraft = {plane.id: [] for plane in aircraft}
    for writeup in open_writeups:
        by_aircraft[writeup.aircraft_id].append(writeup)
    return [AircraftStatus(plane, by_aircraft[plane.id]) for plane in aircraft]


def file_writeup(session, aircraft_id, reported_by, description, severity, now):
    writeup = Writeup(
        aircraft_id=aircraft_id,
        reported_by=require_text(reported_by, "Name"),
        description=require_text(description, "Description"),
        severity=severity,
        status=rules.Status.unscheduled,
        reported_at=_utc(now),
    )
    session.add(writeup)
    session.flush()
    return writeup


def schedule(session, writeup, actor, new_date, now):
    actor = require_text(actor, "Name")
    old_date = writeup.scheduled_date
    kind = EventKind.scheduled if old_date is None else EventKind.rescheduled
    writeup.status = rules.schedule(writeup.status, old_date, new_date, today(now))
    writeup.scheduled_date = new_date
    _log(session, writeup, kind, actor, now, from_value=None if old_date is None else old_date.isoformat(), to_value=new_date.isoformat())


def unschedule(session, writeup, actor, now):
    actor = require_text(actor, "Name")
    writeup.status = rules.unschedule(writeup.status)
    old_date = writeup.scheduled_date
    writeup.scheduled_date = None
    _log(session, writeup, EventKind.unscheduled, actor, now, from_value=old_date.isoformat())


def start(session, writeup, actor, now):
    actor = require_text(actor, "Name")
    writeup.status = rules.start(writeup.status)
    _log(session, writeup, EventKind.started, actor, now)


def resolve(session, writeup, actor, note, now):
    actor = require_text(actor, "Name")
    note = require_text(note, "What was done")
    writeup.status = rules.resolve(writeup.status)
    _log(session, writeup, EventKind.resolved, actor, now, note=note)


def cancel(session, writeup, actor, note, now):
    actor = require_text(actor, "Name")
    note = require_text(note, "Reason")
    writeup.status = rules.cancel(writeup.status)
    _log(session, writeup, EventKind.canceled, actor, now, note=note)


def change_severity(session, writeup, actor, severity, note, now):
    actor = require_text(actor, "Name")
    note = require_text(note, "Reason")
    old = writeup.severity
    rules.change_severity(writeup.status, old, severity)
    writeup.severity = severity
    _log(session, writeup, EventKind.severity_changed, actor, now, from_value=old, to_value=severity, note=note)


def edit_description(session, writeup, actor, description, now):
    actor = require_text(actor, "Name")
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

