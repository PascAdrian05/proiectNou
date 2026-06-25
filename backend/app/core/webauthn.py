import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.config import settings

# We use webauthn-lib for server-side verification
# pip install webauthn-lib
from webauthn import generate_registration_options, verify_registration_response
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    RegistrationCredential,
    AuthenticationCredential,
)
from webauthn.helpers.options_to_json import options_to_json

RP_ID = settings.frontend_url.replace("https://", "").replace("http://", "").split(":")[0]
RP_NAME = settings.app_name
ORIGIN = settings.frontend_url.rstrip("/")


def get_rp_config() -> Dict[str, Any]:
    """Get Relying Party configuration."""
    return {
        "id": RP_ID,
        "name": RP_NAME,
    }


def generate_passkey_registration_options(
    user_id: str,
    user_email: str,
    user_display_name: str,
    existing_credential_ids: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Generate WebAuthn registration options for passkey creation.

    Returns:
        Tuple of (options_dict, challenge_string)
    """
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=UUID(user_id).bytes,
        user_name=user_email,
        user_display_name=user_display_name,
        attestation="none",
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            {"id": cred_id} for cred_id in (existing_credential_ids or [])
        ] if existing_credential_ids else [],
    )

    # Store challenge for later verification
    challenge = options.challenge

    return json.loads(options_to_json(options)), challenge


def verify_passkey_registration(
    credential: Dict[str, Any],
    expected_challenge: str,
    origin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify a passkey registration response.

    Returns:
        Dict with credential_id, public_key, sign_count, transports
    """
    verification = verify_registration_response(
        credential=RegistrationCredential.model_validate(credential),
        expected_challenge=expected_challenge,
        expected_rp_id=RP_ID,
        expected_origin=origin or ORIGIN,
        require_user_verification=True,
    )

    return {
        "credential_id": verification.credential_id,
        "public_key": verification.credential_public_key,
        "sign_count": verification.sign_count,
        "transports": json.dumps(verification.transports or []),
    }


def generate_passkey_authentication_options(
    allowed_credentials: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Generate WebAuthn authentication options for passkey login.

    Returns:
        Tuple of (options_dict, challenge_string)
    """
    options = generate_authentication_options(
        rp_id=RP_ID,
        user_verification=UserVerificationRequirement.REQUIRED,
        allow_credentials=allowed_credentials or [],
    )

    challenge = options.challenge

    return json.loads(options_to_json(options)), challenge


def verify_passkey_authentication(
    credential: Dict[str, Any],
    expected_challenge: str,
    credential_public_key: str,
    credential_current_sign_count: int,
    origin: Optional[str] = None,
) -> int:
    """
    Verify a passkey authentication response.

    Returns:
        New sign count
    """
    verification = verify_authentication_response(
        credential=AuthenticationCredential.model_validate(credential),
        expected_challenge=expected_challenge,
        expected_rp_id=RP_ID,
        expected_origin=origin or ORIGIN,
        credential_public_key=credential_public_key,
        credential_current_sign_count=credential_current_sign_count,
        require_user_verification=True,
    )

    return verification.new_sign_count