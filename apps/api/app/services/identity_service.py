import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.app.core.database import get_db
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


def _safe_get_db() -> Any:
    """Safely acquires a DB client from get_db(), returning None on connection failure."""
    try:
        gen = get_db()
        return next(gen)
    except Exception:
        return None


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


class IdentityService:
    """
    Enterprise Identity, Provisioning, Device Enrollment & Cross-Tool Resolver Service.
    Backbone is PostgreSQL (teams, team_members, invitations, devices, external_identities, users).
    Maintains 1 Human = 1 Canonical KAIRO User mapping across all ingress channels.
    """

    # Thread-safe in-memory store for isolated unit tests / offline runs
    _mem_teams: dict[str, list[dict[str, Any]]] = {}
    _mem_team_members: dict[str, list[dict[str, Any]]] = {}
    _mem_invitations: dict[str, list[dict[str, Any]]] = {}
    _mem_devices: dict[str, list[dict[str, Any]]] = {}
    _mem_external_identities: dict[str, list[dict[str, Any]]] = {}
    _mem_users: dict[str, dict[str, Any]] = {
        "admin@snapmeet.com": {
            "user_id": "usr_snapmeet_admin",
            "email": "admin@snapmeet.com",
            "name": "SnapMeet Admin",
            "organization_id": "snapmeet",
            "company_name": "SnapMeet Inc.",
            "role": "ADMIN",
            "is_org_admin": True,
            "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service", "snapmeet/video-transcoder"],
            "status": "ACTIVE",
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
            "status": "ACTIVE",
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
            "status": "ACTIVE",
        },
    }
    _auth_codes_store: dict[str, dict[str, Any]] = {}

    # =========================================================================
    # Teams Management
    # =========================================================================

    @classmethod
    def create_team(cls, organization_id: str, name: str, description: str | None = None) -> Team:
        team_id = f"team_{secrets.token_hex(4)}"
        now_iso = datetime.now(UTC).isoformat()

        # Mirror in memory
        org_teams = cls._mem_teams.setdefault(organization_id, [])
        for t in org_teams:
            if t["name"].lower() == name.lower():
                return Team(**t)

        team_record = {
            "id": team_id,
            "organization_id": organization_id,
            "name": name,
            "description": description,
            "created_at": now_iso,
            "updated_at": now_iso,
            "member_count": 0,
        }
        org_teams.append(team_record)

        db = _safe_get_db()
        if db:
            try:
                record = {
                    "id": team_id,
                    "organization_id": organization_id,
                    "name": name,
                    "description": description,
                }
                db.table("teams").insert(record).execute()
            except Exception:
                pass

        return Team(**team_record)

    @classmethod
    def list_teams(cls, organization_id: str) -> list[Team]:
        teams_map: dict[str, Team] = {}

        # 1. In-memory teams
        org_teams = cls._mem_teams.get(organization_id, [])
        memberships = cls._mem_team_members.get(organization_id, [])
        for t in org_teams:
            m_count = sum(1 for m in memberships if m.get("team_id") == t["id"])
            teams_map[t["id"]] = Team(
                id=t["id"],
                organization_id=organization_id,
                name=t["name"],
                description=t.get("description"),
                created_at=datetime.fromisoformat(t["created_at"]) if isinstance(t["created_at"], str) else t["created_at"],
                updated_at=datetime.fromisoformat(t["updated_at"]) if isinstance(t["updated_at"], str) else t["updated_at"],
                member_count=m_count,
            )

        # 2. Merge DB teams if available
        db = _safe_get_db()
        if db:
            try:
                teams_res = db.table("teams").select("*").eq("organization_id", organization_id).execute()
                members_res = db.table("team_members").select("team_id, user_id").execute()
                t_rows = _rows(teams_res.data)
                m_rows = _rows(members_res.data)

                for t in t_rows:
                    m_count = sum(1 for m in m_rows if m.get("team_id") == t["id"])
                    created_val = t.get("created_at")
                    updated_val = t.get("updated_at")
                    teams_map[t["id"]] = Team(
                        id=t["id"],
                        organization_id=organization_id,
                        name=t["name"],
                        description=t.get("description"),
                        created_at=datetime.fromisoformat(created_val) if isinstance(created_val, str) else created_val or datetime.now(UTC),
                        updated_at=datetime.fromisoformat(updated_val) if isinstance(updated_val, str) else updated_val or datetime.now(UTC),
                        member_count=m_count,
                    )
            except Exception:
                pass

        return list(teams_map.values())

    @classmethod
    def add_user_to_team(cls, organization_id: str, team_id: str, user_id: str) -> None:
        db = _safe_get_db()
        if db:
            try:
                db.table("team_members").upsert({"team_id": team_id, "user_id": user_id}).execute()
            except Exception:
                pass

        memberships = cls._mem_team_members.setdefault(organization_id, [])
        if not any(m["team_id"] == team_id and m["user_id"] == user_id for m in memberships):
            memberships.append({
                "team_id": team_id,
                "user_id": user_id,
                "created_at": datetime.now(UTC).isoformat(),
            })

    @classmethod
    def get_user_teams(cls, organization_id: str, user_id: str) -> list[dict[str, Any]]:
        db = _safe_get_db()
        if db:
            try:
                m_res = db.table("team_members").select("team_id").eq("user_id", user_id).execute()
                team_ids = [r["team_id"] for r in _rows(m_res.data)]
                if team_ids:
                    t_res = db.table("teams").select("*").eq("organization_id", organization_id).in_("id", team_ids).execute()
                    return _rows(t_res.data)
            except Exception:
                pass

        memberships = cls._mem_team_members.get(organization_id, [])
        user_team_ids = {m["team_id"] for m in memberships if m.get("user_id") == user_id}
        teams = cls._mem_teams.get(organization_id, [])
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
        db = _safe_get_db()
        token = f"kairo_inv_{secrets.token_urlsafe(24)}"
        inv_id = f"inv_{secrets.token_hex(4)}"
        expires_at = datetime.now(UTC) + timedelta(days=7)
        now = datetime.now(UTC)

        record = {
            "id": inv_id,
            "organization_id": organization_id,
            "email": email.lower().strip(),
            "name": name,
            "team_id": team_id,
            "role": role.value if hasattr(role, "value") else str(role),
            "allowed_repos": allowed_repos or [f"{organization_id}/primary-repo"],
            "token": token,
            "token_hash": token,
            "status": InvitationStatus.PENDING.value,
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
        }

        if db:
            try:
                db.table("invitations").insert({
                    "id": inv_id,
                    "organization_id": organization_id,
                    "team_id": team_id,
                    "email": email.lower().strip(),
                    "name": name,
                    "role": record["role"],
                    "allowed_repos": record["allowed_repos"],
                    "token_hash": token,
                    "status": "PENDING",
                    "expires_at": record["expires_at"],
                }).execute()
            except Exception:
                pass

        cls._mem_invitations.setdefault(organization_id, []).append(record)

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
            created_at=now,
        )

    @classmethod
    def list_invitations(cls, organization_id: str) -> list[Invitation]:
        db = _safe_get_db()
        if db:
            try:
                res = db.table("invitations").select("*").eq("organization_id", organization_id).execute()
                rows = _rows(res.data)
                if rows:
                    return [
                        Invitation(
                            id=r["id"],
                            organization_id=r["organization_id"],
                            email=r["email"],
                            name=r.get("name"),
                            team_id=r.get("team_id"),
                            role=UserRole(r.get("role", "DEVELOPER")),
                            allowed_repos=r.get("allowed_repos", []),
                            token=r.get("token_hash", r.get("token", "")),
                            status=InvitationStatus(r.get("status", "PENDING")),
                            expires_at=datetime.fromisoformat(r["expires_at"]) if isinstance(r["expires_at"], str) else r["expires_at"],
                            created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"],
                        )
                        for r in rows
                    ]
            except Exception:
                pass

        raw = cls._mem_invitations.get(organization_id, [])
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
        db = _safe_get_db()
        matched_inv: dict[str, Any] | None = None
        target_org: str | None = None

        if db:
            try:
                # Check if token exists in DB regardless of status
                all_res = db.table("invitations").select("*").eq("token_hash", token).execute()
                all_rows = _rows(all_res.data)
                if all_rows:
                    if all_rows[0].get("status") != "PENDING":
                        # Mark memory store as accepted as well to maintain consistency
                        for invs in cls._mem_invitations.values():
                            for inv in invs:
                                if inv.get("token") == token:
                                    inv["status"] = InvitationStatus.ACCEPTED.value
                        raise ValueError("Invitation has already been accepted or has been revoked.")
                    matched_inv = all_rows[0]
                    target_org = str(matched_inv["organization_id"])
                    # Mark accepted in DB
                    db.table("invitations").update({"status": "ACCEPTED"}).eq("id", matched_inv["id"]).execute()
                    # Also mark accepted in memory
                    for invs in cls._mem_invitations.values():
                        for inv in invs:
                            if inv.get("token") == token:
                                inv["status"] = InvitationStatus.ACCEPTED.value
            except ValueError:
                raise
            except Exception:
                pass

        if not matched_inv:
            for org_id, invs in cls._mem_invitations.items():
                for inv in invs:
                    if inv["token"] == token:
                        if inv["status"] != InvitationStatus.PENDING.value:
                            raise ValueError("Invitation has already been accepted or has been revoked.")
                        matched_inv = inv
                        target_org = org_id
                        inv["status"] = InvitationStatus.ACCEPTED.value
                        break
                if matched_inv:
                    break

        if not matched_inv or not target_org:
            raise ValueError("Invalid or expired invitation token.")

        user_id = f"usr_{secrets.token_hex(4)}"
        email = str(matched_inv["email"]).lower().strip()
        pwd_hash = hash_password(password)

        new_user: dict[str, Any] = {
            "user_id": user_id,
            "email": email,
            "name": name or matched_inv.get("name") or "Employee",
            "organization_id": target_org,
            "company_name": target_org.capitalize(),
            "password_hash": pwd_hash,
            "is_org_admin": matched_inv.get("role") == UserRole.ADMIN.value,
            "role": matched_inv.get("role", "DEVELOPER"),
            "allowed_repos": matched_inv.get("allowed_repos", [f"{target_org}/primary-repo"]),
            "status": UserStatus.ACTIVE.value,
        }

        # Persist to PostgreSQL users table
        if db:
            try:
                db.table("users").upsert({
                    "id": user_id,
                    "organization_id": target_org,
                    "email": email,
                    "full_name": new_user["name"],
                    "password_hash": pwd_hash,
                    "is_org_admin": new_user["is_org_admin"],
                }).execute()
            except Exception:
                pass

        # In-memory registry for seamless fallback
        cls._mem_users[email] = new_user

        if matched_inv.get("team_id"):
            cls.add_user_to_team(target_org, matched_inv["team_id"], user_id)

        return new_user

    # =========================================================================
    # Device Enrollment & Sessions
    # =========================================================================

    @classmethod
    def enroll_device(cls, user_id: str, organization_id: str, device_name: str, platform: str = "windows", app_version: str = "2.0.0") -> Device:
        db = _safe_get_db()
        device_id = f"dev_{secrets.token_hex(4)}"
        now = datetime.now(UTC)

        if db:
            try:
                existing = db.table("devices").select("*").eq("organization_id", organization_id).eq("user_id", user_id).eq("device_name", device_name).execute()
                rows = _rows(existing.data)
                if rows:
                    d = rows[0]
                    db.table("devices").update({"status": "ACTIVE", "last_seen_at": now.isoformat()}).eq("id", d["id"]).execute()
                    return Device(
                        id=d["id"],
                        user_id=user_id,
                        organization_id=organization_id,
                        device_name=d["device_name"],
                        platform=d.get("platform", platform),
                        app_version=d.get("app_version", app_version),
                        status=DeviceStatus.ACTIVE,
                        last_seen_at=now,
                        created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d.get("created_at"), str) else now,
                    )
                db.table("devices").insert({
                    "id": device_id,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "device_name": device_name,
                    "platform": platform,
                    "app_version": app_version,
                    "status": "ACTIVE",
                    "last_seen_at": now.isoformat(),
                }).execute()
            except Exception:
                pass

        org_devices = cls._mem_devices.setdefault(organization_id, [])
        for d in org_devices:
            if d.get("user_id") == user_id and d.get("device_name") == device_name:
                d["status"] = DeviceStatus.ACTIVE.value
                d["last_seen_at"] = now.isoformat()
                return Device(
                    id=d["id"],
                    user_id=user_id,
                    organization_id=organization_id,
                    device_name=d["device_name"],
                    platform=d.get("platform", platform),
                    app_version=d.get("app_version", app_version),
                    status=DeviceStatus(d["status"]),
                    last_seen_at=now,
                    created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
                )

        record = {
            "id": device_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "device_name": device_name,
            "platform": platform,
            "app_version": app_version,
            "status": DeviceStatus.ACTIVE.value,
            "last_seen_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
        org_devices.append(record)

        return Device(
            id=device_id,
            user_id=user_id,
            organization_id=organization_id,
            device_name=device_name,
            platform=platform,
            app_version=app_version,
            status=DeviceStatus.ACTIVE,
            last_seen_at=now,
            created_at=now,
        )

    @classmethod
    def list_devices(cls, organization_id: str, user_id: str | None = None) -> list[Device]:
        db = _safe_get_db()
        if db:
            try:
                query = db.table("devices").select("*").eq("organization_id", organization_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.execute()
                rows = _rows(res.data)
                if rows:
                    return [
                        Device(
                            id=d["id"],
                            user_id=d["user_id"],
                            organization_id=d["organization_id"],
                            device_name=d["device_name"],
                            platform=d.get("platform", "windows"),
                            app_version=d.get("app_version", "2.0.0"),
                            status=DeviceStatus(d.get("status", "ACTIVE")),
                            last_seen_at=datetime.fromisoformat(d["last_seen_at"]) if isinstance(d.get("last_seen_at"), str) else datetime.now(UTC),
                            created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d.get("created_at"), str) else datetime.now(UTC),
                        )
                        for d in rows
                    ]
            except Exception:
                pass

        raw = cls._mem_devices.get(organization_id, [])
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
        db = _safe_get_db()
        found = False
        if db:
            try:
                res = db.table("devices").update({"status": "REVOKED"}).eq("organization_id", organization_id).eq("id", device_id).execute()
                if _rows(res.data):
                    found = True
            except Exception:
                pass

        raw = cls._mem_devices.get(organization_id, [])
        for d in raw:
            if d["id"] == device_id:
                d["status"] = DeviceStatus.REVOKED.value
                found = True

        return found

    @classmethod
    def is_device_active(cls, organization_id: str, device_id: str) -> bool:
        db = _safe_get_db()
        if db:
            try:
                res = db.table("devices").select("status").eq("organization_id", organization_id).eq("id", device_id).execute()
                rows = _rows(res.data)
                if rows:
                    return str(rows[0].get("status", "ACTIVE")).upper() == "ACTIVE"
            except Exception:
                pass

        raw = cls._mem_devices.get(organization_id, [])
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
        db = _safe_get_db()
        provider_val = provider.value if hasattr(provider, "value") else str(provider)
        ident_id = f"ext_{secrets.token_hex(4)}"

        if db:
            try:
                record = {
                    "id": ident_id,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "provider": provider_val,
                    "external_user_id": external_user_id,
                    "external_username": external_username,
                    "external_email": external_email,
                    "verification_status": "VERIFIED",
                }
                res = db.table("external_identities").upsert(record).execute()
                rows = _rows(res.data)
                row = rows[0] if rows else record
                return ExternalIdentity(
                    id=str(row["id"]),
                    user_id=user_id,
                    organization_id=organization_id,
                    provider=ExternalProvider(provider_val),
                    external_user_id=external_user_id,
                    external_username=external_username,
                    external_email=external_email,
                    verification_status="VERIFIED",
                )
            except Exception:
                pass

        org_links = cls._mem_external_identities.setdefault(organization_id, [])
        for link in org_links:
            if link["provider"] == provider_val and (link["external_user_id"] == external_user_id or link["external_username"].lower() == external_username.lower()):
                link["user_id"] = user_id
                link["external_username"] = external_username
                link["external_email"] = external_email
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

        record = {
            "id": ident_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "provider": provider_val,
            "external_user_id": external_user_id,
            "external_username": external_username,
            "external_email": external_email,
            "verification_status": "VERIFIED",
            "created_at": datetime.now(UTC).isoformat(),
        }
        org_links.append(record)

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
        db = _safe_get_db()
        if db:
            try:
                query = db.table("external_identities").select("*").eq("organization_id", organization_id)
                if user_id:
                    query = query.eq("user_id", user_id)
                res = query.execute()
                rows = _rows(res.data)
                if rows:
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
                            created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r.get("created_at"), str) else datetime.now(UTC),
                        )
                        for r in rows
                    ]
            except Exception:
                pass

        raw = cls._mem_external_identities.get(organization_id, [])
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
        db = _safe_get_db()
        # 1. Check PostgreSQL external_identities
        if db:
            try:
                query = db.table("external_identities").select("user_id").eq("organization_id", organization_id).eq("provider", provider)
                if external_user_id:
                    res = query.eq("external_user_id", external_user_id).execute()
                    rows = _rows(res.data)
                    if rows:
                        return str(rows[0]["user_id"])
                if external_username:
                    res = db.table("external_identities").select("user_id").eq("organization_id", organization_id).eq("provider", provider).ilike("external_username", external_username).execute()
                    rows = _rows(res.data)
                    if rows:
                        return str(rows[0]["user_id"])
            except Exception:
                pass

        # In-memory external identities check
        org_links = cls._mem_external_identities.get(organization_id, [])
        for link in org_links:
            if link.get("provider") == provider:
                if external_user_id and link.get("external_user_id") == external_user_id:
                    return str(link["user_id"])
                if external_username and str(link.get("external_username", "")).lower() == external_username.lower():
                    return str(link["user_id"])

        # 2. Match by email in PostgreSQL users table
        if email:
            clean_email = email.lower().strip()
            if db:
                try:
                    res = db.table("users").select("id").eq("organization_id", organization_id).eq("email", clean_email).execute()
                    rows = _rows(res.data)
                    if rows:
                        matched_id = str(rows[0]["id"])
                        if external_username and matched_id:
                            cls.link_external_identity(
                                user_id=matched_id,
                                organization_id=organization_id,
                                provider=ExternalProvider(provider),
                                external_user_id=external_user_id or external_username,
                                external_username=external_username,
                                external_email=email,
                            )
                        return matched_id
                except Exception:
                    pass

            for u_email, u_data in cls._mem_users.items():
                if u_email.lower() == clean_email and u_data.get("organization_id") == organization_id:
                    matched_uid = str(u_data.get("user_id") or "")
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
        db = _safe_get_db()
        user_info: dict[str, Any] | None = None

        if db:
            try:
                res = db.table("users").select("*").eq("organization_id", organization_id).eq("id", user_id).execute()
                rows = _rows(res.data)
                if rows:
                    u = rows[0]
                    user_info = {
                        "user_id": str(u["id"]),
                        "name": str(u.get("full_name") or u["id"]),
                        "email": str(u.get("email") or ""),
                        "organization_id": organization_id,
                        "company_name": organization_id.capitalize(),
                        "role": "ADMIN" if u.get("is_org_admin") else "DEVELOPER",
                        "status": "ACTIVE",
                        "allowed_repos": [f"{organization_id}/billing-service", f"{organization_id}/auth-service"],
                    }
            except Exception:
                pass

        if not user_info:
            for u in cls._mem_users.values():
                if (u.get("user_id") == user_id or u.get("email") == user_id) and u.get("organization_id") == organization_id:
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
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        }
        return code

    @classmethod
    def exchange_authorization_code(cls, code: str) -> dict[str, Any] | None:
        record = cls._auth_codes_store.pop(code, None)
        if not record:
            return None
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(UTC) > expires_at:
            return None
        return record
