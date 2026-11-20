from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Writeup
from app.rules import Status

ZONE = timezone(timedelta(hours=-5))
NOW = datetime(2026, 6, 15, 12, 0, tzinfo=ZONE)
TODAY = date(2026, 6, 15)
YESTERDAY = date(2026, 6, 14)
TOMORROW = date(2026, 6, 16)

OPEN = [Status.unscheduled, Status.scheduled, Status.in_progress]
CLOSED = [Status.resolved, Status.canceled]

FILING = {"severity": "high", "description": "Cracked window", "reported_by": "Dana Ruiz"}


def file(client, **overrides):
    response = client.post("/aircraft/1/writeups", data=FILING | overrides)
    assert response.status_code == 303, response.text
    return int(response.headers["location"].rsplit("#writeup-", 1)[1])


def act(client, writeup_id, action, expected=303, **data):
    data.setdefault("actor", "Sam Okafor")
    if "version" not in data:
        data["version"] = current_version(client, writeup_id)
    response = client.post(f"/writeups/{writeup_id}/{action}", data=data)
    assert response.status_code == expected, response.text
    return response


def current_version(client, writeup_id):
    """The version a freshly loaded page would send back."""
    with Session(client.app.state.engine) as session:
        writeup = session.get(Writeup, writeup_id)
        return writeup.version if writeup else 1
