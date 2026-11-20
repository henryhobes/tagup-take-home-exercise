from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import service
from app.models import Aircraft, Writeup
from app.rules import RuleViolation, Severity


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


def get_now():
    return datetime.now(UTC)


DbSession = Annotated[Session, Depends(get_session)]
Now = Annotated[datetime, Depends(get_now)]
# Text fields default to "" because FastAPI treats an empty form field as missing;
# require_text then rejects blank and missing alike with a readable message.
Text = Annotated[str, Form()]


def load_writeup(writeup_id: int, session: DbSession):
    writeup = session.get(Writeup, writeup_id)
    if writeup is None:
        raise HTTPException(404, "Write-up not found")
    return writeup


LoadedWriteup = Annotated[Writeup, Depends(load_writeup)]


def to_writeup(writeup):
    return RedirectResponse(f"/writeups/{writeup.id}", status_code=303)


def create_app(engine):
    app = FastAPI()
    app.state.engine = engine

    @app.exception_handler(RuleViolation)
    def rule_violation(request, exc):
        return PlainTextResponse(str(exc), status_code=400)

    @app.post("/aircraft/{aircraft_id}/writeups")
    def file_writeup(
        aircraft_id: int, session: DbSession, now: Now, severity: Annotated[Severity, Form()],
        reported_by: Text = "", description: Text = "",
    ):
        if session.get(Aircraft, aircraft_id) is None:
            raise HTTPException(404, "Aircraft not found")
        writeup = service.file_writeup(session, aircraft_id, reported_by, description, severity, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/schedule")
    def schedule(
        writeup: LoadedWriteup, session: DbSession, now: Now,
        scheduled_date: Annotated[date, Form()], actor: Text = "",
    ):
        service.schedule(session, writeup, actor, scheduled_date, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/unschedule")
    def unschedule(writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = ""):
        service.unschedule(session, writeup, actor, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/start")
    def start(writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = ""):
        service.start(session, writeup, actor, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/resolve")
    def resolve(writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", note: Text = ""):
        service.resolve(session, writeup, actor, note, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/cancel")
    def cancel(writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", note: Text = ""):
        service.cancel(session, writeup, actor, note, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/severity")
    def change_severity(
        writeup: LoadedWriteup, session: DbSession, now: Now,
        severity: Annotated[Severity, Form()], actor: Text = "", note: Text = "",
    ):
        service.change_severity(session, writeup, actor, severity, note, now)
        return to_writeup(writeup)

    @app.post("/writeups/{writeup_id}/description")
    def edit_description(writeup: LoadedWriteup, session: DbSession, now: Now, actor: Text = "", description: Text = ""):
        service.edit_description(session, writeup, actor, description, now)
        return to_writeup(writeup)

    return app
