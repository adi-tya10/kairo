"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ShieldCheck,
  Building2,
  Lock,
  Mail,
  Users,
  ArrowRight,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertOctagon,
  Eye,
  EyeOff,
  Check,
  Terminal,
  ChevronDown,
} from "lucide-react";
import { API_BASE } from "../api-config";

const TYPING_PHRASES = [
  "Resolving ground truth for active development work items...",
  "Evaluating deterministic anomaly rule HW-03 (State Mismatch)...",
  "Synthesizing 100% cited handover brief for incoming lead...",
  "Traversing Neo4j temporal decision lineage (:Task)-[:SUPERSEDES]->(:ADR)...",
  "Enforcing Pre-Retrieval ACL: 0 unauthorized vector leaks...",
  "Watching active Git repositories and indexing commit branches...",
];

const TEAM_SIZE_OPTIONS = [
  "5-20 Engineers",
  "20-50 Engineers",
  "50-200 Engineers",
  "200+ Enterprise Pods",
];

function AuthPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialInvite = searchParams.get("invite");
  const initialMode = initialInvite ? "invite" : searchParams.get("mode") === "register" ? "register" : "login";

  const [mode, setMode] = useState<"login" | "register" | "invite">(initialMode);
  const [inviteToken, setInviteToken] = useState(initialInvite || "");
  const [fullName, setFullName] = useState("");

  // Form Fields
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [teamSize, setTeamSize] = useState("20-50 Engineers");
  const [showPassword, setShowPassword] = useState(false);
  const [teamSizeDropdownOpen, setTeamSizeDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Status
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dynamic Typing Animation State for Right Panel
  const [currentPhraseIndex, setCurrentPhraseIndex] = useState(0);
  const [currentText, setCurrentText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState(45);

  useEffect(() => {
    const qInvite = searchParams.get("invite");
    const qMode = searchParams.get("mode");
    if (qInvite) {
      setMode("invite");
      setInviteToken(qInvite);
      setError(null);
    } else if (qMode === "register" || qMode === "login") {
      setMode(qMode);
      setError(null);
    }
  }, [searchParams]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setTeamSizeDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Typing Effect Loop
  useEffect(() => {
    const handleTyping = () => {
      const fullText = TYPING_PHRASES[currentPhraseIndex];

      if (!isDeleting) {
        setCurrentText(fullText.substring(0, currentText.length + 1));
        setTypingSpeed(45);

        if (currentText === fullText) {
          setTimeout(() => setIsDeleting(true), 2400);
        }
      } else {
        setCurrentText(fullText.substring(0, currentText.length - 1));
        setTypingSpeed(25);

        if (currentText === "") {
          setIsDeleting(false);
          setCurrentPhraseIndex((prev) => (prev + 1) % TYPING_PHRASES.length);
        }
      }
    };

    const timer = setTimeout(handleTyping, typingSpeed);
    return () => clearTimeout(timer);
  }, [currentText, isDeleting, currentPhraseIndex, typingSpeed]);

  // Password Strength Calculation
  const calculateStrength = (pwd: string) => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    return score;
  };

  const pwdStrength = calculateStrength(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === "invite") {
        const res = await fetch(`${API_BASE}/identity/invitations/accept`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            token: inviteToken,
            name: fullName.trim() || "Employee",
            password: password.trim(),
          }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Invalid or expired invitation token.");
        }

        const data = await res.json();
        localStorage.setItem("kairo_jwt_token", data.access_token);
        if (data.user?.organization_id) {
          localStorage.setItem("kairo_org_id", data.user.organization_id);
          router.push(`/download?onboarding=true&org=${encodeURIComponent(data.user.organization_id)}`);
        } else {
          router.push("/download?onboarding=true");
        }
      } else if (mode === "login") {
        const res = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password: password.trim() }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Invalid email or password. Please check your credentials.");
        }

        const data = await res.json();
        localStorage.setItem("kairo_jwt_token", data.access_token);
        if (data.user?.organization_id) {
          localStorage.setItem("kairo_org_id", data.user.organization_id);
        }
        router.push("/dashboard");
      } else {
        const res = await fetch(`${API_BASE}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name: companyName.trim() || "Organization",
            admin_email: email.trim(),
            password: password.trim(),
            plan_tier: "ENTERPRISE",
          }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Registration failed.");
        }

        const data = await res.json();
        localStorage.setItem("kairo_jwt_token", data.access_token);
        if (data.organization?.id) {
          localStorage.setItem("kairo_org_id", data.organization.id);
        }
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    setEmail("admin@snapmeet.com");
    setPassword("KairoEnterprise2026!");
  };

  return (
    <div className="min-h-screen bg-[#0A0D12] text-[#EDEDED] flex font-sans selection:bg-[#3ECF8E] selection:text-black">
      {/* ========================================================================= */}
      {/* LEFT COLUMN: AUTHENTICATION FORM (SUPABASE SPLIT STYLE)                    */}
      {/* ========================================================================= */}
      <div className="w-full lg:w-[50%] flex flex-col justify-between p-6 sm:p-12 lg:p-16 border-r border-[#1E232F] bg-[#0A0D12] relative z-10">
        {/* Top Navbar Brand */}
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <img src="/kairo.png" alt="KAIRO" className="w-7 h-7 object-contain group-hover:scale-105 transition-transform" />
            <div className="flex flex-col leading-none">
              <span className="font-bold tracking-tight text-white text-base">KAIRO</span>
              <span className="text-[9px] font-mono tracking-widest text-[#94A3B8] uppercase mt-0.5">enterprise</span>
            </div>
          </Link>

          <Link href="/" className="text-xs text-[#94A3B8] hover:text-white transition-colors">
            &larr; Back to home
          </Link>
        </div>

        {/* Center Main Form */}
        <div className="max-w-md w-full mx-auto space-y-6 py-8">
          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              {mode === "invite"
                ? "Accept Employee Invitation"
                : mode === "login"
                ? "Welcome back"
                : "Create your workspace"}
            </h1>
            <p className="text-xs text-[#94A3B8]">
              {mode === "invite"
                ? "Set your password to activate your enterprise account and unlock KAIRO Desktop HUD."
                : mode === "login"
                ? "Sign in to access real-time continuity maps & decision lineage."
                : "Deploy KAIRO work continuity engine across your engineering pods."}
            </p>
          </div>

          {/* Single Social Login: Continue with Google (only in login/register) */}
          {mode !== "invite" && (
            <>
              <button
                type="button"
                onClick={handleGoogleLogin}
                className="w-full py-2.5 px-4 rounded-lg bg-[#161B26] hover:bg-[#1E232F] border border-[#2B3242] hover:border-[#3ECF8E]/50 text-xs font-semibold text-white transition-all flex items-center justify-center gap-3 cursor-pointer shadow-sm"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>Continue with Google</span>
              </button>

              <div className="relative flex items-center justify-center">
                <div className="border-t border-[#1E232F] w-full" />
                <span className="bg-[#0A0D12] px-3 text-[11px] font-mono text-[#64748B] uppercase">or</span>
              </div>
            </>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-3.5 rounded-lg bg-red-950/50 border border-red-800/50 text-red-300 text-xs flex items-center gap-2.5">
              <AlertOctagon size={16} className="shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Main Credentials Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "invite" && (
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#CBD5E1]">
                  Your Full Name
                </label>
                <div className="relative">
                  <Users size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#11151F] border border-[#1E232F] focus:border-[#3ECF8E] focus:ring-1 focus:ring-[#3ECF8E] text-xs text-white placeholder-[#475569] outline-none transition-all"
                  />
                </div>
              </div>
            )}

            {mode === "register" && (
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#CBD5E1]">
                  Organization / Company Name
                </label>
                <div className="relative">
                  <Building2 size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Acme Technologies Inc."
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#11151F] border border-[#1E232F] focus:border-[#3ECF8E] focus:ring-1 focus:ring-[#3ECF8E] text-xs text-white placeholder-[#475569] outline-none transition-all"
                  />
                </div>
              </div>
            )}

            {mode !== "invite" && (
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-[#CBD5E1]">
                  Work Email Address
                </label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[#11151F] border border-[#1E232F] focus:border-[#3ECF8E] focus:ring-1 focus:ring-[#3ECF8E] text-xs text-white placeholder-[#475569] outline-none transition-all"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-[#CBD5E1]">
                  {mode === "invite" ? "Set New Password" : "Password"}
                </label>
                {mode === "login" && (
                  <button
                    type="button"
                    onClick={() => {
                      setEmail("admin@snapmeet.com");
                      setPassword("KairoEnterprise2026!");
                    }}
                    className="text-[11px] text-[#3ECF8E] hover:underline cursor-pointer"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748B]" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-10 py-2.5 rounded-lg bg-[#11151F] border border-[#1E232F] focus:border-[#3ECF8E] focus:ring-1 focus:ring-[#3ECF8E] text-xs text-white placeholder-[#475569] outline-none transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#64748B] hover:text-white cursor-pointer"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              {/* Password Strength Meter in Register Mode */}
              {mode === "register" && password && (
                <div className="space-y-1 pt-1">
                  <div className="grid grid-cols-4 gap-1.5">
                    {[1, 2, 3, 4].map((step) => (
                      <div
                        key={step}
                        className={`h-1 rounded-full transition-all ${
                          pwdStrength >= step
                            ? pwdStrength === 4
                              ? "bg-[#3ECF8E]"
                              : pwdStrength >= 2
                              ? "bg-amber-400"
                              : "bg-red-400"
                            : "bg-[#1E232F]"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-[10px] font-mono text-[#94A3B8]">
                    {pwdStrength === 4
                      ? "Strong enterprise password"
                      : "Include uppercase, number & symbol"}
                  </span>
                </div>
              )}
            </div>

            {/* Custom Stylish Dark Dropdown for Engineering Team Size */}
            {mode === "register" && (
              <div className="space-y-1.5" ref={dropdownRef}>
                <label className="block text-xs font-semibold text-[#CBD5E1]">
                  Engineering Team Size
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setTeamSizeDropdownOpen(!teamSizeDropdownOpen)}
                    className={`w-full px-3.5 py-2.5 rounded-lg bg-[#11151F] border text-xs text-white flex items-center justify-between transition-all cursor-pointer ${
                      teamSizeDropdownOpen
                        ? "border-[#3ECF8E] ring-1 ring-[#3ECF8E]"
                        : "border-[#1E232F] hover:border-[#2B3242]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Users size={14} className="text-[#3ECF8E]" />
                      <span>{teamSize}</span>
                    </div>
                    <ChevronDown
                      size={15}
                      className={`text-[#94A3B8] transition-transform duration-200 ${
                        teamSizeDropdownOpen ? "rotate-180 text-[#3ECF8E]" : ""
                      }`}
                    />
                  </button>

                  {/* Dropdown Menu Modal */}
                  {teamSizeDropdownOpen && (
                    <div className="absolute top-full left-0 right-0 mt-1.5 p-1.5 rounded-xl bg-[#11151F] border border-[#2B3242] shadow-2xl z-50 space-y-1 animate-in fade-in zoom-in-95 duration-100">
                      {TEAM_SIZE_OPTIONS.map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => {
                            setTeamSize(option);
                            setTeamSizeDropdownOpen(false);
                          }}
                          className={`w-full p-2.5 rounded-lg text-xs flex items-center justify-between text-left transition-colors cursor-pointer ${
                            teamSize === option
                              ? "bg-[#161B26] text-white font-bold border border-[#3ECF8E]/30"
                              : "text-[#94A3B8] hover:text-white hover:bg-white/[0.04]"
                          }`}
                        >
                          <span>{option}</span>
                          {teamSize === option && (
                            <Check size={14} className="text-[#3ECF8E]" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Primary Submit Button (Supabase Green #3ECF8E) */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-[#3ECF8E] hover:bg-[#34B27B] text-black font-bold text-xs transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md disabled:opacity-50 mt-2"
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Authenticating with Supabase...</span>
                </>
              ) : mode === "login" ? (
                <>
                  <span>Sign in</span>
                  <ArrowRight size={14} />
                </>
              ) : (
                <>
                  <span>Create Enterprise Workspace</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          {/* Toggle Sign in / Sign up */}
          <div className="text-center text-xs text-[#94A3B8] pt-2">
            {mode === "login" ? (
              <span>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => { setMode("register"); setError(null); }}
                  className="text-[#3ECF8E] hover:underline font-bold cursor-pointer"
                >
                  Sign up
                </button>
              </span>
            ) : (
              <span>
                Already have an organization account?{" "}
                <button
                  type="button"
                  onClick={() => { setMode("login"); setError(null); }}
                  className="text-[#3ECF8E] hover:underline font-bold cursor-pointer"
                >
                  Sign in
                </button>
              </span>
            )}
          </div>
        </div>

        {/* Footer Legal */}
        <p className="text-[11px] text-[#64748B] text-center max-w-sm mx-auto">
          By continuing, you agree to KAIRO&apos;s <a href="#" className="underline hover:text-[#94A3B8]">Terms of Service</a> and <a href="#" className="underline hover:text-[#94A3B8]">Privacy Policy</a>.
        </p>
      </div>

      {/* ========================================================================= */}
      {/* RIGHT COLUMN: MODERN MOVING / TYPING ENGINE VISUALIZER                    */}
      {/* ========================================================================= */}
      <div className="hidden lg:flex lg:w-[50%] bg-[#080B0F] relative overflow-hidden flex-col justify-between p-16 items-center">
        {/* Background Ambient Glow & Grid Lines */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] pointer-events-none" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-b from-[#3ECF8E]/10 via-[#3B82F6]/5 to-transparent blur-[140px] pointer-events-none" />

        {/* Top Floating Telemetry Header */}
        <div className="w-full flex items-center justify-between z-10 text-xs font-mono text-[#94A3B8]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#3ECF8E] animate-pulse" />
            <span>KAIRO_TEMPORAL_KERNEL :: V2.0</span>
          </div>
        </div>

        {/* Center: Glowing KAIRO Emblem & Live Typing Terminal */}
        <div className="max-w-md w-full space-y-8 z-10 my-auto text-center">
          {/* Glowing Emblem */}
          <div className="relative inline-block group">
            <div className="absolute -inset-4 bg-gradient-to-r from-[#3ECF8E]/20 via-[#3B82F6]/20 to-[#A855F7]/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-500" />
            <img src="/kairo.png" alt="KAIRO" className="w-20 h-20 object-contain relative mx-auto drop-shadow-2xl" />
          </div>

          <div className="space-y-3">
            <h2 className="text-2xl font-black tracking-tight text-white">
              Zero Context Loss During Developer Transitions
            </h2>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Reconstructing ground truth from CI/CD check runs, GitHub PR states, Git author SHAs, and Neo4j temporal decision lineage.
            </p>
          </div>

          {/* Live Typing Terminal Box */}
          <div className="p-5 rounded-2xl bg-[#0E1219] border border-[#1E232F] text-left font-mono text-xs space-y-3 shadow-2xl relative overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#1E232F] pb-3 text-[11px] text-[#64748B]">
              <div className="flex items-center gap-2">
                <Terminal size={14} className="text-[#3ECF8E]" />
                <span className="text-slate-300 font-bold">engine.telemetry.live</span>
              </div>
              <span className="text-[#3ECF8E] font-bold">STREAMING</span>
            </div>

            {/* Dynamic Typing Text Line */}
            <div className="min-h-[48px] flex items-start gap-2 text-slate-200">
              <span className="text-[#3ECF8E] font-bold">&gt;</span>
              <span className="text-white leading-relaxed">
                {currentText}
                <span className="inline-block w-2 h-4 bg-[#3ECF8E] ml-1 animate-pulse align-middle" />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#07090E] flex items-center justify-center text-slate-400 font-mono text-xs">Loading KAIRO Auth...</div>}>
      <AuthPageContent />
    </Suspense>
  );
}

