from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.auth import authenticate_user, create_auth_tokens, register_user
from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import TokenError, decode_token
from app.domain.schemas import APIMessage, AuthOut, UserLoginIn, UserOut, UserRegisterIn
from app.services.integrations.github import GITHUB_INTEGRATION
from app.services.integrations.linear import LINEAR_INTEGRATION

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=settings.refresh_token_expire_minutes * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.access_cookie_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(settings.refresh_cookie_name, path="/", domain=settings.cookie_domain)


def _to_user_out(user: dict[str, object]) -> UserOut:
    return UserOut(
        id=str(user["id"]),
        username=str(user["username"]),
        created_at=datetime.fromisoformat(str(user["created_at"])),
    )


@router.post("/register", response_model=AuthOut)
def register(payload: UserRegisterIn, response: Response) -> AuthOut:
    user = register_user(username=payload.username, password=payload.password)
    tokens = create_auth_tokens(str(user["id"]))
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return AuthOut(user=_to_user_out(user))


@router.post("/login", response_model=AuthOut)
def login(payload: UserLoginIn, response: Response) -> AuthOut:
    user = authenticate_user(payload.username, payload.password)
    tokens = create_auth_tokens(str(user["id"]))
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return AuthOut(user=_to_user_out(user))


@router.post("/refresh", response_model=APIMessage)
def refresh(request: Request, response: Response) -> APIMessage:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    tokens = create_auth_tokens(str(payload["sub"]))
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return APIMessage(message="Session refreshed")


@router.post("/logout", response_model=APIMessage)
def logout(response: Response) -> APIMessage:
    _clear_auth_cookies(response)
    return APIMessage(message="Logged out")


@router.get("/me", response_model=UserOut)
def me(user: dict[str, object] = Depends(get_current_user)) -> UserOut:
    return _to_user_out(user)


@router.get("/oauth/{provider}/start", response_model=APIMessage)
def oauth_start(provider: str, state: str = Query("kobo-state")) -> APIMessage:
    if provider == "github":
        url = GITHUB_INTEGRATION.authorize_url(state)
    elif provider == "linear":
        url = LINEAR_INTEGRATION.authorize_url(state)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported provider")
    return APIMessage(message=url)


@router.get("/oauth/{provider}/callback", response_model=APIMessage)
def oauth_callback(provider: str, code: str = Query(...), state: str = Query(...)) -> APIMessage:
    _ = get_settings()
    return APIMessage(message=f"OAuth callback accepted for {provider} with state {state} and code {code[:6]}...")
