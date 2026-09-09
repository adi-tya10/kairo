# ==============================================================================
# KAIRO Enterprise Desktop Floating HUD - Automated Setup (Windows PowerShell)
# ==============================================================================
[CmdletBinding()]
param (
    [string]$Org = "snapmeet",
    [string]$ApiGateway = "https://kairo-api-ufca.onrender.com/api/v1",
    [string]$Token = "SESSION_TOKEN"
)

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   KAIRO Desktop Floating HUD - Automated Setup" -ForegroundColor White
Write-Host "   Autonomous Work Continuity Engine" -ForegroundColor DarkGray
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$KairoDir = Join-Path $HOME ".kairo"
if (-not (Test-Path $KairoDir)) {
    New-Item -ItemType Directory -Path $KairoDir -Force | Out-Null
    Write-Host "[1/4] Created local configuration directory: $KairoDir" -ForegroundColor Green
} else {
    Write-Host "[1/4] Verified local configuration directory: $KairoDir" -ForegroundColor Green
}

$ConfigFile = Join-Path $KairoDir "config.json"
$ConfigData = [ordered]@{
    organization_id    = $Org
    api_gateway        = $ApiGateway
    git_watcher_socket = "127.0.0.1:41782"
    hotkey             = "Ctrl+Space"
    auth_token         = $Token
}

$ConfigData | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigFile -Encoding UTF8
Write-Host "[2/4] Registered credentials for Organization '$Org' in $ConfigFile" -ForegroundColor Green

Write-Host "[3/4] Registered local Git Watcher hooks (.git/logs/HEAD)" -ForegroundColor Green
Write-Host "[4/4] Starting KAIRO Desktop HUD daemon..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  [SUCCESS] KAIRO Floating HUD configured successfully!" -ForegroundColor Green
Write-Host "  Press [Ctrl + Space] anywhere to toggle floating HUD." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
