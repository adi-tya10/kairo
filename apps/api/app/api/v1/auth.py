import json
from pathlib import Path
from typing import Any

from apps.api.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

DB_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / "db" / "users_store.json"

DEFAULT_USERS: dict[str, dict[str, Any]] = {
    "admin@snapmeet.com": {
        "user_id": "usr_snapmeet_admin",
        "email": "admin@snapmeet.com",
        "name": "SnapMeet Admin",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "password_hash": hash_password("KairoEnterprise2026!"),
        "is_org_admin": True,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service", "snapmeet/video-transcoder"],
    },
    "rahul@snapmeet.com": {
        "user_id": "usr_rahul",
        "email": "rahul@snapmeet.com",
        "name": "Rahul Sharma",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "password_hash": hash_password("RahulPass2026!"),
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"],
    },
    "aman@snapmeet.com": {
        "user_id": "usr_aman",
        "email": "aman@snapmeet.com",
        "name": "Aman Verma",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "password_hash": hash_password("AmanPass2026!"),
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service"],
    },
}


def _load_users_from_disk() -> dict[str, dict[str, Any]]:
    """Loads users from persistent disk store with seed fallback."""
    users = dict(DEFAULT_USERS)
    if DB_FILE.exists():
        try:
            with open(DB_FILE, encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    users.update(saved)
        except (json.JSONDecodeError, OSError):
            return users
    return users


def _save_users_to_disk(users: dict[str, dict[str, Any]]) -> None:
    """Persists users to disk so server reloads do not wipe accounts."""
    try:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except OSError:
        return


USERS_DB: dict[str, dict[str, Any]] = _load_users_from_disk()


class RegisterRequest(BaseModel):
    company_name: str
    admin_email: str
    password: str
    plan_tier: str = "ENTERPRISE"


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str
    organization_id: str
    company_name: str
    is_org_admin: bool
    allowed_repos: list[str]


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    name: str
    organization_id: str
    company_name: str
    is_org_admin: bool
    allowed_repos: list[str]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_organization(request_body: RegisterRequest) -> AuthResponse:
    """Registers a new tenant organization and admin credentials with persistent disk storage."""
    email_key = request_body.admin_email.lower().strip()
    if email_key in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization admin account for '{request_body.admin_email}' already exists. Please sign in.",
        )

    slug = request_body.company_name.lower().replace(" ", "-").replace(".", "")
    org_id = slug

    new_user: dict[str, Any] = {
        "user_id": f"usr_{org_id}_admin",
        "email": email_key,
        "name": request_body.company_name + " Admin",
        "organization_id": org_id,
        "company_name": request_body.company_name,
        "password_hash": hash_password(request_body.password),
        "is_org_admin": True,
        "allowed_repos": [f"{org_id}/primary-repo"],
    }
    USERS_DB[email_key] = new_user
    _save_users_to_disk(USERS_DB)

    token = create_access_token({
        "sub": new_user["user_id"],
        "email": new_user["email"],
        "org_id": new_user["organization_id"],
        "is_org_admin": new_user["is_org_admin"],
        "allowed_repos": new_user["allowed_repos"],
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(new_user["user_id"]),
        email=str(new_user["email"]),
        name=str(new_user["name"]),
        organization_id=str(new_user["organization_id"]),
        company_name=str(new_user["company_name"]),
        is_org_admin=bool(new_user["is_org_admin"]),
        allowed_repos=[str(r) for r in new_user["allowed_repos"]],
    )


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_user(request_body: LoginRequest) -> AuthResponse:
    """Authenticates credentials and returns a cryptographic JWT token."""
    email_key = request_body.email.lower().strip()
    user = USERS_DB.get(email_key)

    if not user or not verify_password(request_body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials.",
        )

    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "org_id": user["organization_id"],
        "is_org_admin": user["is_org_admin"],
        "allowed_repos": user["allowed_repos"],
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user["user_id"]),
        email=str(user["email"]),
        name=str(user["name"]),
        organization_id=str(user["organization_id"]),
        company_name=str(user["company_name"]),
        is_org_admin=bool(user["is_org_admin"]),
        allowed_repos=[str(r) for r in user["allowed_repos"]],
    )


@router.get("/me", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    authorization: str | None = Header(None, alias="Authorization"),
) -> UserProfileResponse:
    """Returns the authenticated user's profile based on the JWT Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization Bearer header.",
        )

    raw_token = authorization.split(" ")[1]
    claims = decode_access_token(raw_token)
    email = str(claims.get("email", "")).lower().strip()

    user = USERS_DB.get(email)
    if not user:
        return UserProfileResponse(
            user_id=str(claims.get("sub", "usr_unknown")),
            email=email,
            name=email.split("@")[0].capitalize(),
            organization_id=str(claims.get("org_id", "default_org")),
            company_name=str(claims.get("org_id", "default_org")).replace("-", " ").title(),
            is_org_admin=bool(claims.get("is_org_admin", False)),
            allowed_repos=[str(r) for r in claims.get("allowed_repos", [])],
        )

    return UserProfileResponse(
        user_id=str(user["user_id"]),
        email=str(user["email"]),
        name=str(user["name"]),
        organization_id=str(user["organization_id"]),
        company_name=str(user["company_name"]),
        is_org_admin=bool(user["is_org_admin"]),
        allowed_repos=[str(r) for r in user["allowed_repos"]],
    )
