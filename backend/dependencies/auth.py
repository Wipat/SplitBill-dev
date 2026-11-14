from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, status
from models.group import Group
from models.group_member import GroupMember
from sqlalchemy import select
from sqlalchemy.orm import Session

from dependencies.database import get_db


def get_current_user_id(
    x_user: Annotated[str | None, Header(alias="X-User")] = None,
) -> int:
    if x_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User header is required",
            headers={"WWW-Authenticate": "X-User"},
        )

    try:
        user_id = int(x_user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User must be a positive integer",
            headers={"WWW-Authenticate": "X-User"},
        ) from exc

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User must be a positive integer",
            headers={"WWW-Authenticate": "X-User"},
        )
    return user_id


def require_group_member(
    group_id: Annotated[int, Path(gt=0)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
) -> Group:
    group = db.scalar(select(Group).where(Group.id == group_id))
    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    membership = db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this group",
        )
    return group
