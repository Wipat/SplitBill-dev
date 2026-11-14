import sys
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dependencies.auth import get_current_user_id, require_group_member
from dependencies.database import get_db
from models import Base, Group, GroupMember, User


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        alice = User(name="alice")
        bob = User(name="bob")
        group = Group(name="Alice and Bob")
        session.add_all([alice, bob, group])
        session.flush()
        session.add(GroupMember(group_id=group.id, user_id=alice.id))
        session.commit()
        alice_id, bob_id, group_id = alice.id, bob.id, group.id

    def override_get_db():
        with Session(engine) as session:
            yield session

    app = FastAPI()

    @app.get("/users/me")
    def current_user(user_id: Annotated[int, Depends(get_current_user_id)]):
        return {"user_id": user_id}

    @app.get("/groups/{group_id}")
    def get_group(group: Annotated[Group, Depends(require_group_member)]):
        return {"id": group.id, "name": group.name}

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, alice_id, bob_id, group_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
