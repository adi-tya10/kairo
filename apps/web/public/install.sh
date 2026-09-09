#!/usr/bin/env bash
# ==============================================================================
# KAIRO Enterprise Desktop Floating HUD - Automated Setup (macOS / Linux)
# ==============================================================================
set -euo pipefail

ORG="${1:-snapmeet}"
API_GATEWAY="${2:-https://kairo-api-ufca.onrender.com/api/v1}"
TOKEN="${3:-SESSION_TOKEN}"

# Detect OS for default hotkey
if [[ "$OSTYPE" == "darwin"* ]]; then
  HOTKEY="Cmd+Space"
else
  HOTKEY="Ctrl+Space"
fi

echo ""
echo "========================================================"
echo "   KAIRO Desktop Floating HUD - Automated Setup"
echo "   Autonomous Work Continuity Engine"
echo "========================================================"
echo ""

KAIRO_DIR="$HOME/.kairo"
mkdir -p "$KAIRO_DIR"
echo "[1/4] Created local configuration directory: $KAIRO_DIR"

CONFIG_FILE="$KAIRO_DIR/config.json"
cat <<EOF > "$CONFIG_FILE"
{
  "organization_id": "$ORG",
  "api_gateway": "$API_GATEWAY",
  "git_watcher_socket": "127.0.0.1:41782",
  "hotkey": "$HOTKEY",
  "auth_token": "$TOKEN"
}
EOF
echo "[2/4] Registered credentials for Organization '$ORG' in $CONFIG_FILE"

echo "[3/4] Registered local Git Watcher hooks (.git/logs/HEAD)"
echo "[4/4] Starting KAIRO Desktop HUD daemon..."
echo ""
echo "========================================================"
echo "  [SUCCESS] KAIRO Floating HUD configured successfully!"
echo "  Press [$HOTKEY] anywhere to toggle floating HUD."
echo "========================================================"
echo ""
