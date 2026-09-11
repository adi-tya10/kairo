# KAIRO Desktop HUD (Tauri 2.0 / React)

Native floating developer HUD providing real-time work continuity context, git branch tracking, active handoffs, and anomaly alerts directly on the developer's screen.

## Build-Time API Configuration

By default, production builds connect to the deployed cloud API gateway:
```
https://kairo-web-91or.onrender.com/api/v1
```

### Overriding the Target API Gateway
To point the Desktop HUD to a custom or local development backend at build time, specify `VITE_KAIRO_API_URL`:

```bash
# Build pointing to local development backend
VITE_KAIRO_API_URL="http://localhost:8000/api/v1" pnpm build

# Build pointing to custom enterprise gateway
VITE_KAIRO_API_URL="https://api.your-company.com/api/v1" pnpm build
```

Or configure `.env.production` / `.env.development` within `apps/desktop/`.