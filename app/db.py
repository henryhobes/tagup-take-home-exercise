from sqlalchemy import create_engine, event

from app.models import Base


def create_db(url):
    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        # SQLite ignores foreign keys unless each connection opts in.
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    return engine
