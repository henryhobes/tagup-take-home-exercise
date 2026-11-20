import time
from datetime import date, datetime

import pytest

from app.main import day, local_time


@pytest.fixture
def eastern(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setenv("TZ", "America/New_York")
        time.tzset()
        yield
    time.tzset()


def test_day_has_no_leading_zero():
    assert day(date(2026, 6, 5)) == "5 Jun 2026"
    assert day("2026-06-05") == "5 Jun 2026"


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="Windows can't change the process time zone")
def test_local_time_uses_the_offset_in_force_on_that_date(eastern):
    assert local_time(datetime(2026, 7, 1, 18, 0)) == "1 Jul 14:00"
    assert local_time(datetime(2026, 12, 1, 18, 5)) == "1 Dec 13:05"
