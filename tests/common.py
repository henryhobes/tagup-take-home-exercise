from datetime import date, datetime, timedelta, timezone

from app.rules import Status

ZONE = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 15, 12, 0, tzinfo=ZONE)
TODAY = date(2026, 6, 15)
YESTERDAY = date(2026, 6, 14)
TOMORROW = date(2026, 6, 16)

OPEN = [Status.unscheduled, Status.scheduled, Status.in_progress]
CLOSED = [Status.resolved, Status.canceled]
