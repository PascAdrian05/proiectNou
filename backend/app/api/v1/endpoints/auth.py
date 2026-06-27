from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from uuid import UUID

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security_controls import clear_failed_login, enforce_rate_limit, is_login_locked, register_failed_login
from app.core.security import create_access_token, create_refresh_token, create_step_up_token, decode_token, get_password_hash, verify_password
from app.core.step_up import require_step_up
from app.core.token_store import is_token_revoked, mark_user_offline, mark_user_online, revoke_token_jti
from app.core.totp import generate_setup_data, verify_totp
from app.core.backup_codes import generate_backup_codes, remove_used_code, verify_backup_code
from app.core.trusted_device import (
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    build_device_fingerprint,
    create_trusted_device_token,
    verify_trusted_device_token,
)
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
    TokenWith2FA,
    BackupCodesResponse,
    BackupCodeRecoverRequest,
    StepUpRequest,
    StepUpResponse,
    SecurityStatusResponse,
)


router = APIRouter()


def _set_trusted_device_cookie(response: Response, user_id: str, request: Request) -> None:
    """Set the trusted device cookie on the response."""
    fingerprint = build_device_fingerprint(request)
    token = create_trusted_device_token(user_id, fingerprint)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def _check_trusted_device(request: Request, user_id: str) -> bool:
    """Check if the request comes from a trusted device."""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return False
    fingerprint = build_device_fingerprint(request)
    return verify_trusted_device_token(cookie, user_id, fingerprint)


def _calculate_security_score(user: User) -> int:
    """Calculate a security score (0-100) for a user."""
    score = 0
    if user.totp_enabled:
        score += 30
    if user.passkey_enabled:
        score += 35
    if user.backup_codes:
        codes = user.get_backup_codes_list()
        if codes:
            score += 15
    if user.security_setup_completed:
        score += 20
    return min(score, 100)


