import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before accessing the database")
    return create_engine(database_url)


def get_db() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
