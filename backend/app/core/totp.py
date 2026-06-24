import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
from typing import Tuple


def generate_totp_secret() -> str:
    """Generate a new TOTP secret key."""
    return pyotp.random_base32()


def generate_totp_uri(email: str, secret: str, issuer: str = "Security Monitor") -> str:
    """Generate TOTP URI for QR code."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer
    )


def generate_qr_code(uri: str) -> str:
    """Generate QR code as base64 data URI."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    # Use SVG factory to avoid pypng/Pillow compatibility issues
    img = qr.make_image(image_factory=qrcode.image.svg.SvgImage, fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/svg+xml;base64,{img_str}"


def verify_totp(token: str, secret: str) -> bool:
    """Verify TOTP token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def generate_setup_data(email: str) -> Tuple[str, str]:
    """Generate TOTP setup data (secret and QR code)."""
    secret = generate_totp_secret()
    uri = generate_totp_uri(email, secret)
    qr_code = generate_qr_code(uri)
    return secret, qr_code