# === Registration ===

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, session: Session = Depends(get_session)) -> Token:
    enforce_rate_limit(request, "register", limit=20, window_seconds=60)

    # Normalize email so login/register lookups agree.
    normalized_email = (payload.email or "").lower().strip()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")

    existing = session.exec(select(User).where(User.email == normalized_email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = Tenant(name=payload.tenant_name)
    session.add(tenant)
    session.flush()

    user = User(
        tenant_id=tenant.id,
        email=normalized_email,
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
        email=user.email,
    )


# === Login ===

@router.post("/login", response_model=TokenWith2FA)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenWith2FA:
    enforce_rate_limit(request, "login", limit=30, window_seconds=60)

    identity = form_data.username.lower().strip()
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    user = session.exec(select(User).where(User.email == identity)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        register_failed_login(identity)
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
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")

    clear_failed_login(identity)

    # If 2FA is enabled, require 2FA verification
    if user.totp_enabled:
        temp_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            expires_delta=timedelta(minutes=5),
        )
        return TokenWith2FA(
            access_token=temp_token,
            refresh_token="",
            role=user.role,
            tenant_id=str(user.tenant_id),
            requires_2fa=True,
        )

    # No 2FA — proceed with normal login
    mark_user_online(str(user.tenant_id), str(user.id))

    # Set trusted device cookie
    _set_trusted_device_cookie(response, str(user.id), request)

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


# === Token Refresh ===

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
        email=user.email,
    )


# === Logout ===

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


# === 2FA Setup ===

@router.post("/2fa/setup", response_model=TOTPSetupResponse)
def setup_2fa(
    payload: TOTPSetupRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TOTPSetupResponse:
    """Generate TOTP secret and QR code for 2FA setup."""
    user = current_user

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    secret, qr_code = generate_setup_data(user.email)

    user.totp_secret = secret
    session.add(user)
    session.commit()

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
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Enable 2FA after verifying the token."""
    user = current_user
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    if not verify_totp(payload.token, user.totp_secret):
        raise HTTPException(status_code=400, detail="Invalid TOTP token")

    user.totp_enabled = True
    session.add(user)
    session.commit()

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
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_step_up),
) -> dict[str, str]:
    """Disable 2FA.

    Requires step-up authentication (recent TOTP verification) plus a
    password confirmation. Both checks must succeed — the password is
    defended in depth in case the user's session cookie was hijacked.
    """
    user = current_user

    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required to disable 2FA")
    if not verify_password(payload.password, user.hashed_password):
        # Audit the failed attempt before bailing out.
        try:
            log_action(
                session=session,
                user_id=user.id,
                tenant_id=user.tenant_id,
                action="2fa_disable_failed",
                resource_type="user",
                resource_id=str(user.id),
                request=request,
                success=False,
                details={"reason": "invalid_password"},
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid password")
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    session.add(user)
    session.commit()

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
    response: Response,
    session: Session = Depends(get_session),
) -> TokenWith2FA:
    """Verify login with 2FA token."""
    enforce_rate_limit(request, "2fa_verify", limit=20, window_seconds=60)

    identity = payload.email.lower().strip()
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    # Always compare against a normalized email so case / whitespace
    # variants don't bypass the failed-login lockout.
    email_normalized = (payload.email or "").lower().strip()
    if not email_normalized:
        raise HTTPException(status_code=400, detail="Email is required")
    user = session.exec(select(User).where(User.email == email_normalized)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        register_failed_login(identity)
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

    if user.totp_enabled:
        if not user.totp_secret:
            raise HTTPException(status_code=400, detail="2FA enabled but no secret found")

        if not verify_totp(payload.token, user.totp_secret):
            register_failed_login(identity)
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

    # Set trusted device cookie after successful 2FA
    _set_trusted_device_cookie(response, str(user.id), request)

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


# === Backup Codes ===

@router.post("/2fa/backup-codes", response_model=BackupCodesResponse)
def generate_backup_codes_endpoint(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_step_up),
) -> BackupCodesResponse:
    """Generate new backup codes. Invalidates any existing ones.

    Requires step-up auth — replacing backup codes silently could let an
    attacker who briefly hijacks a session lock the real user out.
    """
    user = current_user

    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA must be enabled before generating backup codes")

    plaintext_codes, hashed_codes = generate_backup_codes()
    user.set_backup_codes_list(hashed_codes)
    session.add(user)
    session.commit()

    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="backup_codes_generated",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return BackupCodesResponse(codes=plaintext_codes)


@router.post("/2fa/recover", response_model=TokenWith2FA)
def recover_with_backup_code(
    payload: BackupCodeRecoverRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> TokenWith2FA:
    """Recover account access using a backup code."""
    enforce_rate_limit(request, "2fa_recover", limit=5, window_seconds=300)

    identity = (payload.email or "").lower().strip()
    if not identity:
        raise HTTPException(status_code=400, detail="Email is required")
    if is_login_locked(identity):
        raise HTTPException(status_code=429, detail="Account temporarily locked due to failed logins")

    user = session.exec(select(User).where(User.email == identity)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        register_failed_login(identity)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled on this account")

    hashed_codes = user.get_backup_codes_list()
    if not hashed_codes:
        raise HTTPException(status_code=400, detail="No backup codes available. Contact support for account recovery.")

    if not verify_backup_code(payload.code, hashed_codes):
        register_failed_login(identity)
        log_action(
            session=session,
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="backup_code_recovery_failed",
            resource_type="user",
            resource_id=str(user.id),
            request=request,
            success=False,
        )
        raise HTTPException(status_code=401, detail="Invalid backup code")

    # Remove the used code
    remaining = remove_used_code(payload.code, hashed_codes)
    user.set_backup_codes_list(remaining)
    session.add(user)
    session.commit()

    clear_failed_login(identity)
    mark_user_online(str(user.tenant_id), str(user.id))

    # Set trusted device cookie
    _set_trusted_device_cookie(response, str(user.id), request)

    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="backup_code_recovery_success",
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


# === Step-Up Authentication ===

@router.post("/step-up", response_model=StepUpResponse)
def step_up_authenticate(
    payload: StepUpRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StepUpResponse:
    """Verify identity for sensitive actions (step-up auth)."""
    user = current_user

    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled. Cannot perform step-up authentication.")

    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA secret not found")

    if not verify_totp(payload.token, user.totp_secret):
        log_action(
            session=session,
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="step_up_failed",
            resource_type="user",
            resource_id=str(user.id),
            request=request,
            success=False,
        )
        raise HTTPException(status_code=401, detail="Invalid TOTP token")

    step_up_token = create_step_up_token(
        subject=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        expires_minutes=5,
    )

    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="step_up_success",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return StepUpResponse(step_up_token=step_up_token, expires_in=300)


# === Security Status ===

@router.get("/security-status", response_model=SecurityStatusResponse)
def get_security_status(
    current_user: User = Depends(get_current_user),
) -> SecurityStatusResponse:
    """Get the current security status and score for the authenticated user."""
    user = current_user
    has_codes = bool(user.backup_codes and user.get_backup_codes_list())

    return SecurityStatusResponse(
        totp_enabled=user.totp_enabled,
        passkey_enabled=user.passkey_enabled,
        has_backup_codes=has_codes,
        security_setup_completed=user.security_setup_completed,
        security_score=_calculate_security_score(user),
    )


@router.post("/security-setup-completed")
def mark_security_setup_completed(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Mark the security onboarding wizard as completed."""
    user = current_user
    user.security_setup_completed = True
    session.add(user)
    session.commit()

    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="security_setup_completed",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return {"status": "security_setup_completed"}


