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


def is_cleared(writeups):
    return not any(w.severity == Severity.high and w.status in OPEN_STATUSES for w in writeups)
