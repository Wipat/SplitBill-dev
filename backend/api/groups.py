from typing import Annotated

from dependencies.auth import get_current_user_id, require_group_member
from dependencies.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.group import Group
from models.group_member import GroupMember
from models.user import User
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

router = APIRouter()


class UserSummary(BaseModel):
    id: int
    name: str


class GroupSummary(BaseModel):
    id: int
    name: str
    members: list[UserSummary]


@router.get("/users", response_model=list[UserSummary])
def list_users(db: Annotated[Session, Depends(get_db)]) -> list[UserSummary]:
    users = db.scalars(
        select(User).where(User.deleted_at.is_(None)).order_by(User.name, User.id)
    ).all()
    return [UserSummary(id=user.id, name=user.name) for user in users]


def _group_response(group: Group) -> GroupSummary:
    members = sorted(
        (membership.user for membership in group.members),
        key=lambda user: (user.name, user.id),
    )
    return GroupSummary(
        id=group.id,
        name=group.name,
        members=[
            UserSummary(id=user.id, name=user.name)
            for user in members
            if user.deleted_at is None
        ],
    )


@router.get("/groups", response_model=list[GroupSummary])
def list_user_groups(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GroupSummary]:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    groups = db.scalars(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .options(selectinload(Group.members).selectinload(GroupMember.user))
        .where(GroupMember.user_id == user_id, Group.deleted_at.is_(None))
        .order_by(Group.name, Group.id)
    ).all()
    return [_group_response(group) for group in groups]


@router.get("/groups/{group_id}", response_model=GroupSummary)
def get_group(
    group: Annotated[Group, Depends(require_group_member)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupSummary:
    group = db.scalar(
        select(Group)
        .options(selectinload(Group.members).selectinload(GroupMember.user))
        .where(Group.id == group.id)
    )
    assert group is not None
    return _group_response(group)
