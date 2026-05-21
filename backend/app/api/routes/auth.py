from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.auth_schema import AuthUserRead, LoginRequest, LoginResponse
from app.security.auth import (
    AuthenticatedUser,
    authenticate_user,
    create_access_token,
    require_current_user,
)


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return LoginResponse(access_token=create_access_token(user), user=_user_read(user))


@router.get("/me", response_model=AuthUserRead)
def me(user: AuthenticatedUser = Depends(require_current_user)) -> AuthUserRead:
    return _user_read(user)


def _user_read(user: AuthenticatedUser) -> AuthUserRead:
    return AuthUserRead(username=user.username, name=user.name, role=user.role)
