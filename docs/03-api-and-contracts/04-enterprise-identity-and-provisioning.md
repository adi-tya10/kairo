# KAIRO Enterprise Identity, Team Hierarchy & Device Provisioning

## 1. Overview
KAIRO implements a **Canonical Identity Model** (`1 Human = 1 Canonical User`) bridging multi-tenant organizations, hierarchical teams, hardware desktop HUD devices, and external software tool accounts (GitHub, Jira, Linear, GitLab, Slack).

```
┌────────────────────────────────────────────────────────┐
│                   ORGANIZATION                         │
│             (e.g., SnapMeet Inc.)                      │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      ┌─────────────┐             ┌─────────────┐
      │  Core Team  │             │  Infra Pod  │
      └──────┬──────┘             └──────┬──────┘
             │                           │
             ▼                           ▼
      ┌─────────────┐             ┌─────────────┐
      │ Rahul Sharma│             │ Aman Verma  │
      └──────┬──────┘             └──────┬──────┘
             │                           │
     ┌───────┴───────────────┐           │
     ▼                       ▼           ▼
┌──────────────┐    ┌─────────────────┐ ┌──────────────┐
│Enrolled HUD  │    │External Handles │ │Enrolled HUD  │
│(Laptop DevID)│    │- gh: rahul-dev  │ │(MacBook DevID│
└──────────────┘    │- jira: 7120:38  │ └──────────────┘
                    └─────────────────┘
```

---

## 2. Relational Schema (`db/migrations/002_enterprise_identity.sql`)
1. **`teams`**: `(id, organization_id, name, description, created_at, updated_at)`
2. **`team_members`**: `(team_id, user_id, created_at)`
3. **`invitations`**: `(id, organization_id, email, name, team_id, role, allowed_repos, token_hash, status, expires_at)`
4. **`devices`**: `(id, user_id, organization_id, device_name, platform, app_version, status, last_seen_at)`
5. **`external_identities`**: `(id, user_id, organization_id, provider, external_user_id, external_username, external_email, verification_status)`

---

## 3. REST API Contract

### Context Retrieval
* `GET /api/v1/me/context` (or `/api/v1/identity/me`)
  - Authenticated endpoint returning user profile, company, assigned teams, allowed repositories, enrolled hardware devices, and linked tool identities.

### Teams Management
* `POST /api/v1/identity/teams`: Create a team pod in the organization.
* `GET /api/v1/identity/teams`: List all teams and member counts.
* `POST /api/v1/identity/teams/{team_id}/members`: Assign an employee to a team.

### Employee Invitations
* `POST /api/v1/identity/invitations`: Send single-use time-bounded invite token.
* `GET /api/v1/identity/invitations`: List pending invitations.
* `POST /api/v1/identity/invitations/accept`: Redeem token, set password, create canonical user.

### Device Enrollment & Revocation
* `POST /api/v1/identity/devices/enroll`: Desktop HUD registers local machine.
* `GET /api/v1/identity/devices`: List all registered devices.
* `POST /api/v1/identity/devices/{id}/revoke`: 1-Click revoke to terminate stolen/offboarded sessions.

### Cross-Tool Identity Linking & Resolution
* `POST /api/v1/identity/links`: Bind GitHub/Jira/Linear handle to canonical `user_id`.
* `GET /api/v1/identity/links`: View all verified external handle mappings.
* `IdentityResolver.resolve_canonical_user_id(org_id, provider, external_id, username, email)`: Webhook ingress resolution with strong signal ranking (Explicit Link $\to$ Verified Work Email).
