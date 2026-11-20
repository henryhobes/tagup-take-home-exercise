from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Path as PathParam, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import service
from app.models import Aircraft, Writeup
from app.rules import RuleViolation, Severity, WrongStatus, is_overdue

HERE = Path(__file__).parent

FIELD_LABELS = {
    "severity": "Severity",
    "scheduled_date": "Due date",
    "actor": "Name",
    "reported_by": "Name",
    "description": "Description",
    "note": "Note",
    "version": "Page version",
}


def local_now():
    # Local time with its zone attached: "today" is the server's local date (A8).
    return datetime.now().astimezone()


def day(value):
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return f"{value.day} {value:%b %Y}"


def local_time(at):
    # Stored as naive UTC (models.py); shown in the server's zone, the same one "today" uses,
    # at the offset that zone had on that date.
    at = at.replace(tzinfo=UTC).astimezone()
    return f"{at.day} {at:%b %H:%M}"


templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["day"] = day
templates.env.filters["local_time"] = local_time
templates.env.globals["Severity"] = Severity
templates.env.globals["is_overdue"] = is_overdue
templates.env.globals["filed_severity"] = service.filed_severity


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


def get_now(request: Request):
    return request.app.state.clock()


DbSession = Annotated[Session, Depends(get_session)]
Now = Annotated[datetime, Depends(get_now)]
Text = Annotated[str, Form()]
# SQLite can't bind an integer wider than 64 bits, so a larger id is rejected as a bad path.
RowId = Annotated[int, PathParam(le=2**63 - 1)]


class StalePage(Exception):
    pass


def load_writeup(writeup_id: RowId, session: DbSession, version: Annotated[int, Form()]):
    """Every write-up form sends back the version it was rendered with, so an action
    taken from a page that is out of date is refused rather than applied to a write-up
    the person hasn't seen."""
    writeup = session.get(Writeup, writeup_id)
    if writeup is None:
        raise HTTPException(404, "Write-up not found")
    if writeup.version != version:
        raise StalePage
    return writeup


LoadedWriteup = Annotated[Writeup, Depends(load_writeup)]


@dataclass
class Failure:
    form_id: str
    message: str
    values: dict


def board_url(query="", hidden=(), tail=""):
    params = [("q", query)] if query else []
    params += [("hide", group) for group in sorted(hidden)]
    if tail:
        params.append(("aircraft", tail))
    return "/?" + urlencode(params) if params else "/"


def board_linker(query, hidden, tail):
    """Builds links from the current board, changing only what the caller names."""
    def link(query=query, tail=tail, toggle=None):
        return board_url(query, hidden ^ {toggle} if toggle else hidden, tail)
    return link


def board_state(request):
    """The search and hidden groups ride along on every link and form so no click loses them."""
    return request.query_params.get("q", ""), set(request.query_params.getlist("hide"))


def done(request, session, writeup):
    query, hidden = board_state(request)
    location = f"{board_url(query, hidden, writeup.aircraft.tail_number)}#writeup-{writeup.id}"
    # Commit here rather than when get_session exits: FastAPI has already sent the response
    # by then, so a failed commit would go unreported.
    session.commit()
    return RedirectResponse(location, status_code=303)


def render_board(request, session, now, tail="", failure=None):
    query, hidden = board_state(request)
    aircraft = None
    if tail:
        aircraft = session.scalar(select(Aircraft).where(func.lower(Aircraft.tail_number) == tail.lower()))
        if aircraft is None:
            raise HTTPException(404, "Aircraft not found")
        tail = aircraft.tail_number
    today = service.today(now)
    context = {
        "board": service.board(session, today, query),
        "query": query,
        "hidden": hidden,
        "link": board_linker(query, hidden, tail),
        "form_query": board_url(query, hidden).removeprefix("/"),
        "aircraft": aircraft,
        "now": now,
        "today": today,
        "failure": failure,
    }
    if aircraft:
        context["status"] = service.AircraftStatus(aircraft, service.open_writeups(aircraft))
        context["timeline"] = service.timeline(aircraft)
    return templates.TemplateResponse(request, "board.html", context, status_code=400 if failure else 200)


