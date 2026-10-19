from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status

from app.api.deps import AuthSvc, CurrentUser, SettingsDep, get_rate_limiter
from app.api.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
)
from app.application.auth import Session
from app.domain.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def _set_cookie(response: Response, settings, value: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path=COOKIE_PATH,
    )


def _clear_cookie(response: Response, settings) -> None:
    response.delete_cookie(
        COOKIE_NAME, path=COOKIE_PATH, httponly=True, samesite="strict", secure=settings.cookie_secure
    )


def _token(session: Session) -> TokenResponse:
    return TokenResponse(access_token=session.access_token, expires_in=session.expires_in)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, svc: AuthSvc, settings: SettingsDep
):
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    if limiter.is_blocked(ip):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos fallidos. Intenta de nuevo en unos minutos.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
    try:
        session = await svc.login(body.email, body.password)
    except AuthenticationError:
        limiter.register_failure(ip)
        raise
    limiter.reset(ip)
    _set_cookie(response, settings, session.refresh_token)
    return _token(session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    svc: AuthSvc,
    settings: SettingsDep,
    refresh_token: str | None = Cookie(default=None),
):
    try:
        session = await svc.refresh(refresh_token)
    except AuthenticationError:
        _clear_cookie(response, settings)
        raise
    _set_cookie(response, settings, session.refresh_token)
    return _token(session)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    svc: AuthSvc,
    settings: SettingsDep,
    refresh_token: str | None = Cookie(default=None),
):
    await svc.logout(refresh_token)
    _clear_cookie(response, settings)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(body: UserUpdate, user: CurrentUser, svc: AuthSvc):
    return await svc.update_profile(user.id, body.changes())


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordRequest, user: CurrentUser, svc: AuthSvc):
    await svc.change_password(user.id, body.current_password, body.new_password)
    return Response(status_code=204)
