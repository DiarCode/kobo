from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import create_token, hash_password, verify_password
from app.core.store import STORE


def register_user(username: str, password: str) -> dict[str, object]:
    normalized = username.strip().lower()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")
    if normalized in STORE.users_by_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user_id = STORE.new_id()
    user = {
        "id": user_id,
        "username": normalized,
        "password_hash": hash_password(password),
        "created_at": STORE.now_iso(),
    }
    STORE.users[user_id] = user
    STORE.users_by_username[normalized] = user_id
    return user


def authenticate_user(username: str, password: str) -> dict[str, object]:
    normalized = username.strip().lower()
    user_id = STORE.users_by_username.get(normalized)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = STORE.users[user_id]
    if not verify_password(password, str(user["password_hash"])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


def create_auth_tokens(user_id: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "access_token": create_token(user_id, settings.access_token_expire_minutes, "access"),
        "refresh_token": create_token(user_id, settings.refresh_token_expire_minutes, "refresh"),
    }
