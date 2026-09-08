# KAIRO: GitHub App Integration & Webhooks Guide

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-GITHUB  
> **Target:** GitHub App Ingress, HMAC Verification & Event Parsing

---

## 1. GitHub App Configuration

1. In GitHub, go to **Settings** $\rightarrow$ **Developer Settings** $\rightarrow$ **GitHub Apps** $\rightarrow$ **New GitHub App**.
2. **Settings:**
   * **Name:** `Kairo-Work-Continuity-Engine`
   * **Webhook URL (Global):** `https://<your-domain>/api/v1/webhooks/github`
   * **Webhook URL (Tenant Scoped):** `https://<your-domain>/api/v1/webhooks/github/{organization_id}`
   * **Webhook Secret:** High-entropy string (`openssl rand -hex 20`) configured as `GITHUB_WEBHOOK_SECRET`.
3. **Repository Permissions (Least-Privilege):**
   * **Contents:** Read-only (commits and file trees)
   * **Pull Requests:** Read-only (diffs, descriptions, comments)
   * **Issues:** Read-only (labels and references)
   * **Commit Statuses / Checks:** Read-only (CI build results)
   * **Members:** Read-only (team membership and offboarding tracking)
4. **Subscribed Events:**
   * `pull_request`, `push`, `issues`, `pull_request_review`, `check_run`, `membership`, `repository`.
5. Install the App onto target repositories.

---

## 2. Ingress Cryptographic Verification & Repository Auto-Discovery

```python
import hmac
import hashlib

def verify_github_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

### Auto-Discovery of Tenant Repositories
Incoming webhooks automatically link discovered repository names (e.g. `snapmeet/billing-service`) into the tenant's real-time service registry in `apps/api/app/api/v1/team.py:TENANT_SERVICES_STORE`, making new repositories instantly visible in the admin portal dashboard.
