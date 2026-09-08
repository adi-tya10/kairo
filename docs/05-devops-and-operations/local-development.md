# KAIRO: Local Development & Multi-Service Runbook

> **Domain:** DevOps & Infrastructure  
> **Document ID:** KAIRO-OPS-DEV  
> **Target:** Local Developer Environment, Docker Compose & Tunneling

---

## 1. Prerequisites

* **Python:** `3.11` / `3.12` with [`uv`](https://github.com/astral-sh/uv)
* **Node.js:** `20.x LTS` with [`pnpm`](https://pnpm.io/)
* **Docker & Docker Compose**
* **Tunneling Tool:** `ngrok` or `cloudflared`

---

## 2. Fast Local Execution

```bash
# 1. Start Docker multi-container environment
docker-compose up --build -d

# 2. Start local tunnel for external webhooks
ngrok http 8000
# Output: https://xyz.ngrok-free.app

# 3. Configure webhook URL in Jira / GitHub / Slack
# https://xyz.ngrok-free.app/api/v1/webhooks/{provider}
```
