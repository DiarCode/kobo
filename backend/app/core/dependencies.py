from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import TokenError, decode_token
from app.core.store import STORE


def get_current_user(request: Request) -> dict[str, object]:
    settings = get_settings()
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    user = STORE.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_workspace_member(workspace_id: str, user_id: str) -> dict[str, object]:
    members = STORE.workspace_members.get(workspace_id, [])
    for member in members:
        if member["user_id"] == user_id:
            return member
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