async def render_failure(request, message, stale=False):
    """Re-renders the aircraft the failed form belonged to, with the message and what was typed."""
    params = request.path_params
    with Session(request.app.state.engine) as session:
        if "writeup_id" in params:
            writeup = session.get(Writeup, int(params["writeup_id"]))
            if writeup is None:
                return PlainTextResponse("Write-up not found", status_code=404)
            tail = writeup.aircraft.tail_number
            if stale:
                # The form that was submitted isn't on the card any more, so the panel carries the message.
                form_id = "panel"
                message = f"Write-up #{writeup.id} has changed since this page loaded. {message}"
            else:
                form_id = f"{writeup.id}-{request.url.path.rsplit('/', 1)[1]}"
        else:
            aircraft = session.get(Aircraft, int(params["aircraft_id"]))
            if aircraft is None:
                return PlainTextResponse("Aircraft not found", status_code=404)
            tail = aircraft.tail_number
            form_id = "file"
        failure = Failure(form_id, message, dict(await request.form()))
        return render_board(request, session, get_now(request), tail=tail, failure=failure)


def create_app(engine, clock=local_now):
    app = FastAPI()
    app.state.engine = engine
    app.state.clock = clock
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        # FastAPI's default answers in JSON; every other error here is text or the page itself.
        return PlainTextResponse(exc.detail, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RuleViolation)
    async def rule_violation(request, exc):
        return await render_failure(request, str(exc), stale=isinstance(exc, WrongStatus))

    @app.exception_handler(StalePage)
    @app.exception_handler(StaleDataError)
    async def changed_meanwhile(request, exc):
        return await render_failure(request, "Nothing was saved.", stale=True)

    @app.exception_handler(RequestValidationError)
    async def invalid_form(request, exc):
        if any(error["loc"][0] == "path" for error in exc.errors()):
            return PlainTextResponse("Not found", status_code=404)
        message = " ".join(
            f"{FIELD_LABELS[error['loc'][-1]]} is {'required' if error['type'] == 'missing' else 'invalid'}."
            for error in exc.errors()
        )
        return await render_failure(request, message)

    @app.get("/")
    def fleet(request: Request, session: DbSession, now: Now, aircraft: str = ""):
        return render_board(request, session, now, aircraft)

    # Text fields default to "" because FastAPI treats an empty form field as missing
    # and Annotated[..., Form()] can't carry a default; require_text in the service then
    # rejects blank and missing alike with a readable message.

    @app.post("/aircraft/{aircraft_id}/writeups")
    def file_writeup(
        request: Request, aircraft_id: RowId, session: DbSession, now: Now, severity: Annotated[Severity, Form()],
        reported_by: Text = "", description: Text = "", scheduled_date: Annotated[date | None, Form()] = None,
    ):
        if session.get(Aircraft, aircraft_id) is None:
            raise HTTPException(404, "Aircraft not found")
        writeup = service.file_writeup(session, aircraft_id, reported_by, description, severity, now, scheduled_date)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/schedule")
    def schedule(
        request: Request, writeup: LoadedWriteup, session: DbSession, now: Now,
        scheduled_date: Annotated[date, Form()], actor: Text = "",
    ):
        service.schedule(session, writeup, actor, scheduled_date, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/unschedule")
    def unschedule(request: Request, writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = ""):
        service.unschedule(session, writeup, actor, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/start")
    def start(request: Request, writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = ""):
        service.start(session, writeup, actor, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/resolve")
    def resolve(request: Request, writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", note: Text = ""):
        service.resolve(session, writeup, actor, note, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/cancel")
    def cancel(request: Request, writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", note: Text = ""):
        service.cancel(session, writeup, actor, note, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/severity")
    def change_severity(
        request: Request, writeup: LoadedWriteup, session: DbSession, now: Now,
        severity: Annotated[Severity, Form()], actor: Text = "", note: Text = "",
    ):
        service.change_severity(session, writeup, actor, severity, note, now)
        return done(request, session, writeup)

    @app.post("/writeups/{writeup_id}/description")
    def edit_description(request: Request, writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", description: Text = ""):
        service.edit_description(session, writeup, actor, description, now)
        return done(request, session, writeup)

    return app
