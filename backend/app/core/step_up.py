from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

_security_scheme = HTTPBearer(auto_error=False)


STEP_UP_HEADER = "x-step-up-token"
SENSITIVE_ACTIONS = [
    "change_api_keys",
    "modify_billing",
    "disable_2fa",
    "delete_account",
    "change_email",
    "change_security_settings",
]


def require_step_up(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_security_scheme),
) -> None:
    """
    Middleware dependency for endpoints that require step-up authentication.

    Checks for a valid step-up token in either:
    1. The `X-Step-Up-Token` header (preferred)
    2. The `step_up_verified` claim in the main access token

    Usage:
        @router.post("/api-keys/regenerate")
        def regenerate_api_key(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_step_up),
        ):
            ...
    """
    # First, check if the main access token already has step_up_verified
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("step_up_verified") is True and payload.get("type") == "access":
                return
        except Exception:
            pass

    # Second, check for a step-up token in the custom header
    step_up_token = request.headers.get(STEP_UP_HEADER)
    if step_up_token:
        try:
            payload = decode_token(step_up_token)
            if payload.get("step_up_verified") is True and payload.get("type") == "step_up":
                # Check expiry is already handled by decode_token
                return
        except Exception:
            pass

    # No valid step-up found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Step-up authentication required. Please re-verify your identity.",
        headers={
            "WWW-Authenticate": "Bearer",
            "X-Step-Up-Required": "true",
        },
    )