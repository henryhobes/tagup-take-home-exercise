from types import SimpleNamespace

import pytest

from app import rules
from app.rules import RuleViolation, Severity, Status
from tests.common import CLOSED, OPEN, TODAY, TOMORROW, YESTERDAY

ALL = OPEN + CLOSED


def writeup(status, scheduled_date):
    return SimpleNamespace(status=status, scheduled_date=scheduled_date)


class TestOverdue:
    @pytest.mark.parametrize("status", [Status.scheduled, Status.in_progress])
    def test_open_with_past_date_is_overdue(self, status):
        assert rules.is_overdue(writeup(status, YESTERDAY), TODAY)

    @pytest.mark.parametrize("status", [Status.scheduled, Status.in_progress])
    def test_due_today_is_not_overdue(self, status):
        assert not rules.is_overdue(writeup(status, TODAY), TODAY)

    def test_unscheduled_is_never_overdue(self):
        assert not rules.is_overdue(writeup(Status.unscheduled, None), TODAY)

    @pytest.mark.parametrize("status", CLOSED)
    def test_closed_is_never_overdue(self, status):
        assert not rules.is_overdue(writeup(status, YESTERDAY), TODAY)


class TestSchedule:
    def test_unscheduled_becomes_scheduled(self):
        assert rules.schedule(Status.unscheduled, None, TOMORROW, TODAY) == Status.scheduled

    def test_today_is_allowed(self):
        assert rules.schedule(Status.unscheduled, None, TODAY, TODAY) == Status.scheduled

    def test_rescheduling_keeps_scheduled(self):
        assert rules.schedule(Status.scheduled, TODAY, TOMORROW, TODAY) == Status.scheduled

    def test_rescheduling_keeps_in_progress(self):
        assert rules.schedule(Status.in_progress, TODAY, TOMORROW, TODAY) == Status.in_progress

    def test_overdue_writeup_can_be_rescheduled(self):
        assert rules.schedule(Status.scheduled, YESTERDAY, TODAY, TODAY) == Status.scheduled

    @pytest.mark.parametrize("status", OPEN)
    def test_past_date_is_rejected(self, status):
        current = None if status == Status.unscheduled else TODAY
        with pytest.raises(RuleViolation):
            rules.schedule(status, current, YESTERDAY, TODAY)

    def test_same_date_is_rejected(self):
        with pytest.raises(RuleViolation):
            rules.schedule(Status.scheduled, TOMORROW, TOMORROW, TODAY)

    @pytest.mark.parametrize("status", CLOSED)
    def test_closed_is_rejected(self, status):
        with pytest.raises(RuleViolation):
            rules.schedule(status, TODAY, TOMORROW, TODAY)


def allowed_from(transition, allowed, expected):
    for status in ALL:
        if status in allowed:
            assert transition(status) == expected
        else:
            with pytest.raises(RuleViolation):
                transition(status)


def test_unschedule_only_from_scheduled():
    allowed_from(rules.unschedule, {Status.scheduled}, Status.unscheduled)


def test_start_only_from_scheduled():
    allowed_from(rules.start, {Status.scheduled}, Status.in_progress)


def test_resolve_only_from_in_progress():
    allowed_from(rules.resolve, {Status.in_progress}, Status.resolved)


def test_cancel_from_any_open_status():
    allowed_from(rules.cancel, set(OPEN), Status.canceled)


class TestChangeSeverity:
    @pytest.mark.parametrize("status", OPEN)
    def test_allowed_while_open(self, status):
        rules.change_severity(status, Severity.high, Severity.low)

    @pytest.mark.parametrize("status", CLOSED)
    def test_rejected_once_closed(self, status):
        with pytest.raises(RuleViolation):
            rules.change_severity(status, Severity.high, Severity.low)

    def test_same_severity_is_rejected(self):
        with pytest.raises(RuleViolation):
            rules.change_severity(Status.scheduled, Severity.high, Severity.high)


class TestEditDescription:
    @pytest.mark.parametrize("status", OPEN)
    def test_allowed_while_open(self, status):
        rules.edit_description(status, "Cracked window", "Cracked left cockpit window")

    @pytest.mark.parametrize("status", CLOSED)
    def test_rejected_once_closed(self, status):
        with pytest.raises(RuleViolation):
            rules.edit_description(status, "Cracked window", "Cracked left cockpit window")

    def test_unchanged_description_is_rejected(self):
        with pytest.raises(RuleViolation):
            rules.edit_description(Status.scheduled, "Cracked window", "Cracked window")


class TestRequireText:
    def test_strips_whitespace(self):
        assert rules.require_text("  Dana Ruiz ", "Name") == "Dana Ruiz"

    @pytest.mark.parametrize("value", ["", "   "])
    def test_blank_is_rejected(self, value):
        with pytest.raises(RuleViolation, match="Name"):
            rules.require_text(value, "Name")

    def test_longest_allowed_is_accepted(self):
        assert rules.require_name("x" * rules.NAME_LIMIT) == "x" * rules.NAME_LIMIT
        assert rules.require_text("x" * rules.TEXT_LIMIT, "Description") == "x" * rules.TEXT_LIMIT

    def test_too_long_is_rejected(self):
        with pytest.raises(RuleViolation, match="Name can't be longer than 100 characters."):
            rules.require_name("x" * 101)
        with pytest.raises(RuleViolation, match="Description can't be longer than 1000 characters."):
            rules.require_text("x" * 1001, "Description")

    def test_surrounding_whitespace_does_not_count_toward_the_limit(self):
        assert rules.require_name(" " + "x" * 100 + " ") == "x" * 100
