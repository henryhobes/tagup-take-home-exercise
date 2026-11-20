from types import SimpleNamespace

import pytest

from app.rules import Severity, Status, is_cleared
from tests.common import CLOSED, OPEN


def writeup(severity, status):
    return SimpleNamespace(severity=severity, status=status)


def test_aircraft_with_no_writeups_is_cleared():
    assert is_cleared([])


@pytest.mark.parametrize("status", OPEN)
def test_open_high_grounds(status):
    assert not is_cleared([writeup(Severity.high, status)])


@pytest.mark.parametrize("status", CLOSED)
def test_closed_high_does_not_ground(status):
    assert is_cleared([writeup(Severity.high, status)])


@pytest.mark.parametrize("severity", [Severity.medium, Severity.low])
@pytest.mark.parametrize("status", OPEN + CLOSED)
def test_medium_and_low_never_ground(severity, status):
    assert is_cleared([writeup(severity, status)])


def test_one_open_high_among_resolved_highs_grounds():
    writeups = [
        writeup(Severity.high, Status.resolved),
        writeup(Severity.high, Status.in_progress),
        writeup(Severity.high, Status.canceled),
    ]
    assert not is_cleared(writeups)


def test_cleared_once_every_high_is_closed():
    writeups = [
        writeup(Severity.high, Status.resolved),
        writeup(Severity.high, Status.canceled),
        writeup(Severity.low, Status.unscheduled),
    ]
    assert is_cleared(writeups)
