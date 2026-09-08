import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from apps.api.app.core.security import hash_password
from packages.schemas.identity import (
    Device,
    DeviceStatus,
    ExternalIdentity,
    ExternalProvider,
    Invitation,
    InvitationStatus,
    Team,
    UserIdentityContextResponse,
    UserRole,
    UserStatus,
)

STORE_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / "db" / "enterprise_identity_store.json"
USERS_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / "db" / "users_store.json"

DEFAULT_USERS: dict[str, dict[str, Any]] = {
    "admin@snapmeet.com": {
        "user_id": "usr_snapmeet_admin",
        "email": "admin@snapmeet.com",
        "name": "SnapMeet Admin",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "role": "ADMIN",
        "is_org_admin": True,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service", "snapmeet/video-transcoder"],
    },
    "rahul@snapmeet.com": {
        "user_id": "usr_rahul",
        "email": "rahul@snapmeet.com",
        "name": "Rahul Sharma",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "role": "LEAD",
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"],
    },
    "aman@snapmeet.com": {
        "user_id": "usr_aman",
        "email": "aman@snapmeet.com",
        "name": "Aman Verma",
        "organization_id": "snapmeet",
        "company_name": "SnapMeet Inc.",
        "role": "DEVELOPER",
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service"],
    },
}


