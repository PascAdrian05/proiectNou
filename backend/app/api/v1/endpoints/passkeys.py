import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.audit import log_action
from app.core.database import get_session
from app.core.passkey_store import consume_challenge, store_challenge
from app.core.security import create_access_token, create_refresh_token
from app.core.webauthn import (
    generate_passkey_authentication_options,
    generate_passkey_registration_options,
    verify_passkey_authentication,
    verify_passkey_registration,
)
from app.models.credential import Credential
from app.models.user import User


router = APIRouter()


class PasskeyRegistrationBeginResponse(BaseModel):
    """Options to pass to navigator.credentials.create()."""

    publicKey: dict
    challenge_id: str


class PasskeyRegistrationCompleteRequest(BaseModel):
    credential: dict
    challenge_id: str


class PasskeyAuthenticationBeginRequest(BaseModel):
    email: str | None = None


class PasskeyAuthenticationBeginResponse(BaseModel):
    publicKey: dict
    challenge_id: str


class PasskeyAuthenticationCompleteRequest(BaseModel):
    credential: dict
    challenge_id: str
    email: str | None = None


class PasskeyAuthenticationCompleteResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str
    tenant_id: str


class PasskeyCredentialsResponse(BaseModel):
    credentials: list[dict]


# === Registration ===


