from fastapi import APIRouter, Depends, status

from app.application.auth import use_cases
from app.interfaces.api.deps import (
    PasswordHasherDep,
    TokenServiceDep,
    UserRepositoryDep,
    auth_rate_limit,
)
from app.interfaces.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(auth_rate_limit)])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(
    payload: RegisterRequest, repo: UserRepositoryDep, hasher: PasswordHasherDep
) -> UserResponse:
    """RF-01. Crea la cuenta con rol ``user``; la contraseña se guarda con bcrypt (cost 12)."""
    user = use_cases.register_user(
        repo,
        hasher,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    repo: UserRepositoryDep,
    hasher: PasswordHasherDep,
    tokens: TokenServiceDep,
) -> TokenResponse:
    """RF-02. Devuelve access token (15 min) y refresh token (7 días)."""
    pair = use_cases.login_user(
        repo, hasher, tokens, email=payload.email, password=payload.password
    )
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    payload: RefreshRequest, repo: UserRepositoryDep, tokens: TokenServiceDep
) -> AccessTokenResponse:
    """Renueva el access token a partir de un refresh token vigente."""
    result = use_cases.refresh_access_token(repo, tokens, refresh_token=payload.refresh_token)
    return AccessTokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )
