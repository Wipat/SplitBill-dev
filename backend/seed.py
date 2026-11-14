import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models import Group, GroupMember, User

SEED_USERS = ("alice", "bob", "carol", "dan")
SEED_GROUPS = ("Chiang Mai trip", "Office lunch")
SEED_MEMBERSHIPS = (
    ("Chiang Mai trip", "alice"),
    ("Chiang Mai trip", "bob"),
    ("Chiang Mai trip", "carol"),
    ("Office lunch", "bob"),
    ("Office lunch", "dan"),
)


def seed() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before running the seed script")

    engine = create_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            for name in SEED_USERS:
                if session.scalar(select(User).where(User.name == name)) is None:
                    session.add(User(name=name))
            for name in SEED_GROUPS:
                if session.scalar(select(Group).where(Group.name == name)) is None:
                    session.add(Group(name=name))
            session.flush()

            for group_name, user_name in SEED_MEMBERSHIPS:
                group = session.scalar(select(Group).where(Group.name == group_name))
                user = session.scalar(select(User).where(User.name == user_name))
                assert group is not None and user is not None
                membership = session.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == group.id,
                        GroupMember.user_id == user.id,
                    )
                )
                if membership is None:
                    session.add(GroupMember(group_id=group.id, user_id=user.id))
        print("Seed complete: users, groups, and memberships are present.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed()