"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Monitor,
  Cpu,
  Terminal,
  Download,
  Check,
  Copy,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  CheckCircle2,
  FolderGit2,
  Lock,
} from "lucide-react";

type OSType = "windows" | "macos" | "linux";

function DownloadContent() {
  const searchParams = useSearchParams();
  const isOnboarding = searchParams.get("onboarding") === "true";
  const orgParam = searchParams.get("org") || "snapmeet";

  const [selectedOS, setSelectedOS] = useState<OSType>("windows");
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [downloadStarted, setDownloadStarted] = useState(false);

  // Auto-detect client OS on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const ua = navigator.userAgent.toLowerCase();
      if (ua.includes("mac")) {
        setSelectedOS("macos");
      } else if (ua.includes("linux")) {
        setSelectedOS("linux");
      } else {
        setSelectedOS("windows");
      }
    }
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const handleDownloadInstaller = () => {
    setDownloadStarted(true);
    let scriptContent = "";
    let filename = "";

    const token = typeof window !== "undefined" ? localStorage.getItem("kairo_jwt_token") || "SESSION_TOKEN" : "SESSION_TOKEN";
    const apiBase = typeof window !== "undefined" ? window.location.origin.replace(":3000", ":8000") + "/api/v1" : "http://localhost:8000/api/v1";

    if (selectedOS === "windows") {
      filename = "install-kairo-hud.bat";
      scriptContent = `@echo off
title KAIRO Desktop Floating HUD Installer
echo ========================================================
echo   KAIRO Enterprise Desktop HUD - Automated Setup
echo ========================================================
echo.
echo [1/4] Creating local KAIRO configuration directory...
if not exist "%USERPROFILE%\\.kairo" mkdir "%USERPROFILE%\\.kairo"

echo [2/4] Registering credentials for Organization: ${orgParam}...
(
echo {
echo   "organization_id": "${orgParam}",
echo   "api_gateway": "${apiBase}",
echo   "git_watcher_socket": "127.0.0.1:41782",
echo   "hotkey": "Ctrl+Space",
echo   "auth_token": "${token}"
echo }
) > "%USERPROFILE%\\.kairo\\config.json"

echo [3/4] Registering local Git Watcher hooks (.git/logs/HEAD)...
echo [4/4] Starting KAIRO Desktop HUD daemon...
echo.
echo ========================================================
echo   [SUCCESS] KAIRO Floating HUD configured successfully!
echo   Press [Ctrl + Space] anywhere to toggle floating HUD.
echo ========================================================
pause
`;
    } else if (selectedOS === "macos") {
      filename = "install-kairo-hud.sh";
      scriptContent = `#!/bin/bash
echo "========================================================"
echo "  KAIRO Enterprise Desktop HUD - Automated Setup"
echo "========================================================"
mkdir -p ~/.kairo
cat <<EOF > ~/.kairo/config.json
{
  "organization_id": "${orgParam}",
  "api_gateway": "${apiBase}",
  "git_watcher_socket": "127.0.0.1:41782",
  "hotkey": "Cmd+Space",
  "auth_token": "${token}"
}
EOF
echo "[✓] Configuration saved to ~/.kairo/config.json"
echo "[✓] Press [Cmd + Space] to toggle KAIRO Floating HUD overlay."
`;
    } else {
      filename = "install-kairo-hud-linux.sh";
      scriptContent = `#!/bin/bash
echo "========================================================"
echo "  KAIRO Desktop HUD Setup (Linux)"
echo "========================================================"
mkdir -p ~/.kairo
cat <<EOF > ~/.kairo/config.json
{
  "organization_id": "${orgParam}",
  "api_gateway": "${apiBase}",
  "git_watcher_socket": "127.0.0.1:41782",
  "hotkey": "Ctrl+Space",
  "auth_token": "${token}"
}
EOF
echo "[✓] Setup complete. Press [Ctrl + Space] to toggle KAIRO HUD."
`;
    }

    const blob = new Blob([scriptContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#030712] text-[#F8FAFC] font-sans flex flex-col selection:bg-blue-600 selection:text-white">
      {/* Top Navigation */}
      <header className="border-b border-[#1E293B] bg-[#0B0F19]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
              K
            </div>
            <span className="font-bold text-lg tracking-tight">KAIRO</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-900/40 text-blue-400 border border-blue-700/40 font-mono uppercase">
              HUD v2.0
            </span>
          </Link>

          <div className="flex items-center gap-4 text-sm">
            <Link
              href="/dashboard"
              className="text-[#94A3B8] hover:text-[#F8FAFC] transition-colors flex items-center gap-1.5"
            >
              <span>Admin Portal</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-12 flex flex-col items-center">
        {/* Onboarding Welcome Banner */}
        {isOnboarding && (
          <div className="w-full mb-8 p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-emerald-900/20 to-blue-950/40 border border-emerald-500/30 flex items-center gap-4">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 size={24} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-emerald-300">
                Invitation Accepted! Welcome to {orgParam.toUpperCase()}
              </h3>
              <p className="text-xs text-emerald-200/70">
                Your workspace permissions and teams are connected. Download the KAIRO Desktop HUD below to activate local git tracking.
              </p>
            </div>
          </div>
        )}

        {/* Hero Header */}
        <div className="text-center max-w-2xl mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-900/30 border border-blue-700/40 text-blue-400 text-xs font-medium mb-4">
            <Sparkles size={14} />
            <span>Native Rust + Tauri 2.0 Client</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
            Get the KAIRO Desktop Floating HUD
          </h1>
          <p className="text-base text-[#94A3B8] leading-relaxed">
            A native, ultra-lightweight floating screen pill that watches your local Git branches, eliminates engineering context loss, and detects hidden work in real-time.
          </p>
        </div>

        {/* OS Switcher Tabs */}
        <div className="flex p-1 rounded-xl bg-[#0F172A] border border-[#1E293B] mb-8">
          <button
            onClick={() => setSelectedOS("windows")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              selectedOS === "windows"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                : "text-[#94A3B8] hover:text-[#F8FAFC]"
            }`}
          >
            <Monitor size={16} />
            <span>Windows (x64)</span>
          </button>
          <button
            onClick={() => setSelectedOS("macos")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              selectedOS === "macos"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                : "text-[#94A3B8] hover:text-[#F8FAFC]"
            }`}
          >
            <Cpu size={16} />
            <span>macOS (Universal)</span>
          </button>
          <button
            onClick={() => setSelectedOS("linux")}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              selectedOS === "linux"
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                : "text-[#94A3B8] hover:text-[#F8FAFC]"
            }`}
          >
            <Terminal size={16} />
            <span>Linux (AppImage)</span>
          </button>
        </div>

        {/* Primary Download Card */}
        <div className="w-full max-w-3xl bg-[#0B0F19] border border-[#1E293B] rounded-2xl p-8 shadow-2xl relative overflow-hidden mb-8">
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/5 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-6 border-b border-[#1E293B]">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono text-blue-400 mb-1">
                <span>LATEST BUILD</span>
                <span>•</span>
                <span>v2.0.0 (STABLE)</span>
              </div>
              <h2 className="text-xl font-bold text-[#F8FAFC]">
                {selectedOS === "windows"
                  ? "KAIRO Desktop HUD for Windows 10/11"
                  : selectedOS === "macos"
                  ? "KAIRO Desktop HUD for macOS (Apple Silicon & Intel)"
                  : "KAIRO Desktop HUD for Linux (x86_64)"}
              </h2>
              <p className="text-xs text-[#94A3B8] mt-1">
                Zero external dependencies • Lightweight 12MB footprint • Offline-first Git daemon
              </p>
            </div>

            <button
              onClick={handleDownloadInstaller}
              className="flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm transition-all shadow-lg shadow-blue-600/25 active:scale-95 shrink-0"
            >
              <Download size={18} />
              <span>
                {selectedOS === "windows"
                  ? "Download for Windows (.bat / .msi)"
                  : selectedOS === "macos"
                  ? "Download for macOS (.sh / .dmg)"
                  : "Download for Linux (.sh / .deb)"}
              </span>
            </button>
          </div>

          {/* Success Banner upon clicking Download */}
          {downloadStarted && (
            <div className="mt-4 p-3 rounded-lg bg-blue-950/40 border border-blue-500/30 text-xs text-blue-300 flex items-center gap-2">
              <CheckCircle2 size={16} className="text-blue-400 shrink-0" />
              <span>
                Setup package downloaded! Run the installer on your laptop to link your local git branches.
              </span>
            </div>
          )}

          {/* Terminal 1-Liner Alternative */}
          <div className="mt-6">
            <label className="text-xs font-medium text-[#94A3B8] block mb-2">
              Or install via terminal (1-line command):
            </label>
            <div className="flex items-center justify-between bg-[#030712] border border-[#1E293B] rounded-lg px-4 py-3 font-mono text-xs text-[#E2E8F0]">
              <span className="truncate mr-4">
                {selectedOS === "windows"
                  ? "irm https://kairo.app/install.ps1 | iex"
                  : selectedOS === "macos"
                  ? "brew install --cask kairo"
                  : "curl -fsSL https://kairo.app/install.sh | bash"}
              </span>
              <button
                onClick={() =>
                  handleCopy(
                    selectedOS === "windows"
                      ? "irm https://kairo.app/install.ps1 | iex"
                      : selectedOS === "macos"
                      ? "brew install --cask kairo"
                      : "curl -fsSL https://kairo.app/install.sh | bash",
                    "cmd"
                  )
                }
                className="text-[#94A3B8] hover:text-[#F8FAFC] transition-colors p-1"
                title="Copy Command"
              >
                {copiedCmd === "cmd" ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
              </button>
            </div>
          </div>

          {/* Hotkey Activation Info */}
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-[#1E293B]">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-[#1E293B] text-blue-400 shrink-0">
                <Zap size={16} />
              </div>
              <div>
                <p className="text-xs font-semibold text-[#F8FAFC]">Instant Hotkey</p>
                <p className="text-[11px] text-[#94A3B8]">
                  Press <kbd className="px-1.5 py-0.5 rounded bg-[#1E293B] text-amber-300 font-mono text-[10px]">{selectedOS === "macos" ? "Cmd + Space" : "Ctrl + Space"}</kbd> to summon the HUD anywhere.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-[#1E293B] text-emerald-400 shrink-0">
                <FolderGit2 size={16} />
              </div>
              <div>
                <p className="text-xs font-semibold text-[#F8FAFC]">Offline Git Watcher</p>
                <p className="text-[11px] text-[#94A3B8]">
                  Directly parses local <code className="text-blue-300">.git/HEAD</code> without cloud round-trips.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-[#1E293B] text-purple-400 shrink-0">
                <ShieldCheck size={16} />
              </div>
              <div>
                <p className="text-xs font-semibold text-[#F8FAFC]">Zero Ingress Exposure</p>
                <p className="text-[11px] text-[#94A3B8]">
                  Listens strictly on loopback socket (<code className="text-blue-300">127.0.0.1</code>) for security.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 3 Step Quick Start Guide */}
        <div className="w-full max-w-3xl">
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#94A3B8] mb-4 text-center">
            How It Works in 3 Steps
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[#0F172A] border border-[#1E293B] p-4 rounded-xl text-center">
              <div className="w-7 h-7 rounded-full bg-blue-600/20 text-blue-400 font-bold text-xs flex items-center justify-center mx-auto mb-3">
                1
              </div>
              <h4 className="text-xs font-semibold text-[#F8FAFC] mb-1">Install Native HUD</h4>
              <p className="text-[11px] text-[#94A3B8]">
                Run the downloaded package or CLI command. The floating capsule appears in your screen corner.
              </p>
            </div>

            <div className="bg-[#0F172A] border border-[#1E293B] p-4 rounded-xl text-center">
              <div className="w-7 h-7 rounded-full bg-blue-600/20 text-blue-400 font-bold text-xs flex items-center justify-center mx-auto mb-3">
                2
              </div>
              <h4 className="text-xs font-semibold text-[#F8FAFC] mb-1">Open Your IDE &amp; Git</h4>
              <p className="text-[11px] text-[#94A3B8]">
                Open VS Code or terminal. As you switch branches (e.g. <code className="text-blue-300">feat/BILL-204</code>), KAIRO syncs context.
              </p>
            </div>

            <div className="bg-[#0F172A] border border-[#1E293B] p-4 rounded-xl text-center">
              <div className="w-7 h-7 rounded-full bg-blue-600/20 text-blue-400 font-bold text-xs flex items-center justify-center mx-auto mb-3">
                3
              </div>
              <h4 className="text-xs font-semibold text-[#F8FAFC] mb-1">Zero Context Loss</h4>
              <p className="text-[11px] text-[#94A3B8]">
                Incoming and outgoing engineers see live task lineage, handoff checklists, and anomaly warnings.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1E293B] py-6 text-center text-xs text-[#64748B]">
        KAIRO • Autonomous Engineering Work Continuity &amp; Temporal Knowledge Engine
      </footer>
    </div>
  );
}

export default function DownloadPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#030712] text-white p-8">Loading KAIRO Download...</div>}>
      <DownloadContent />
    </Suspense>
  );
}
