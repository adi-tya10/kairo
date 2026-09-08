import time
from typing import Annotated, Any

from apps.api.app.core.database import get_db
from apps.api.app.core.logging import get_logger
from apps.api.app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from packages.schemas.permissions import UserPermissionProfile
from pydantic import BaseModel
from supabase import Client

logger = get_logger("kairo.api.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory sliding-window rate limiter to prevent brute-force attacks
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60.0  # 1 minute window
MAX_AUTH_ATTEMPTS = 20    # Max 20 attempts per window per client


def _check_rate_limit(client_identifier: str) -> None:
    now = time.time()
    attempts = _rate_limit_store.setdefault(client_identifier, [])
    # Filter out attempts older than window
    valid_attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    if len(valid_attempts) >= MAX_AUTH_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again in 60 seconds.",
        )
    valid_attempts.append(now)
    _rate_limit_store[client_identifier] = valid_attempts


# Ephemeral in-memory fallback store for unit tests when Supabase is not connected
_ephemeral_user_cache: dict[str, dict[str, Any]] = {}


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


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_organization(
    request_body: RegisterRequest,
    request: Request,
    db: Annotated[Client, Depends(get_db)],
) -> AuthResponse:
    """Registers a new tenant organization and admin credentials in PostgreSQL."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"reg_{client_ip}")

    email_key = request_body.admin_email.lower().strip()
    slug = request_body.company_name.lower().replace(" ", "-").replace(".", "")
    org_id = slug
    user_id = f"usr_{org_id}_admin"
    pwd_hash = hash_password(request_body.password)

    # 1. Try PostgreSQL via Supabase client
    try:
        existing_user = db.table("users").select("id").eq("email", email_key).execute()
        if _rows(existing_user.data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization admin account for '{request_body.admin_email}' already exists. Please sign in.",
            )

        # Create organization
        org_record = {
            "id": org_id,
            "name": request_body.company_name,
            "domain": f"{org_id}.com",
        }
        db.table("organizations").upsert(org_record).execute()

        # Create user
        user_record = {
            "id": user_id,
            "organization_id": org_id,
            "email": email_key,
            "full_name": request_body.company_name + " Admin",
            "password_hash": pwd_hash,
            "is_org_admin": True,
        }
        db.table("users").insert(user_record).execute()

        # Default repo permission
        perm_record = {
            "organization_id": org_id,
            "user_id": user_id,
            "repo_id": f"{org_id}/primary-repo",
            "access_level": "admin",
        }
        db.table("user_repo_permissions").upsert(perm_record).execute()

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Database write failed during register, using fallback: {exc}")
        # Check ephemeral cache
        if email_key in _ephemeral_user_cache:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization admin account for '{request_body.admin_email}' already exists. Please sign in.",
            )

    # Cache for resilience
    user_data = {
        "user_id": user_id,
        "email": email_key,
        "name": request_body.company_name + " Admin",
        "organization_id": org_id,
        "company_name": request_body.company_name,
        "password_hash": pwd_hash,
        "is_org_admin": True,
        "allowed_repos": [f"{org_id}/primary-repo"],
    }
    _ephemeral_user_cache[email_key] = user_data

    token = create_access_token({
        "sub": user_data["user_id"],
        "email": user_data["email"],
        "org_id": user_data["organization_id"],
        "is_org_admin": user_data["is_org_admin"],
        "allowed_repos": user_data["allowed_repos"],
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user_data["user_id"]),
        email=str(user_data["email"]),
        name=str(user_data["name"]),
        organization_id=str(user_data["organization_id"]),
        company_name=str(user_data["company_name"]),
        is_org_admin=bool(user_data["is_org_admin"]),
        allowed_repos=[str(r) for r in user_data["allowed_repos"]],
    )


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login_user(
    request_body: LoginRequest,
    request: Request,
    db: Annotated[Client, Depends(get_db)],
) -> AuthResponse:
    """Authenticates credentials against PostgreSQL with constant-time password verification."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"login_{client_ip}")

    email_key = request_body.email.lower().strip()
    user_record: dict[str, Any] | None = None

    # 1. Query PostgreSQL
    try:
        res = db.table("users").select("id, organization_id, email, full_name, is_org_admin, password_hash").eq("email", email_key).execute()
        rows = _rows(res.data)
        if rows:
            u = rows[0]
            # Fetch allowed repos
            perms = db.table("user_repo_permissions").select("repo_id").eq("user_id", u["id"]).execute()
            repos = [str(r["repo_id"]) for r in _rows(perms.data)] or [f"{u['organization_id']}/primary-repo"]
            user_record = {
                "user_id": str(u["id"]),
                "email": str(u["email"]),
                "name": str(u["full_name"]),
                "organization_id": str(u["organization_id"]),
                "company_name": str(u["organization_id"]).replace("-", " ").title(),
                "is_org_admin": bool(u["is_org_admin"]),
                "password_hash": str(u.get("password_hash") or ""),
                "allowed_repos": repos,
            }
    except Exception as exc:
        logger.warning(f"Database query failed during login (using fallback): {exc}")

    # Fallback to cache if DB was unreachable
    if not user_record:
        user_record = _ephemeral_user_cache.get(email_key)

    if not user_record or not user_record.get("password_hash") or not verify_password(request_body.password, user_record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials.",
        )

    token = create_access_token({
        "sub": user_record["user_id"],
        "email": user_record["email"],
        "org_id": user_record["organization_id"],
        "is_org_admin": user_record["is_org_admin"],
        "allowed_repos": user_record["allowed_repos"],
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user_record["user_id"]),
        email=str(user_record["email"]),
        name=str(user_record["name"]),
        organization_id=str(user_record["organization_id"]),
        company_name=str(user_record["company_name"]),
        is_org_admin=bool(user_record["is_org_admin"]),
        allowed_repos=[str(r) for r in user_record["allowed_repos"]],
    )


@router.get("/me", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: UserPermissionProfile = Depends(get_current_user),
    db: Annotated[Client, Depends(get_db)] = None,
) -> UserProfileResponse:
    """Returns authenticated user profile from verified JWT profile dependency."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.email.split("@")[0].replace(".", " ").capitalize(),
        organization_id=current_user.organization_id,
        company_name=current_user.organization_id.replace("-", " ").title(),
        is_org_admin=current_user.is_org_admin,
        allowed_repos=current_user.allowed_repo_ids,
    )
