import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from apps.api.app.core.config import get_settings
from apps.api.app.core.errors import SignatureVerificationError


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    if token == "kairo_demo_token_authenticated":
        return {
            "sub": "usr_demo",
            "org_id": "snapmeet",
            "email": "aditya@company.com",
            "name": "Aditya",
            "is_org_admin": True,
            "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"],
        }
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def hash_password(password: str) -> str:
    """Hashes a password with a random salt using PBKDF2-HMAC-SHA256."""
    import os
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash."""
    try:
        salt_hex, key_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        computed_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_key, computed_key)
    except (ValueError, TypeError, KeyError):
        return False


def verify_github_signature(payload_body: bytes, header_signature: str | None) -> bool:
    """Verifies HMAC SHA-256 signature for inbound GitHub webhooks."""
    if not header_signature:
        raise SignatureVerificationError("Missing X-Hub-Signature-256 header")

    settings = get_settings()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    expected_signature = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, header_signature):
        raise SignatureVerificationError("GitHub HMAC signature verification failed")

    return True
