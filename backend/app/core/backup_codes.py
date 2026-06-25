import hashlib
import os
import secrets
import string
from typing import List, Tuple


def _hash_code(code: str) -> str:
    """Hash a backup code using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", code.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def _verify_code(code: str, stored: str) -> bool:
    """Verify a backup code against a stored hash."""
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", code.encode(), salt, 100_000)
        return dk == expected
    except (ValueError, TypeError):
        return False


def generate_backup_codes(count: int = 10) -> Tuple[List[str], List[str]]:
    """
    Generate backup codes.

    Returns:
        Tuple of (plaintext_codes, hashed_codes)
    """
    alphabet = string.ascii_uppercase + string.digits
    plaintext_codes = []
    hashed_codes = []

    for _ in range(count):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        code = f"{code[:4]}-{code[4:]}"
        plaintext_codes.append(code)
        hashed_codes.append(_hash_code(code))

    return plaintext_codes, hashed_codes


def verify_backup_code(code: str, hashed_codes: List[str]) -> bool:
    """Verify a backup code against a list of hashed codes."""
    normalized = code.upper().replace("-", "")
    formatted = f"{normalized[:4]}-{normalized[4:]}"

    for hashed in hashed_codes:
        if _verify_code(formatted, hashed):
            return True

    return False


def remove_used_code(code: str, hashed_codes: List[str]) -> List[str]:
    """Remove a used backup code from the list of hashed codes."""
    normalized = code.upper().replace("-", "")
    formatted = f"{normalized[:4]}-{normalized[4:]}"

    remaining = []
    removed = False
    for hashed in hashed_codes:
        if not removed and _verify_code(formatted, hashed):
            removed = True
            continue
        remaining.append(hashed)

    return remaining