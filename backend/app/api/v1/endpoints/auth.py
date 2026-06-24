from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security_controls import clear_failed_login, enforce_rate_limit, is_login_locked, register_failed_login
from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.core.token_store import is_token_revoked, mark_user_offline, mark_user_online, revoke_token_jti
from app.core.totp import generate_setup_data, verify_totp
from app.core.audit import log_action
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    Token,
    TokenRefreshRequest,
    UserCreate,
    TOTPSetupRequest,
    TOTPSetupResponse,
    TOTPEnableRequest,
    TOTPVerifyRequest,
    TOTPToggleRequest,
    TokenWith2FA
)


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

    # Audit log
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="register",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return Token(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
    )


@router.post("/login", response_model=TokenWith2FA)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)) -> TokenWith2FA:
    enforce_rate_limit(request, "login", limit=30, window_seconds=60)

    identity = form_data.username.lower().strip()
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        register_failed_login(identity)
        # Audit log failed login attempt
        try:
            log_action(
                session=session,
                user_id=user.id if user else None,
                tenant_id=user.tenant_id if user else None,
                action="login_failed",
                resource_type="user",
                request=request,
                success=False,
                details={"reason": "invalid_credentials"},
            )
        except Exception:
            pass  # Don't fail login if audit logging fails
        raise HTTPException(status_code=401, detail="Invalid email or password")

    clear_failed_login(identity)

    # If 2FA is enabled, return temporary token that requires 2FA verification
    if user.totp_enabled:
        # Create a temporary token with short expiry for 2FA verification
        from datetime import timedelta
        temp_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            expires_delta=timedelta(minutes=5)  # Short expiry for 2FA verification
        )
        return TokenWith2FA(
            access_token=temp_token,
            refresh_token="",  # No refresh token for 2FA verification
            role=user.role,
            tenant_id=str(user.tenant_id),
            requires_2fa=True,
        )

    # No 2FA, proceed with normal login
    mark_user_online(str(user.tenant_id), str(user.id))

    # Audit log successful login
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return TokenWith2FA(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
        requires_2fa=False,
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
def logout(payload: TokenRefreshRequest, request: Request, session: Session = Depends(get_session)) -> dict[str, str]:
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
            # Audit log logout
            log_action(
                session=session,
                user_id=user_uuid,
                tenant_id=tenant_id,
                action="logout",
                resource_type="user",
                resource_id=str(user_uuid),
                request=request,
                success=True,
            )
        except Exception:
            pass
    return {"status": "logged_out"}


@router.post("/2fa/setup", response_model=TOTPSetupResponse)
def setup_2fa(
    payload: TOTPSetupRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> TOTPSetupResponse:
    """Generate TOTP secret and QR code for 2FA setup."""
    user = current_user

    # Verify password for security
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Generate new secret and QR code
    secret, qr_code = generate_setup_data(user.email)

    # Temporarily store secret (not enabled yet)
    user.totp_secret = secret
    session.add(user)
    session.commit()

    # Audit log 2FA setup
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="2fa_setup_initiated",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return TOTPSetupResponse(secret=secret, qr_code=qr_code)


@router.post("/2fa/enable")
def enable_2fa(
    payload: TOTPEnableRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """Enable 2FA after verifying the token."""
    user = current_user
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    # Verify the token
    if not verify_totp(payload.token, payload.secret):
        raise HTTPException(status_code=400, detail="Invalid TOTP token")

    # Enable 2FA
    user.totp_enabled = True
    session.add(user)
    session.commit()

    # Audit log 2FA enable
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="2fa_enabled",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return {"status": "2fa_enabled"}


@router.post("/2fa/disable")
def disable_2fa(
    payload: TOTPToggleRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """Disable 2FA."""
    user = current_user
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Disable 2FA
    user.totp_enabled = False
    user.totp_secret = None
    session.add(user)
    session.commit()

    # Audit log 2FA disable
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="2fa_disabled",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return {"status": "2fa_disabled"}


@router.post("/2fa/verify", response_model=TokenWith2FA)
def verify_2fa_login(
    payload: TOTPVerifyRequest,
    request: Request,
    session: Session = Depends(get_session)
) -> TokenWith2FA:
    """Verify login with 2FA token."""
    enforce_rate_limit(request, "2fa_verify", limit=20, window_seconds=60)

    identity = payload.email.lower().strip()
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        register_failed_login(identity)
        # Audit log failed 2FA verification
        try:
            log_action(
                session=session,
                user_id=user.id if user else None,
                tenant_id=user.tenant_id if user else None,
                action="2fa_verification_failed",
                resource_type="user",
                request=request,
                success=False,
                details={"reason": "invalid_credentials"},
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if 2FA is enabled
    if user.totp_enabled:
        if not user.totp_secret:
            raise HTTPException(status_code=400, detail="2FA enabled but no secret found")

        if not verify_totp(payload.token, user.totp_secret):
            register_failed_login(identity)
            # Audit log failed 2FA verification
            try:
                log_action(
                    session=session,
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    action="2fa_verification_failed",
                    resource_type="user",
                    resource_id=str(user.id),
                    request=request,
                    success=False,
                    details={"reason": "invalid_totp_token"},
                )
            except Exception:
                pass
            raise HTTPException(status_code=401, detail="Invalid TOTP token")

    clear_failed_login(identity)
    mark_user_online(str(user.tenant_id), str(user.id))

    # Audit log successful 2FA login
    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="login_2fa_verified",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return TokenWith2FA(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
        requires_2fa=False,
    )