@router.post("/passkey/register/begin", response_model=PasskeyRegistrationBeginResponse)
def begin_passkey_registration(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PasskeyRegistrationBeginResponse:
    """Begin passkey registration. Returns options for navigator.credentials.create()."""
    existing = session.exec(
        select(Credential).where(Credential.user_id == current_user.id)
    ).all()
    existing_ids = [cred.credential_id for cred in existing]

    options, challenge = generate_passkey_registration_options(
        user_id=str(current_user.id),
        user_email=current_user.email,
        user_display_name=current_user.email.split("@")[0],
        existing_credential_ids=existing_ids,
    )

    challenge_id = store_challenge(
        {
            "challenge": challenge,
            "user_id": str(current_user.id),
            "type": "registration",
        }
    )

    return PasskeyRegistrationBeginResponse(
        publicKey=options,
        challenge_id=challenge_id,
    )


@router.post("/passkey/register/complete")
def complete_passkey_registration(
    payload: PasskeyRegistrationCompleteRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Complete passkey registration after user creates a credential."""
    stored = consume_challenge(payload.challenge_id)
    if not stored:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")
    if stored.get("type") != "registration":
        raise HTTPException(status_code=400, detail="Invalid challenge type")
    if stored.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Challenge belongs to another user")

    try:
        result = verify_passkey_registration(
            credential=payload.credential,
            expected_challenge=stored["challenge"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Passkey verification failed: {str(e)}")

    credential = Credential(
        user_id=current_user.id,
        credential_id=result["credential_id"],
        public_key=result["public_key"],
        sign_count=result["sign_count"],
        transports=result["transports"],
    )
    session.add(credential)

    current_user.passkey_enabled = True
    session.add(current_user)
    session.commit()

    log_action(
        session=session,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        action="passkey_registered",
        resource_type="user",
        resource_id=str(current_user.id),
        request=request,
        success=True,
        details={"credential_id": result["credential_id"][:16]},
    )

    return {"status": "passkey_registered", "credential_id": str(credential.id)}


# === Authentication ===


@router.post("/passkey/login/begin", response_model=PasskeyAuthenticationBeginResponse)
def begin_passkey_authentication(
    payload: PasskeyAuthenticationBeginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> PasskeyAuthenticationBeginResponse:
    """Begin passkey authentication. Returns options for navigator.credentials.get()."""
    allowed_credentials = None

    if payload.email:
        # Email matching is case-insensitive — normalize before lookup.
        email_normalized = payload.email.strip().lower()
        user = session.exec(select(User).where(User.email == email_normalized)).first()
        if user:
            existing = session.exec(
                select(Credential).where(Credential.user_id == user.id)
            ).all()
            if existing:
                allowed_credentials = [
                    {
                        "id": cred.credential_id,
                        "transports": json.loads(cred.transports) if cred.transports else [],
                    }
                    for cred in existing
                ]

    options, challenge = generate_passkey_authentication_options(
        allowed_credentials=allowed_credentials,
    )

    challenge_id = store_challenge(
        {
            "challenge": challenge,
            "type": "authentication",
        }
    )

    return PasskeyAuthenticationBeginResponse(
        publicKey=options,
        challenge_id=challenge_id,
    )


@router.post("/passkey/login/complete", response_model=PasskeyAuthenticationCompleteResponse)
def complete_passkey_authentication(
    payload: PasskeyAuthenticationCompleteRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> PasskeyAuthenticationCompleteResponse:
    """Complete passkey authentication after user selects a credential."""
    stored = consume_challenge(payload.challenge_id)
    if not stored:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")
    if stored.get("type") != "authentication":
        raise HTTPException(status_code=400, detail="Invalid challenge type")

    credential_id = payload.credential.get("id", "")
    if not credential_id:
        raise HTTPException(status_code=400, detail="Missing credential ID")

    stored_cred = session.exec(
        select(Credential).where(Credential.credential_id == credential_id)
    ).first()
    if not stored_cred:
        raise HTTPException(status_code=400, detail="Credential not found")

    user = session.exec(select(User).where(User.id == stored_cred.user_id)).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    try:
        new_sign_count = verify_passkey_authentication(
            credential=payload.credential,
            expected_challenge=stored["challenge"],
            credential_public_key=stored_cred.public_key,
            credential_current_sign_count=stored_cred.sign_count,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Passkey verification failed: {str(e)}")

    stored_cred.sign_count = new_sign_count
    stored_cred.last_used_at = datetime.now(timezone.utc)
    session.add(stored_cred)
    session.commit()

    log_action(
        session=session,
        user_id=user.id,
        tenant_id=user.tenant_id,
        action="passkey_login",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
        success=True,
    )

    return PasskeyAuthenticationCompleteResponse(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id), role=user.role),
        role=user.role,
        tenant_id=str(user.tenant_id),
    )


# === List & Delete Credentials ===


@router.get("/passkey/credentials", response_model=PasskeyCredentialsResponse)
def list_passkey_credentials(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PasskeyCredentialsResponse:
    """List all passkey credentials for the current user."""
    credentials = session.exec(
        select(Credential).where(Credential.user_id == current_user.id)
    ).all()

    return PasskeyCredentialsResponse(
        credentials=[
            {
                # The stable public id is the DB primary key — clients use
                # this when calling DELETE. The WebAuthn id is not exposed.
                "id": str(cred.id),
                "credential_id_preview": cred.credential_id[:16] + "...",
                "created_at": cred.created_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
                "device_name": cred.device_name,
            }
            for cred in credentials
        ]
    )


@router.delete("/passkey/credentials/{credential_id}")
def delete_passkey_credential(
    credential_id: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a passkey credential.

    ``credential_id`` is the stable DB primary key (UUID) returned by
    ``GET /passkey/credentials``. Using a substring prefix of the WebAuthn
    credential id (as the previous implementation did) could match the
    wrong credential.
    """
    try:
        cred_uuid = uuid.UUID(credential_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Credential not found")

    credential = session.exec(
        select(Credential).where(
            Credential.id == cred_uuid,
            Credential.user_id == current_user.id,
        )
    ).first()

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    session.delete(credential)

    # Check if user has any remaining credentials
    remaining = session.exec(
        select(Credential).where(Credential.user_id == current_user.id)
    ).all()
    if not remaining:
        current_user.passkey_enabled = False
        session.add(current_user)

    session.commit()

    log_action(
        session=session,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        action="passkey_deleted",
        resource_type="user",
        resource_id=str(current_user.id),
        request=request,
        success=True,
    )

    return {"status": "credential_deleted"}