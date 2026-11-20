import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Aircraft
from tests.common import NOW, TOMORROW, file


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
    change = {"severity": "low", "note": "Cosmetic only", "actor": "Sam Okafor"}
    assert client.post("/writeups/1/severity", data=change).status_code == 303
    assert "Filed as High" in page(client, "/?aircraft=N101TG")


def test_unknown_aircraft_is_404(client):
    assert client.get("/?aircraft=N999TG").status_code == 404


def test_filing_form_has_no_default_severity(client):
    assert "checked" not in page(client, "/?aircraft=N101TG")


def test_failed_action_rerenders_panel_with_message_and_input(client):
    file(client)
    client.post("/writeups/1/schedule", data={"actor": "Jordan Bell", "scheduled_date": TOMORROW.isoformat()})
    client.post("/writeups/1/start", data={"actor": "Sam Okafor"})
    response = client.post("/writeups/1/resolve", data={"actor": "Lee Park", "note": " "})
    assert response.status_code == 400
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
