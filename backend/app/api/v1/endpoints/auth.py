from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from uuid import UUID

from app.core.database import get_session
from app.core.security_controls import clear_failed_login, enforce_rate_limit, is_login_locked, register_failed_login
from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.core.token_store import is_token_revoked, mark_user_offline, mark_user_online, revoke_token_jti
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Token, TokenRefreshRequest, UserCreate


router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, session: Session = Depends(get_session)) -> Token:
    enforce_rate_limit(request, "register", limit=20, window_seconds=60)

    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = Tenant(name=payload.tenant_name)
    session.add(tenant)
    session.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        role="owner",
        hashed_password=get_password_hash(payload.password),
    )
    session.add(user)
    subscription = Subscription(tenant_id=tenant.id, plan="free", status="active")
    session.add(subscription)
    session.commit()
    session.refresh(user)
    mark_user_online(str(user.tenant_id), str(user.id))

    return Token(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
    )


@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> Token:
    enforce_rate_limit(request, "login", limit=30, window_seconds=60)

    identity = form_data.username.lower().strip()
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        register_failed_login(identity)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    clear_failed_login(identity)
    mark_user_online(str(user.tenant_id), str(user.id))

    return Token(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(payload: TokenRefreshRequest, request: Request, session: Session = Depends(get_session)) -> Token:
    enforce_rate_limit(request, "refresh", limit=40, window_seconds=60)

    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    refresh_jti = decoded.get("jti")
    refresh_exp = decoded.get("exp")
    if not refresh_jti or not refresh_exp:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if is_token_revoked(str(refresh_jti)):
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    subject = decoded.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    try:
        user_uuid = UUID(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user in token") from exc

    user = session.exec(select(User).where(User.id == user_uuid)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    revoke_token_jti(str(refresh_jti), int(refresh_exp))
    mark_user_online(str(user.tenant_id), str(user.id))

    new_refresh = create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role)

    return Token(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=new_refresh,
        role=user.role,
        tenant_id=str(user.tenant_id),
    )


@router.post("/logout")
def logout(payload: TokenRefreshRequest, request: Request) -> dict[str, str]:
    enforce_rate_limit(request, "logout", limit=40, window_seconds=60)

    decoded = decode_token(payload.refresh_token)
    jti = decoded.get("jti")
    subject = decoded.get("sub")
    tenant_id = decoded.get("tenant_id")
    exp = decoded.get("exp")
    if not jti or not exp:
        raise HTTPException(status_code=400, detail="Invalid token")
    if is_token_revoked(str(jti)):
        return {"status": "logged_out"}
    revoke_token_jti(str(jti), int(exp))
    if subject and tenant_id:
        try:
            user_uuid = UUID(subject)
            mark_user_offline(str(tenant_id), str(user_uuid))
        except Exception:
            pass
    return {"status": "logged_out"}
