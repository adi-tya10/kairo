import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from packages.schemas.permissions import UserPermissionProfile

from apps.api.app.core.config import get_settings
from apps.api.app.core.errors import SignatureVerificationError


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and cryptographically verifies JWT access tokens with HS256."""
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
) -> UserPermissionProfile:
    """
    Reusable FastAPI dependency for extracting and verifying JWT bearer credentials.
    Replaces duplicated manual header parsing across all route handlers.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization Bearer header.",
        )

    raw_token = authorization.replace("Bearer ", "").strip()
    try:
        payload = decode_access_token(raw_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {exc!s}",
        ) from exc

    return UserPermissionProfile(
        organization_id=str(payload.get("org_id", "")),
        user_id=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        allowed_repo_ids=[str(r) for r in payload.get("allowed_repos", [])],
        is_org_admin=bool(payload.get("is_org_admin", False)),
    )


def hash_password(password: str) -> str:
    """Hashes a password with a random salt using PBKDF2-HMAC-SHA256."""
    import os
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash using constant-time comparison."""
    try:
        salt_hex, key_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        computed_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_key, computed_key)
    except (ValueError, TypeError, KeyError):
        return False


def verify_github_signature(payload_body: bytes, header_signature: str | None) -> bool:
    """Verifies mandatory HMAC SHA-256 signature for inbound GitHub webhooks."""
    if not header_signature:
        raise SignatureVerificationError("Missing X-Hub-Signature-256 header")

    settings = get_settings()
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    expected_signature = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, header_signature):
        raise SignatureVerificationError("GitHub HMAC signature verification failed")

    return True


def verify_jira_signature(payload_body: bytes, header_signature: str | None) -> bool:
    """Verifies mandatory HMAC SHA-256 signature for inbound Jira webhooks."""
    if not header_signature:
        raise SignatureVerificationError("Missing Jira signature header")

    settings = get_settings()
    secret = settings.JIRA_WEBHOOK_SECRET.encode("utf-8")
    computed = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    expected_signature = "sha256=" + computed

    # Support raw hex or sha256= prefix
    target_sig = header_signature.strip()
    if target_sig.startswith("sha256="):
        is_valid = hmac.compare_digest(expected_signature, target_sig)
    else:
        is_valid = hmac.compare_digest(computed, target_sig)

    if not is_valid:
        raise SignatureVerificationError("Jira HMAC signature verification failed")

    return True


def verify_linear_signature(payload_body: bytes, header_signature: str | None) -> bool:
    """Verifies mandatory HMAC SHA-256 signature for inbound Linear webhooks."""
    if not header_signature:
        raise SignatureVerificationError("Missing Linear-Signature header")

    settings = get_settings()
    secret = settings.LINEAR_WEBHOOK_SECRET.encode("utf-8")
    computed = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()

    target_sig = header_signature.strip()
    if target_sig.startswith("sha256="):
        is_valid = hmac.compare_digest("sha256=" + computed, target_sig)
    else:
        is_valid = hmac.compare_digest(computed, target_sig)

    if not is_valid:
        raise SignatureVerificationError("Linear HMAC signature verification failed")

    return True


def verify_gitlab_token(header_token: str | None) -> bool:
    """Verifies mandatory secret token for inbound GitLab webhooks."""
    if not header_token:
        raise SignatureVerificationError("Missing X-Gitlab-Token header")

    settings = get_settings()
    expected_token = settings.GITLAB_WEBHOOK_SECRET
    if not hmac.compare_digest(header_token.strip(), expected_token.strip()):
        raise SignatureVerificationError("GitLab secret token verification failed")

    return True
