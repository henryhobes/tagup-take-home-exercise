import pytest
from sqlalchemy.orm import Session

from app.db import create_db


@pytest.fixture
def engine(tmp_path):
    return create_db(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
