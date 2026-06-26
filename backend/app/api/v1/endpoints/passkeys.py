import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.security import create_access_token, create_refresh_token
from app.core.webauthn import (
    generate_passkey_registration_options,
    generate_passkey_authentication_options,
    verify_passkey_registration,
    verify_passkey_authentication,
)
from app.core.audit import log_action
from app.models.credential import Credential
from app.models.user import User


router = APIRouter()


# In-memory / Redis challenge store (use Redis in production)
_challenge_store: dict[str, dict] = {}


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
    # Get existing credential IDs to exclude duplicates
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

    # Store challenge
    import uuid
    challenge_id = str(uuid.uuid4())
    _challenge_store[challenge_id] = {
        "challenge": challenge,
        "user_id": str(current_user.id),
        "type": "registration",
        "expires_at": datetime.now(timezone.utc).timestamp() + 120,
    }


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
    # Get stored challenge
    stored = _challenge_store.pop(payload.challenge_id, None)
    if not stored:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")
    if stored["type"] != "registration":
        raise HTTPException(status_code=400, detail="Invalid challenge type")
    if stored["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Challenge belongs to another user")
    if stored["expires_at"] < datetime.now(timezone.utc).timestamp():
        raise HTTPException(status_code=400, detail="Challenge expired. Please try again.")

    try:
        result = verify_passkey_registration(
            credential=payload.credential,
            expected_challenge=stored["challenge"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Passkey verification failed: {str(e)}")

    # Save credential
    credential = Credential(
        user_id=current_user.id,
        credential_id=result["credential_id"],
        public_key=result["public_key"],
        sign_count=result["sign_count"],
        transports=result["transports"],
    )
    session.add(credential)

    # Mark passkey as enabled on user
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

    return {"status": "passkey_registered", "credential_id": result["credential_id"]}


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
        # Find user and their credentials
        user = session.exec(select(User).where(User.email == payload.email)).first()
        if user:
            existing = session.exec(
                select(Credential).where(Credential.user_id == user.id)
            ).all()
            if existing:
                allowed_credentials = [
                    {"id": cred.credential_id, "transports": json.loads(cred.transports) if cred.transports else []}
                    for cred in existing
                ]

    options, challenge = generate_passkey_authentication_options(
        allowed_credentials=allowed_credentials,
    )

    import uuid
    challenge_id = str(uuid.uuid4())
    _challenge_store[challenge_id] = {
        "challenge": challenge,
        "type": "authentication",
        "expires_at": datetime.now(timezone.utc).timestamp() + 120,
    }

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
    stored = _challenge_store.pop(payload.challenge_id, None)
    if not stored:
        raise HTTPException(status_code=400, detail="Challenge not found or expired")
    if stored["type"] != "authentication":
        raise HTTPException(status_code=400, detail="Invalid challenge type")
    if stored["expires_at"] < datetime.now(timezone.utc).timestamp():
        raise HTTPException(status_code=400, detail="Challenge expired. Please try again.")

    # Find the credential by ID
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

    # Update sign count and last used
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
                "id": cred.credential_id[:16] + "...",
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
    """Delete a passkey credential."""
    # We need to search for full credential_id that starts with the given prefix
    credentials = session.exec(
        select(Credential).where(
            Credential.user_id == current_user.id,
            Credential.credential_id.startswith(credential_id.replace("...", "")),
        )
    ).all()

    if not credentials:
        raise HTTPException(status_code=404, detail="Credential not found")

    for cred in credentials:
        session.delete(cred)

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