import sys
from pathlib import Path

import uvicorn
from sqlalchemy.orm import Session

from app.db import create_db
from app.main import create_app, local_now
from app.seed import seed_if_empty

DB_PATH = Path("maintenance.db")

if "--reset" in sys.argv:
    DB_PATH.unlink(missing_ok=True)

engine = create_db(f"sqlite:///{DB_PATH}")
with Session(engine) as session:
    seed_if_empty(session, local_now())

uvicorn.run(create_app(engine), host="127.0.0.1", port=8000)
