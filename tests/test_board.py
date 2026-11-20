from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Aircraft
from tests.common import NOW, TOMORROW, act, file


@pytest.fixture
def client(engine, session):
    session.add_all([Aircraft(tail_number="N101TG"), Aircraft(tail_number="N202TG")])
    session.commit()
    return TestClient(create_app(engine, clock=lambda: NOW), follow_redirects=False)


def page(client, url="/"):
    response = client.get(url)
    assert response.status_code == 200, response.text
    return response.text


def test_board_lists_grounded_before_cleared_with_reason(client):
    file(client)
    html = page(client)
    assert html.index("N101TG") < html.index("N202TG")
    assert "Cracked window" in html
    assert "1 grounded" in html


def test_empty_group_says_so(client):
    assert "No aircraft grounded" in page(client)


def test_search_filters_by_tail(client):
    html = page(client, "/?q=101")
    assert "N101TG" in html
    assert "N202TG" not in html


def test_search_without_match_says_so(client):
    assert "No aircraft match" in page(client, "/?q=zzz")


def test_aircraft_panel_shows_open_writeups_and_timeline(client):
    file(client)
    html = page(client, "/?aircraft=N101TG")
    assert "Cracked window" in html
    assert "Filed" in html
    assert "Dana Ruiz" in html


def test_timeline_shows_the_severity_a_writeup_was_filed_with(client):
    file(client)
    act(client, 1, "severity", severity="low", note="Cosmetic only")
    assert "Filed as High" in page(client, "/?aircraft=N101TG")


def test_unknown_aircraft_is_404(client):
    assert client.get("/?aircraft=N999TG").status_code == 404


def test_filing_form_has_no_default_severity(client):
    assert "checked" not in page(client, "/?aircraft=N101TG")


def test_failed_action_rerenders_panel_with_message_and_input(client):
    file(client)
    act(client, 1, "schedule", actor="Jordan Bell", scheduled_date=TOMORROW.isoformat())
    act(client, 1, "start")
    response = act(client, 1, "resolve", expected=400, actor="Lee Park", note=" ")
    assert "What was done is required." in response.text
    assert 'value="Lee Park"' in response.text
    assert "N101TG" in response.text


def test_failed_filing_keeps_what_was_typed(client):
    response = client.post("/aircraft/1/writeups", data={"description": "Cracked window", "reported_by": "Dana Ruiz"})
    assert response.status_code == 400
    assert "Severity is required." in response.text
    assert "Cracked window" in response.text


def test_hidden_group_keeps_its_header_and_a_show_link(client):
    html = page(client, "/?hide=cleared")
    assert "N202TG" not in html
    assert "Show" in html


def test_links_keep_search_and_hidden_groups(client):
    html = page(client, "/?q=N&hide=grounded")
    assert "/?q=N&amp;hide=grounded&amp;aircraft=N101TG" in html


def test_cleared_row_lists_its_open_writeups(client):
    file(client, severity="medium", description="Seat 3C recline stuck")
    html = page(client)
    assert "Seat 3C recline stuck" in html


def test_action_the_writeup_has_moved_past_still_shows_why(client):
    file(client)
    act(client, 1, "schedule", actor="Jordan Bell", scheduled_date=TOMORROW.isoformat())
    act(client, 1, "start")
    response = act(client, 1, "start", expected=400, actor="Lee Park")
    assert "Write-up #1 has changed since this page loaded." in response.text
    assert "Only a scheduled write-up can be started." in response.text


def test_action_on_a_closed_writeup_still_shows_why(client):
    file(client)
    act(client, 1, "cancel", note="Duplicate")
    response = act(client, 1, "cancel", expected=400, actor="Lee Park", note="Duplicate")
    assert "Write-up #1 has changed since this page loaded." in response.text
    assert "A canceled write-up" in response.text


def test_search_and_clearing_it_keep_the_open_aircraft(client):
    html = page(client, "/?q=101&aircraft=N202TG")
    assert '<input type="hidden" name="aircraft" value="N202TG">' in html
    assert '<a href="/?aircraft=N202TG">Clear search</a>' in html


def test_row_shows_when_each_open_writeup_is_due(client):
    file(client, scheduled_date=TOMORROW.isoformat())
    file(client, severity="low", description="Reading light flickers")
    html = page(client)
    assert '<span class="due">Due 16 Jun 2026</span>' in html
    assert '<span class="due">Unscheduled</span>' in html


def test_row_marks_an_overdue_writeup(client):
    file(client, scheduled_date=TOMORROW.isoformat())
    client.app.state.clock = lambda: NOW + timedelta(days=2)
    assert '<span class="due due-overdue">Due 16 Jun 2026</span>' in page(client)


def test_the_date_is_called_due_by_wherever_it_is_set_or_shown(client):
    file(client, scheduled_date=TOMORROW.isoformat())
    html = page(client, "/?aircraft=N101TG")
    assert "Due by (optional)" in html
    assert "Scheduled date" not in html
    assert ">Due 16 Jun 2026</summary>" in html
    assert "Scheduled, due by 16 Jun 2026" in html


def test_past_due_date_says_so(client):
    file(client)
    response = act(client, 1, "schedule", expected=400, scheduled_date="2026-06-14")
    assert "The due date can&#39;t be in the past." in response.text


def test_missing_due_date_says_so(client):
    file(client)
    response = act(client, 1, "schedule", expected=400)
    assert "Due date is required." in response.text


def test_every_writeup_form_carries_the_version_it_was_rendered_with(client):
    file(client)
    act(client, 1, "description", description="Cracked left cockpit window")
    html = page(client, "/?aircraft=N101TG")
    assert html.count('<input type="hidden" name="version" value="2">') == html.count(' action="/writeups/1/')
