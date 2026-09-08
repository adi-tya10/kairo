# KAIRO: API Error Handling & Problem Details Standard

> **Domain:** API & Developer Contracts  
> **Document ID:** KAIRO-API-ERRORS  
> **Standard:** RFC 7807 Problem Details for HTTP APIs

---

## 1. Standard RFC 7807 Error Envelope

All API errors return consistent JSON Problem Details formatted by `app.core.errors.kairo_exception_handler`:

```json
{
  "type": "https://api.kairo.dev/errors/access_restricted",
  "title": "ACCESS_RESTRICTED",
  "status": 403,
  "detail": "Access Restricted: User 'usr_aman' does not have permission for repo 'snapmeet/auth-service'",
  "instance": "http://localhost:8000/api/v1/context/work-items/AUTH-101?repo_id=snapmeet/auth-service",
  "details": {
    "user_id": "usr_aman",
    "attempted_repo": "snapmeet/auth-service"
  }
}
```

---

## 2. Typed Domain Exceptions (`app.core.errors`)

| Python Exception Class | Error Code Identifier | HTTP Status | Description |
| :--- | :--- | :--- | :--- |
| `TenantIsolationError` | `TENANT_ISOLATION_VIOLATION` | `403 Forbidden` | Caller organization does not match requested tenant boundary. |
| `AccessRestrictedError` | `ACCESS_RESTRICTED` | `403 Forbidden` | User permission profile does not contain requested repository in `allowed_repo_ids`. |
| `SignatureVerificationError` | `INVALID_SIGNATURE` | `401 Unauthorized` | Incoming webhook HMAC SHA-256 signature does not match secret. |
| `KairoError` | `INTERNAL_ERROR` | `500 Internal Server Error` | Unhandled runtime exception. |

---

## 3. Standard HTTP Error Codes

| HTTP Status | Error Type Identifier | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `https://api.kairo.dev/errors/validation_error` | Request schema violation (Pydantic validation). |
| `401 Unauthorized` | `https://api.kairo.dev/errors/authentication_required` | Missing or invalid Bearer JWT or webhook signature failure. |
| `403 Forbidden` | `https://api.kairo.dev/errors/access_restricted` | Pre-Retrieval ACL gate blocked repository or tenant access. |
| `404 Not Found` | `https://api.kairo.dev/errors/resource_not_found` | Requested task key, handoff event, or project ID not found. |
| `500 Internal Server Error` | `https://api.kairo.dev/errors/internal_error` | Unhandled exception caught by RFC 7807 handler. |