class IdentityService:
    """
    Enterprise Identity, Provisioning, Device Enrollment & Cross-Tool Resolver Service.
    Maintains 1 Human = 1 Canonical KAIRO User mapping across all ingress channels.
    """

    _teams_store: dict[str, list[dict[str, Any]]] = {}
    _team_members_store: dict[str, list[dict[str, Any]]] = {}
    _invitations_store: dict[str, list[dict[str, Any]]] = {}
    _devices_store: dict[str, list[dict[str, Any]]] = {}
    _external_identities_store: dict[str, list[dict[str, Any]]] = {}
    _auth_codes_store: dict[str, dict[str, Any]] = {}

    @classmethod
    def _init_storage(cls) -> None:
        if STORE_FILE.exists():
            try:
                with open(STORE_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    cls._teams_store = data.get("teams", {})
                    cls._team_members_store = data.get("team_members", {})
                    cls._invitations_store = data.get("invitations", {})
                    cls._devices_store = data.get("devices", {})
                    cls._external_identities_store = data.get("external_identities", {})
            except Exception:
                pass

    @classmethod
    def _save_storage(cls) -> None:
        try:
            STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STORE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "teams": cls._teams_store,
                        "team_members": cls._team_members_store,
                        "invitations": cls._invitations_store,
                        "devices": cls._devices_store,
                        "external_identities": cls._external_identities_store,
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except Exception:
            pass

    # =========================================================================
    # Teams Management
    # =========================================================================

    @classmethod
    def create_team(cls, organization_id: str, name: str, description: str | None = None) -> Team:
        cls._init_storage()
        org_teams = cls._teams_store.setdefault(organization_id, [])
        for t in org_teams:
            if t["name"].lower() == name.lower():
                return Team(**t)

        team_id = f"team_{secrets.token_hex(4)}"
        team_record = {
            "id": team_id,
            "organization_id": organization_id,
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "member_count": 0,
        }
        org_teams.append(team_record)
        cls._save_storage()
        return Team(**team_record)

    @classmethod
    def list_teams(cls, organization_id: str) -> list[Team]:
        cls._init_storage()
        org_teams = cls._teams_store.get(organization_id, [])
        memberships = cls._team_members_store.get(organization_id, [])

        teams = []
        for t in org_teams:
            m_count = sum(1 for m in memberships if m.get("team_id") == t["id"])
            teams.append(Team(
                id=t["id"],
                organization_id=organization_id,
                name=t["name"],
                description=t.get("description"),
                created_at=datetime.fromisoformat(t["created_at"]) if isinstance(t["created_at"], str) else t["created_at"],
                updated_at=datetime.fromisoformat(t["updated_at"]) if isinstance(t["updated_at"], str) else t["updated_at"],
                member_count=m_count,
            ))
        return teams

    @classmethod
    def add_user_to_team(cls, organization_id: str, team_id: str, user_id: str) -> None:
        cls._init_storage()
        memberships = cls._team_members_store.setdefault(organization_id, [])
        if not any(m["team_id"] == team_id and m["user_id"] == user_id for m in memberships):
            memberships.append({
                "team_id": team_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            cls._save_storage()

    @classmethod
    def get_user_teams(cls, organization_id: str, user_id: str) -> list[dict[str, Any]]:
        cls._init_storage()
        memberships = cls._team_members_store.get(organization_id, [])
        user_team_ids = {m["team_id"] for m in memberships if m.get("user_id") == user_id}

        teams = cls._teams_store.get(organization_id, [])
        return [t for t in teams if t["id"] in user_team_ids]

    # =========================================================================
    # Invitations & Provisioning
    # =========================================================================

    @classmethod
    def create_invitation(
        cls,
        organization_id: str,
        email: str,
        name: str | None = None,
        team_id: str | None = None,
        role: UserRole = UserRole.DEVELOPER,
        allowed_repos: list[str] | None = None,
    ) -> Invitation:
        cls._init_storage()
        inv_list = cls._invitations_store.setdefault(organization_id, [])

        token = f"kairo_inv_{secrets.token_urlsafe(24)}"
        inv_id = f"inv_{secrets.token_hex(4)}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        record = {
            "id": inv_id,
            "organization_id": organization_id,
            "email": email.lower().strip(),
            "name": name,
            "team_id": team_id,
            "role": role.value if hasattr(role, "value") else str(role),
            "allowed_repos": allowed_repos or [f"{organization_id}/primary-repo"],
            "token": token,
            "status": InvitationStatus.PENDING.value,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        inv_list.append(record)
        cls._save_storage()

        return Invitation(
            id=record["id"],
            organization_id=organization_id,
            email=record["email"],
            name=record["name"],
            team_id=record["team_id"],
            role=UserRole(record["role"]),
            allowed_repos=record["allowed_repos"],
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def list_invitations(cls, organization_id: str) -> list[Invitation]:
        cls._init_storage()
        raw = cls._invitations_store.get(organization_id, [])
        return [
            Invitation(
                id=r["id"],
                organization_id=r["organization_id"],
                email=r["email"],
                name=r.get("name"),
                team_id=r.get("team_id"),
                role=UserRole(r.get("role", "DEVELOPER")),
                allowed_repos=r.get("allowed_repos", []),
                token=r["token"],
                status=InvitationStatus(r.get("status", "PENDING")),
                expires_at=datetime.fromisoformat(r["expires_at"]) if isinstance(r["expires_at"], str) else r["expires_at"],
                created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"],
            )
            for r in raw
        ]

    @classmethod
    def accept_invitation(cls, token: str, name: str, password: str) -> dict[str, Any]:
        cls._init_storage()
        matched_inv = None
        target_org = None

        for org_id, invs in cls._invitations_store.items():
            for inv in invs:
                if inv["token"] == token and inv["status"] == InvitationStatus.PENDING.value:
                    matched_inv = inv
                    target_org = org_id
                    break
            if matched_inv:
                break

        if not matched_inv or not target_org:
            raise ValueError("Invalid or expired invitation token.")

        matched_inv["status"] = InvitationStatus.ACCEPTED.value
        cls._save_storage()

        user_id = f"usr_{secrets.token_hex(4)}"
        email = matched_inv["email"]

        # Create Canonical User in User Store
        new_user = {
            "user_id": user_id,
            "email": email,
            "name": name or matched_inv.get("name") or "Employee",
            "organization_id": target_org,
            "company_name": target_org.capitalize(),
            "password_hash": hash_password(password),
            "is_org_admin": matched_inv.get("role") == UserRole.ADMIN.value,
            "role": matched_inv.get("role", "DEVELOPER"),
            "allowed_repos": matched_inv.get("allowed_repos", [f"{target_org}/primary-repo"]),
            "status": UserStatus.ACTIVE.value,
        }

        # Save to users_store
        users_db = {}
        if USERS_FILE.exists():
            try:
                with open(USERS_FILE, encoding="utf-8") as f:
                    users_db = json.load(f)
            except Exception:
                pass
        users_db[email] = new_user
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_db, f, indent=2)

        # Attach to team if specified
        if matched_inv.get("team_id"):
            cls.add_user_to_team(target_org, matched_inv["team_id"], user_id)

        return new_user

    # =========================================================================
    # Device Enrollment & Sessions
    # =========================================================================

    @classmethod
    def enroll_device(cls, user_id: str, organization_id: str, device_name: str, platform: str = "windows", app_version: str = "2.0.0") -> Device:
        cls._init_storage()
        org_devices = cls._devices_store.setdefault(organization_id, [])

        # Deduplicate or create new device
        for d in org_devices:
            if d.get("user_id") == user_id and d.get("device_name") == device_name:
                d["status"] = DeviceStatus.ACTIVE.value
                d["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                cls._save_storage()
                return Device(
                    id=d["id"],
                    user_id=user_id,
                    organization_id=organization_id,
                    device_name=d["device_name"],
                    platform=d.get("platform", platform),
                    app_version=d.get("app_version", app_version),
                    status=DeviceStatus(d["status"]),
                    last_seen_at=datetime.now(timezone.utc),
                    created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
                )

        device_id = f"dev_{secrets.token_hex(4)}"
        record = {
            "id": device_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "device_name": device_name,
            "platform": platform,
            "app_version": app_version,
            "status": DeviceStatus.ACTIVE.value,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        org_devices.append(record)
        cls._save_storage()

        return Device(
            id=device_id,
            user_id=user_id,
            organization_id=organization_id,
            device_name=device_name,
            platform=platform,
            app_version=app_version,
            status=DeviceStatus.ACTIVE,
            last_seen_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def list_devices(cls, organization_id: str, user_id: str | None = None) -> list[Device]:
        cls._init_storage()
        raw = cls._devices_store.get(organization_id, [])
        if user_id:
            raw = [d for d in raw if d.get("user_id") == user_id]

        return [
            Device(
                id=d["id"],
                user_id=d["user_id"],
                organization_id=d["organization_id"],
                device_name=d["device_name"],
                platform=d.get("platform", "windows"),
                app_version=d.get("app_version", "2.0.0"),
                status=DeviceStatus(d.get("status", "ACTIVE")),
                last_seen_at=datetime.fromisoformat(d["last_seen_at"]) if isinstance(d["last_seen_at"], str) else d["last_seen_at"],
                created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
            )
            for d in raw
        ]

    @classmethod
    def revoke_device(cls, organization_id: str, device_id: str) -> bool:
        cls._init_storage()
        raw = cls._devices_store.get(organization_id, [])
        for d in raw:
            if d["id"] == device_id:
                d["status"] = DeviceStatus.REVOKED.value
                cls._save_storage()
                return True
        return False

    @classmethod
    def is_device_active(cls, organization_id: str, device_id: str) -> bool:
        cls._init_storage()
        raw = cls._devices_store.get(organization_id, [])
        for d in raw:
            if d["id"] == device_id:
                return d.get("status") == DeviceStatus.ACTIVE.value
        return True

    # =========================================================================
    # Cross-Tool External Identity Resolver
    # =========================================================================

    @classmethod
    def link_external_identity(
        cls,
        user_id: str,
        organization_id: str,
        provider: ExternalProvider,
        external_user_id: str,
        external_username: str,
        external_email: str | None = None,
    ) -> ExternalIdentity:
        cls._init_storage()
        org_links = cls._external_identities_store.setdefault(organization_id, [])

        provider_val = provider.value if hasattr(provider, "value") else str(provider)
        # Update existing or add new
        for link in org_links:
            if link["provider"] == provider_val and (link["external_user_id"] == external_user_id or link["external_username"].lower() == external_username.lower()):
                link["user_id"] = user_id
                link["external_username"] = external_username
                link["external_email"] = external_email
                cls._save_storage()
                return ExternalIdentity(
                    id=link["id"],
                    user_id=user_id,
                    organization_id=organization_id,
                    provider=ExternalProvider(provider_val),
                    external_user_id=external_user_id,
                    external_username=external_username,
                    external_email=external_email,
                    verification_status="VERIFIED",
                )

        ident_id = f"ext_{secrets.token_hex(4)}"
        record = {
            "id": ident_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "provider": provider_val,
            "external_user_id": external_user_id,
            "external_username": external_username,
            "external_email": external_email,
            "verification_status": "VERIFIED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        org_links.append(record)
        cls._save_storage()

        return ExternalIdentity(
            id=ident_id,
            user_id=user_id,
            organization_id=organization_id,
            provider=ExternalProvider(provider_val),
            external_user_id=external_user_id,
            external_username=external_username,
            external_email=external_email,
            verification_status="VERIFIED",
        )

    @classmethod
    def list_external_identities(cls, organization_id: str, user_id: str | None = None) -> list[ExternalIdentity]:
        cls._init_storage()
        raw = cls._external_identities_store.get(organization_id, [])
        if user_id:
            raw = [r for r in raw if r.get("user_id") == user_id]

        return [
            ExternalIdentity(
                id=r["id"],
                user_id=r["user_id"],
                organization_id=r["organization_id"],
                provider=ExternalProvider(r["provider"]),
                external_user_id=r["external_user_id"],
                external_username=r["external_username"],
                external_email=r.get("external_email"),
                verification_status=r.get("verification_status", "VERIFIED"),
                created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"],
            )
            for r in raw
        ]

    @classmethod
    def resolve_canonical_user_id(
        cls,
        organization_id: str,
        provider: str,
        external_user_id: str | None = None,
        external_username: str | None = None,
        email: str | None = None,
    ) -> str | None:
        """
        Cross-Tool Resolver: Resolves incoming webhook author/assignee to canonical user_id.
        Strong Signal Order: 1. Explicit external_identity link -> 2. Verified Email match.
        """
        cls._init_storage()
        org_links = cls._external_identities_store.get(organization_id, [])

        # 1. Match by provider + external_user_id or username
        for link in org_links:
            if link.get("provider") == provider:
                if external_user_id and link.get("external_user_id") == external_user_id:
                    return str(link["user_id"])
                if external_username and str(link.get("external_username", "")).lower() == external_username.lower():
                    return str(link["user_id"])

        # 2. Match by email in canonical user store
        if email:
            clean_email = email.lower().strip()
            users_db = dict(DEFAULT_USERS)
            if USERS_FILE.exists():
                try:
                    with open(USERS_FILE, encoding="utf-8") as f:
                        saved = json.load(f)
                        if isinstance(saved, dict):
                            users_db.update(saved)
                except Exception:
                    pass
            for u_email, u_data in users_db.items():
                if u_email.lower() == clean_email and u_data.get("organization_id") == organization_id:
                    matched_uid = str(u_data.get("user_id") or "")
                    # Auto-bind external identity for future fast lookup
                    if external_username and matched_uid:
                        cls.link_external_identity(
                            user_id=matched_uid,
                            organization_id=organization_id,
                            provider=ExternalProvider(provider),
                            external_user_id=external_user_id or external_username,
                            external_username=external_username,
                            external_email=email,
                        )
                    return matched_uid if matched_uid else None

        return None

    # =========================================================================
    # Full Identity Context Builder (/me/context)
    # =========================================================================

    @classmethod
    def get_user_identity_context(
        cls,
        user_id: str,
        organization_id: str,
        device_id: str | None = None,
    ) -> UserIdentityContextResponse:
        cls._init_storage()

        # Fetch canonical user info
        user_info: dict[str, Any] | None = None
        users_db = dict(DEFAULT_USERS)
        if USERS_FILE.exists():
            try:
                with open(USERS_FILE, encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        users_db.update(saved)
            except Exception:
                pass
        for u in users_db.values():
            if u.get("user_id") == user_id or u.get("email") == user_id:
                user_info = u
                break

        if not user_info:
            user_info = {
                "user_id": user_id,
                "name": "Developer",
                "email": f"{user_id}@{organization_id}.com",
                "organization_id": organization_id,
                "company_name": organization_id.capitalize(),
                "role": "DEVELOPER",
                "status": "ACTIVE",
                "allowed_repos": [f"{organization_id}/primary-repo"],
            }

        resolved_uid = str(user_info.get("user_id", user_id))
        teams = cls.get_user_teams(organization_id, resolved_uid)
        devices = cls.list_devices(organization_id, resolved_uid)
        ext_identities = cls.list_external_identities(organization_id, resolved_uid)

        return UserIdentityContextResponse(
            user_id=user_info["user_id"],
            name=user_info.get("name", "Developer"),
            email=user_info.get("email", ""),
            organization_id=organization_id,
            company_name=user_info.get("company_name", organization_id.capitalize()),
            role=user_info.get("role", "DEVELOPER"),
            status=user_info.get("status", "ACTIVE"),
            teams=teams,
            allowed_repos=user_info.get("allowed_repos", []),
            devices=devices,
            external_identities=ext_identities,
            active_device_id=device_id,
        )

    # =========================================================================
    # Single-use Authorization Code Handshake (Deep Link Loopback)
    # =========================================================================

    @classmethod
    def create_authorization_code(cls, user_id: str, organization_id: str) -> str:
        code = secrets.token_urlsafe(32)
        cls._auth_codes_store[code] = {
            "user_id": user_id,
            "organization_id": organization_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }
        return code

    @classmethod
    def exchange_authorization_code(cls, code: str) -> dict[str, Any] | None:
        record = cls._auth_codes_store.pop(code, None)
        if not record:
            return None
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return None
        return record
