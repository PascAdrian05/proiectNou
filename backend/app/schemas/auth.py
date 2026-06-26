from typing import List

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    role: str | None = None
    tenant_id: str | None = None
    email: str | None = None


class TokenPayload(BaseModel):
    sub: str | None = None


class UserCreate(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TOTPSetupRequest(BaseModel):
    password: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str


class TOTPEnableRequest(BaseModel):
    secret: str
    token: str


class TOTPVerifyRequest(BaseModel):
    email: str
    password: str
    token: str


class TOTPToggleRequest(BaseModel):
    password: str


class TokenWith2FA(Token):
    requires_2fa: bool = False


# === Backup Codes ===

class BackupCodesResponse(BaseModel):
    codes: List[str]
    message: str = "Save these backup codes in a secure place. Each code can only be used once."


class BackupCodeRecoverRequest(BaseModel):
    email: str
    password: str
    code: str


# === Step-Up Authentication ===

class StepUpRequest(BaseModel):
    token: str  # TOTP token to verify


class StepUpResponse(BaseModel):
    step_up_token: str  # Short-lived token with step_up_verified claim
    expires_in: int  # Seconds until expiry


# === Security Status ===

class SecurityStatusResponse(BaseModel):
    totp_enabled: bool
    passkey_enabled: bool
    has_backup_codes: bool
    security_setup_completed: bool
    security_score: int
