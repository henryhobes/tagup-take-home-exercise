from enum import StrEnum


class Severity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class Status(StrEnum):
    unscheduled = "unscheduled"
    scheduled = "scheduled"
    in_progress = "in_progress"
    resolved = "resolved"
    canceled = "canceled"


OPEN_STATUSES = {Status.unscheduled, Status.scheduled, Status.in_progress}


def grounding(writeups):
    return [w for w in writeups if w.severity == Severity.high and w.status in OPEN_STATUSES]


def is_cleared(writeups):
    return not grounding(writeups)


class RuleViolation(Exception):
    pass


class WrongStatus(RuleViolation):
    pass


def is_overdue(writeup, today):
    return writeup.status in {Status.scheduled, Status.in_progress} and writeup.scheduled_date < today


def schedule(status, current_date, new_date, today):
    _require_open(status)
    if new_date < today:
        raise RuleViolation("The due date can't be in the past.")
    if new_date == current_date:
        raise RuleViolation("The write-up is already due on that date.")
    if status == Status.unscheduled:
        return Status.scheduled
    return status


def unschedule(status):
    _require_status(status, {Status.scheduled}, "Only a scheduled write-up can be unscheduled.")
    return Status.unscheduled


def start(status):
    _require_status(status, {Status.scheduled}, "Only a scheduled write-up can be started.")
    return Status.in_progress


def resolve(status):
    _require_status(status, {Status.in_progress}, "Only an in-progress write-up can be resolved.")
    return Status.resolved


def cancel(status):
    _require_open(status)
    return Status.canceled


def change_severity(status, current, new):
    _require_open(status)
    if new == current:
        raise RuleViolation(f"Severity is already {current}.")


def edit_description(status, current, new):
    _require_open(status)
    if new == current:
        raise RuleViolation("The description hasn't changed.")


NAME_LIMIT = 100
TEXT_LIMIT = 1000


def require_text(value, field, limit=TEXT_LIMIT):
    value = value.strip()
    if not value:
        raise RuleViolation(f"{field} is required.")
    if len(value) > limit:
        raise RuleViolation(f"{field} can't be longer than {limit} characters.")
    return value


def require_name(value):
    return require_text(value, "Name", NAME_LIMIT)


def _require_open(status):
    _require_status(status, OPEN_STATUSES, f"A {status} write-up can't be changed.")


def _require_status(status, allowed, message):
    if status not in allowed:
        raise WrongStatus(message)
