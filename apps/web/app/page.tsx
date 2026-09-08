"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Github,
  Download,
  Users,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Building2,
  Lock,
  Mail,
  LogOut,
  RefreshCw,
  Radio,
  ExternalLink,
  ChevronRight,
  GitPullRequest,
  GitCommit,
  Layers,
  ArrowUpRight,
  Shield,
  Zap,
  Check,
  Terminal,
  Activity,
  Network,
  Cpu,
  FileText,
  Workflow,
  Eye,
  Sliders,
  ChevronDown,
  Clock,
  Database,
  BarChart3,
  PlayCircle,
  GitBranch,
  Fingerprint,
  FileCode,
  Flame,
  ArrowDownRight,
  TrendingUp,
  Search,
  Code2,
  Send,
  CheckCheck,
  Binary,
  Compass,
  Copy,
  Box,
  Server,
  FolderGit2,
  HardDrive,
  MessageSquare,
  Globe,
  Share2,
  Key,
} from "lucide-react";
import { API_BASE } from "./api-config";

export default function LandingPage() {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string | null>(null);

  // Studio Interactive Explorer Tab State
  const [activeStudioTab, setActiveStudioTab] = useState<"continuity" | "anomalies" | "lineage" | "hud">("continuity");

  // Knowledge Graph Studio Interactive State
  const [graphZoom, setGraphZoom] = useState(1.0);
  const [selectedGraphNode, setSelectedGraphNode] = useState<string>("BILL-204");

  // Anomaly Rules Interactive State
  const [activeRule, setActiveRule] = useState<"HW-01" | "HW-02" | "HW-03" | "HW-04" | "HW-05">("HW-03");

  // CLI Copied State
  const [copiedCli, setCopiedCli] = useState(false);

  // Accordion FAQ State
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("kairo_jwt_token");
    if (token) {
      setAuthToken(token);
      try {
        fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
          .then((r) => r.json())
          .then((data) => {
            if (data.company_name) setCompanyName(data.company_name);
          })
          .catch(() => {});
      } catch {}
    }
  }, []);

  const handleCopyCli = () => {
    navigator.clipboard.writeText("npx kairo@latest init");
    setCopiedCli(true);
    setTimeout(() => setCopiedCli(false), 2000);
  };

  const toggleFaq = (index: number) => {
    setOpenFaq(openFaq === index ? null : index);
  };

  return (
    <div className="min-h-screen bg-[#0A0D12] text-[#EDEDED] flex flex-col font-sans selection:bg-[#3ECF8E] selection:text-black antialiased">
      {/* Background Subtle Gradient & Micro Grid */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:4rem_4rem]" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1100px] h-[500px] bg-gradient-to-b from-[#3ECF8E]/8 via-[#3B82F6]/5 to-transparent blur-[160px] pointer-events-none" />
      </div>

      {/* ========================================================================= */}
      {/* 1. TOP NAVBAR (SUPABASE-STYLE CLEAN MINIMALIST)                            */}
      {/* ========================================================================= */}
      <header className="border-b border-[#1E232F] bg-[#0A0D12]/90 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-10">
          <Link href="/" className="flex items-center gap-2.5 group">
            <img src="/kairo.png" alt="KAIRO" className="w-7 h-7 object-contain group-hover:scale-105 transition-transform" />
            <div className="flex flex-col leading-none">
              <span className="font-bold tracking-tight text-white text-base">KAIRO</span>
              <span className="text-[9px] font-mono tracking-widest text-[#94A3B8] uppercase mt-0.5">enterprise</span>
            </div>
          </Link>

          <nav className="hidden lg:flex items-center gap-6 text-[13px] font-medium text-[#94A3B8]">
            <a href="#product" className="hover:text-white transition-colors">Product</a>
            <a href="#anomalies" className="hover:text-white transition-colors">Anomaly Engine</a>
            <a href="#studio" className="hover:text-white transition-colors">Manager Studio</a>
            <a href="#templates" className="hover:text-white transition-colors">Templates</a>
            <a href="#cli" className="hover:text-white transition-colors">Developers</a>
            <a href="#security" className="hover:text-white transition-colors">Security & ACL</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          {authToken ? (
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#3ECF8E] hover:bg-[#34B27B] text-black text-xs font-bold transition-all shadow-sm"
            >
              <span>Launch Studio ({companyName || "Workspace"})</span>
              <ArrowRight size={13} />
            </Link>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                href="/auth?mode=login"
                className="text-xs font-semibold text-[#CBD5E1] hover:text-white px-3 py-1.5 rounded-lg hover:bg-white/[0.04] transition-all"
              >
                Sign in
              </Link>
              <Link
                href="/auth?mode=register"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#3ECF8E] hover:bg-[#34B27B] text-black text-xs font-bold transition-all shadow-sm"
              >
                <span>Start your project</span>
              </Link>
            </div>
          )}
        </div>
      </header>

      {/* ========================================================================= */}
      {/* SECTION 1: HERO (SPLIT GRID SUPABASE STYLE)                               */}
      {/* ========================================================================= */}
      <section className="relative z-10 pt-24 pb-16 px-6 max-w-7xl mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Monumental Headline & CTAs */}
          <div className="lg:col-span-7 space-y-7">
            <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-[1.08]">
              Build in a transition <br />
              <span className="text-[#3ECF8E]">Scale to millions</span>
            </h1>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Link
                href="/auth?mode=register"
                className="px-6 py-3 rounded-lg bg-[#3ECF8E] hover:bg-[#34B27B] text-black font-bold text-xs shadow-md transition-all flex items-center gap-2"
              >
                <span>Start your project</span>
                <ArrowRight size={14} />
              </Link>
              <Link
                href="/auth?mode=login"
                className="px-6 py-3 rounded-lg bg-[#161B26] hover:bg-[#1E232F] text-[#CBD5E1] hover:text-white font-semibold text-xs border border-[#2B3242] transition-all flex items-center gap-2"
              >
                <span>Request a demo</span>
              </Link>
            </div>
          </div>

          {/* Right Column: Hero Description */}
          <div className="lg:col-span-5 space-y-4">
            <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed font-normal">
              Start your handovers with a verified temporal graph. Add Deterministic Anomaly Evaluation (<span className="text-white font-mono font-medium">HW-01..HW-05</span>), Pre-Retrieval ACLs, Multi-Tenant GitHub Webhook Ingress, and Grounded Vector Embeddings.
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 2: THE ICONIC BENTO GRID - PART 1 (3 HERO CARDS WITH WIREFRAMES)   */}
      {/* ========================================================================= */}
      <section id="product" className="relative z-10 py-10 px-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: 4-Tier Postgres Ground Truth */}
          <div className="p-7 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-6 flex flex-col justify-between group relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-center gap-2.5 text-[#3ECF8E]">
                <Database size={18} />
                <h3 className="font-bold text-sm text-white">Postgres Truth Database</h3>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Every organization is backed by a <strong className="text-white">full PostgreSQL schema</strong> with <code className="text-[#3ECF8E]">pgvector</code> for grounded evidence retrieval.
              </p>
            </div>

            {/* Wireframe Graphic (Postgres Elephant Silhouette & Layer Stack) */}
            <div className="p-4 rounded-xl bg-[#090C10] border border-[#1B202A] font-mono text-[11px] space-y-2 text-[#94A3B8] relative">
              <div className="flex items-center justify-between text-white border-b border-white/[0.06] pb-1.5">
                <span className="flex items-center gap-1.5 text-xs"><Layers size={13} className="text-[#3ECF8E]" /> Tier 1: CI Check Run</span>
                <span className="text-[#3ECF8E] font-bold">100% TRUTH</span>
              </div>
              <div className="flex items-center justify-between text-slate-300 border-b border-white/[0.06] pb-1.5">
                <span className="flex items-center gap-1.5 text-xs"><GitPullRequest size={13} className="text-[#3B82F6]" /> Tier 2: GitHub PR State</span>
                <span className="text-[#3B82F6]">DELTA</span>
              </div>
              <div className="flex items-center justify-between text-slate-400 border-b border-white/[0.06] pb-1.5">
                <span className="flex items-center gap-1.5 text-xs"><GitCommit size={13} className="text-[#A855F7]" /> Tier 3: Git Commits</span>
                <span className="text-[#A855F7]">SHAs</span>
              </div>
              <div className="flex items-center justify-between text-[#64748B]">
                <span className="flex items-center gap-1.5 text-xs"><FileText size={13} /> Tier 4: Jira Declared</span>
                <span>LOWEST</span>
              </div>
            </div>

            <ul className="space-y-2 text-xs text-[#CBD5E1] pt-3 border-t border-[#1B202A]">
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>100% portable relational storage</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Built-in Auth with Row-Level Security</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Easy to extend with custom anomaly rules</span>
              </li>
            </ul>
          </div>

          {/* Card 2: Authentication & Multi-Tenant User Management */}
          <div className="p-7 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-6 flex flex-col justify-between group relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-center gap-2.5 text-[#3ECF8E]">
                <Lock size={18} />
                <h3 className="font-bold text-sm text-white">Authentication & Roles</h3>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Add user sign ups and logins, securing your repository work items and transition briefs with <strong className="text-white">Row Level Security</strong>.
              </p>
            </div>

            {/* Wireframe Graphic (Realistic User Management Rows) */}
            <div className="p-3 rounded-xl bg-[#090C10] border border-[#1B202A] font-mono text-[10px] space-y-2 text-[#94A3B8]">
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#141822] border border-[#1F2533]">
                <span className="text-white font-medium">rahul@snapmeet.com</span>
                <span className="text-amber-400 font-bold">OFFBOARDING</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#141822] border border-[#1F2533]">
                <span className="text-white font-medium">aman@snapmeet.com</span>
                <span className="text-[#3ECF8E] font-bold">ACTIVE LEAD</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#141822] border border-[#1F2533]">
                <span className="text-white font-medium">alice@snapmeet.com</span>
                <span className="text-blue-400 font-bold">MAINTAINER</span>
              </div>
            </div>

            <ul className="space-y-2 text-xs text-[#CBD5E1] pt-3 border-t border-[#1B202A]">
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Salted PBKDF2 & JWT tokens</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Fine-grained repository ACL guards</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Zero cross-tenant data leakage</span>
              </li>
            </ul>
          </div>

          {/* Card 3: Native Desktop HUD & Git Daemon */}
          <div className="p-7 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-6 flex flex-col justify-between group relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-center gap-2.5 text-[#3ECF8E]">
                <Cpu size={18} />
                <h3 className="font-bold text-sm text-white">Desktop Floating HUD</h3>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Native Tauri 2.0 Rust client that floats on developers&apos; screens <strong className="text-white">without deploying or scaling heavy servers</strong>.
              </p>
            </div>

            {/* Wireframe Graphic (Terminal Deploy & Wireframe Radar Arc) */}
            <div className="p-4 rounded-xl bg-[#090C10] border border-[#1B202A] font-mono text-[11px] space-y-2">
              <div className="text-slate-400 flex items-center justify-between">
                <span>$ kairo hud <span className="text-[#3ECF8E]">--watch</span></span>
                <span className="text-[#3ECF8E] font-bold">RUST ACTIVE</span>
              </div>
              <div className="p-2 rounded bg-[#141822] border border-[#1F2533] text-[10px] text-slate-300 space-y-1">
                <div>[git] Branch: <span className="text-blue-400">feat/billing-webhooks</span></div>
                <div>[hud] Day-1 Action Checklist: <span className="text-emerald-400">2 Items Ready</span></div>
              </div>
            </div>

            <ul className="space-y-2 text-xs text-[#CBD5E1] pt-3 border-t border-[#1B202A]">
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Native Windows, macOS & Linux</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Sub-5ms local Git repository state sync</span>
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-[#3ECF8E]" />
                <span>Slide-out handover briefing drawer</span>
              </li>
            </ul>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION 2 (CONT.): BENTO GRID - PART 2 (4 CARDS: STORAGE, REALTIME, VECTOR, APIS) */}
        {/* ========================================================================= */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
          {/* Card 4: Storage & Diagram OCR */}
          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white">
                <HardDrive size={16} className="text-[#3ECF8E]" />
                <h4 className="font-bold text-xs text-white">Architecture Storage</h4>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Store, parse, and OCR architecture diagrams and ADR assets in high resolution.
              </p>
            </div>
            {/* 3x3 Grid of Asset Wireframes */}
            <div className="grid grid-cols-3 gap-1.5 p-2 rounded-xl bg-[#090C10] border border-[#1B202A]">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-8 rounded bg-[#161B26] border border-[#232936] flex items-center justify-center text-[#64748B]">
                  <FileCode size={13} />
                </div>
              ))}
            </div>
          </div>

          {/* Card 5: Realtime Webhooks & Multiplayer Sync */}
          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white">
                <Radio size={16} className="text-[#3B82F6]" />
                <h4 className="font-bold text-xs text-white">Realtime Ingress</h4>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Dedicated multi-tenant webhook URLs with real-time GitHub & Jira synchronization.
              </p>
            </div>
            {/* Multiplayer Cursor Wireframe */}
            <div className="h-20 rounded-xl bg-[#090C10] border border-[#1B202A] p-2 relative flex items-center justify-center font-mono text-[10px] text-blue-400">
              <div className="flex items-center gap-1">
                <Zap size={13} className="animate-bounce text-[#3ECF8E]" />
                <span>/webhooks/github/{'{org_id}'}</span>
              </div>
            </div>
          </div>

          {/* Card 6: Vector & Provenance Graph */}
          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white">
                <Network size={16} className="text-[#A855F7]" />
                <h4 className="font-bold text-xs text-white">Vector & Neo4j</h4>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Integrate ML models to store, index and traverse temporal provenance graphs.
              </p>
            </div>
            {/* 3D Wireframe Lineage Tag */}
            <div className="p-2.5 rounded-xl bg-[#090C10] border border-[#1B202A] font-mono text-[10px] space-y-1 text-purple-300">
              <div>(:Task)-[:SUPERSEDES]-&gt;(:ADR)</div>
              <div className="text-[#94A3B8] text-[9px]">OpenAI & Gemini Grounded</div>
            </div>
          </div>

          {/* Card 7: Instant Data REST APIs */}
          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-4 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-white">
                <Terminal size={16} className="text-[#F59E0B]" />
                <h4 className="font-bold text-xs text-white">Data APIs</h4>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Instant ready-to-use REST endpoints with OpenAPI specs and Pre-Retrieval ACLs.
              </p>
            </div>
            {/* API Endpoints Wireframe */}
            <div className="p-2 rounded-xl bg-[#090C10] border border-[#1B202A] font-mono text-[10px] space-y-1 text-amber-300">
              <div className="truncate">GET /api/v1/context/work-items</div>
              <div className="truncate text-[#94A3B8]">GET /api/v1/team/continuity</div>
            </div>
          </div>
        </div>

        {/* Section Bottom Tagline */}
        <div className="text-center pt-6">
          <p className="text-xs text-[#94A3B8]">
            <strong className="text-white">Use one or all.</strong> Best of breed work continuity engines. Integrated as a platform.
          </p>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 3: TRUSTED BY 12 FAST-GROWING COMPANIES (SUPABASE MONOCHROME STRIP) */}
      {/* ========================================================================= */}
      <section className="py-16 px-6 max-w-7xl mx-auto w-full border-y border-[#1E232F] text-center space-y-8">
        <p className="text-xs font-semibold text-[#94A3B8] tracking-wider">
          Trusted by fast-growing engineering companies worldwide
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-8 items-center justify-items-center opacity-60 grayscale hover:grayscale-0 transition-all font-bold text-sm tracking-tight text-[#94A3B8]">
          <span className="hover:text-white transition-colors">GitHub</span>
          <span className="hover:text-white transition-colors">Vercel</span>
          <span className="hover:text-white transition-colors">Supabase</span>
          <span className="hover:text-white transition-colors">Linear</span>
          <span className="hover:text-white transition-colors">Stripe</span>
          <span className="hover:text-white transition-colors">Figma</span>
          <span className="hover:text-white transition-colors">Notion</span>
          <span className="hover:text-white transition-colors">Datadog</span>
          <span className="hover:text-white transition-colors">Cloudflare</span>
          <span className="hover:text-white transition-colors">OpenAI</span>
          <span className="hover:text-white transition-colors">HashiCorp</span>
          <span className="hover:text-white transition-colors">Docker</span>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 4: MANAGER STUDIO DASHBOARD EXPLORER (SUPABASE STUDIO SIMULATOR)  */}
      {/* ========================================================================= */}
      <section id="studio" className="py-24 px-6 max-w-7xl mx-auto w-full space-y-12">
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            Stay productive and manage continuity <br />
            without leaving the dashboard
          </h2>
          <p className="text-sm text-[#94A3B8]">
            Inspect live repository single-points-of-failure, evaluate deterministic anomaly radar rules, and audit temporal decision lineage.
          </p>
        </div>

        {/* Tab Controls (Exact Supabase Pill Buttons: Table Editor, SQL Editor, RLS Policies) */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {[
            { id: "continuity", label: "Continuity Map" },
            { id: "anomalies", label: "Anomaly Radar (HW-03)" },
            { id: "lineage", label: "Knowledge Graph & Lineage" },
            { id: "hud", label: "Desktop HUD Stream" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveStudioTab(tab.id as any)}
              className={`px-5 py-2 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                activeStudioTab === tab.id
                  ? "bg-[#1E232F] border-[#2B3242] text-white font-bold shadow-sm"
                  : "bg-transparent border-transparent text-[#94A3B8] hover:text-white hover:bg-white/[0.02]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Studio Window Simulator (Exact Supabase Form & Policy Style) */}
        <div className="rounded-3xl border border-[#1E232F] bg-[#11151F] p-6 sm:p-10 shadow-2xl space-y-6 max-w-5xl mx-auto">
          {/* Top Window Bar */}
          <div className="flex items-center justify-between border-b border-[#1E232F] pb-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#EF4444]/60" />
                <span className="w-3 h-3 rounded-full bg-[#F59E0B]/60" />
                <span className="w-3 h-3 rounded-full bg-[#3ECF8E]/60" />
              </div>
              <span className="font-mono text-xs text-[#94A3B8]">
                kairo-project :: {activeStudioTab}
              </span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-[10px] font-mono bg-[#090C10] text-[#3ECF8E] border border-[#1E232F]">
              RLS ENFORCED
            </span>
          </div>

          {/* Active Tab Content 1: Continuity Map */}
          {activeStudioTab === "continuity" && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-white">Repository Ownership & Single Points of Failure</h3>
                  <p className="text-xs text-[#94A3B8]">Automatic bus factor analysis across connected GitHub repositories</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-[#090C10] border border-[#1E232F] flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FolderGit2 size={16} className="text-[#3ECF8E]" />
                      <span className="font-bold text-xs text-white">snapmeet/billing-service</span>
                    </div>
                    <p className="text-[11px] text-[#94A3B8]">Primary Maintainer: Rahul Sharma (85% ownership) · Target: Aman Verma</p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-red-950/80 text-red-300 border border-red-800/50">
                    CRITICAL SPOF (Bus Factor = 1)
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-[#090C10] border border-[#1E232F] flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FolderGit2 size={16} className="text-[#3ECF8E]" />
                      <span className="font-bold text-xs text-white">snapmeet/auth-service</span>
                    </div>
                    <p className="text-[11px] text-[#94A3B8]">Primary Maintainer: Alice Chen (40% ownership, 3 active reviewers)</p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">
                    HEALTHY (Bus Factor = 3)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Active Tab Content 2: Anomaly Radar */}
          {activeStudioTab === "anomalies" && (
            <div className="p-6 rounded-2xl bg-[#090C10] border border-amber-800/40 space-y-4">
              <div className="flex items-center justify-between border-b border-[#1E232F] pb-3">
                <span className="font-bold text-amber-400 text-xs font-mono">RULE HW-03: STATE MISMATCH</span>
                <span className="text-[11px] font-mono text-amber-300">TRIGGERED: BILL-204</span>
              </div>
              <p className="text-xs text-[#CBD5E1] leading-relaxed">
                Jira ticket <code className="text-[#3ECF8E]">BILL-204</code> is marked <strong className="text-[#3ECF8E]">DONE</strong>, but PR #88 is still <strong className="text-red-400">OPEN</strong> with failing pytest check runs. Offboarding sign-off blocked until CI passes.
              </p>
              <div className="p-3 rounded-lg bg-[#141822] border border-[#1F2533] font-mono text-[11px] text-[#94A3B8]">
                &gt; Remediation: Dispatching alert to #eng-billing Slack channel with commit SHA [e91c2b].
              </div>
            </div>
          )}

          {/* Active Tab Content 3: Interactive Knowledge Graph Studio */}
          {activeStudioTab === "lineage" && (
            <div className="space-y-4">
              {/* Graph Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[#090C10] border border-[#1E232F] text-xs">
                <div className="flex items-center gap-2">
                  <Network size={16} className="text-[#A855F7]" />
                  <span className="font-bold text-white">Neo4j Temporal Knowledge Graph</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950/80 text-purple-300 border border-purple-800/40">
                    AuraDB LIVE
                  </span>
                </div>

                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className="text-[#94A3B8]">Zoom:</span>
                  <button
                    onClick={() => setGraphZoom((prev) => Math.min(prev + 0.15, 1.8))}
                    className="w-6 h-6 rounded bg-[#161B26] hover:bg-[#212635] text-white border border-[#2B3242] flex items-center justify-center font-bold"
                  >
                    +
                  </button>
                  <span className="text-purple-300 px-1">{Math.round(graphZoom * 100)}%</span>
                  <button
                    onClick={() => setGraphZoom((prev) => Math.max(prev - 0.15, 0.7))}
                    className="w-6 h-6 rounded bg-[#161B26] hover:bg-[#212635] text-white border border-[#2B3242] flex items-center justify-center font-bold"
                  >
                    -
                  </button>
                  <button
                    onClick={() => { setGraphZoom(1.0); setSelectedGraphNode("BILL-204"); }}
                    className="px-2 py-0.5 rounded bg-[#161B26] hover:bg-[#212635] text-[#94A3B8] hover:text-white border border-[#2B3242] text-[10px]"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {/* Interactive SVG Graph Canvas with Animated Nodes & Relationship Streams */}
              <div className="relative rounded-2xl bg-[#090C10] border border-[#1E232F] overflow-hidden h-[340px] flex items-center justify-center p-4">
                {/* Background Grid Lines inside Graph */}
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:2rem_2rem] pointer-events-none" />

                <div
                  className="transition-transform duration-300 ease-out w-full h-full flex items-center justify-center relative"
                  style={{ transform: `scale(${graphZoom})` }}
                >
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    <defs>
                      <linearGradient id="lineGradPurple" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#A855F7" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#3ECF8E" stopOpacity="0.8" />
                      </linearGradient>
                      <linearGradient id="lineGradBlue" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#A855F7" stopOpacity="0.8" />
                      </linearGradient>
                    </defs>

                    {/* Edge: Task -> ADR (SUPERSEDES) */}
                    <line x1="22%" y1="50%" x2="48%" y2="28%" stroke="url(#lineGradPurple)" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
                    <text x="32%" y="36%" fill="#A855F7" fontSize="9" fontFamily="monospace" fontWeight="bold">[:SUPERSEDES]</text>

                    {/* Edge: Task -> PR (IMPLEMENTED_BY) */}
                    <line x1="22%" y1="50%" x2="50%" y2="72%" stroke="url(#lineGradBlue)" strokeWidth="2" />
                    <text x="32%" y="65%" fill="#3B82F6" fontSize="9" fontFamily="monospace" fontWeight="bold">[:IMPLEMENTED_BY]</text>

                    {/* Edge: PR -> Commit (CONTAINS) */}
                    <line x1="50%" y1="72%" x2="78%" y2="72%" stroke="#3ECF8E" strokeWidth="2" strokeDasharray="3 3" />
                    <text x="61%" y="66%" fill="#3ECF8E" fontSize="9" fontFamily="monospace" fontWeight="bold">[:CONTAINS]</text>

                    {/* Edge: ADR -> Architecture Doc */}
                    <line x1="48%" y1="28%" x2="78%" y2="28%" stroke="#A855F7" strokeWidth="2" strokeDasharray="2 2" />
                    <text x="60%" y="22%" fill="#94A3B8" fontSize="9" fontFamily="monospace">[:DOCUMENTS]</text>
                  </svg>

                  {/* Node 1: Root Task Node (:Task BILL-204) */}
                  <div
                    onClick={() => setSelectedGraphNode("BILL-204")}
                    className={`absolute left-[12%] top-[38%] -translate-y-1/2 p-3.5 rounded-2xl border transition-all cursor-pointer shadow-lg z-10 flex flex-col items-center gap-1 ${
                      selectedGraphNode === "BILL-204"
                        ? "bg-[#1E1B4B] border-purple-500 shadow-purple-500/30 scale-110"
                        : "bg-[#141822] border-[#2B3242] hover:border-purple-400"
                    }`}
                  >
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping absolute -top-1 -right-1" />
                    <Layers size={18} className="text-purple-400" />
                    <span className="font-mono text-[11px] font-bold text-white">BILL-204</span>
                    <span className="text-[9px] font-mono text-purple-300">:Task</span>
                  </div>

                  {/* Node 2: ADR Node (:ADR-004) */}
                  <div
                    onClick={() => setSelectedGraphNode("ADR-004")}
                    className={`absolute left-[44%] top-[16%] p-3 rounded-2xl border transition-all cursor-pointer shadow-md z-10 flex flex-col items-center gap-1 ${
                      selectedGraphNode === "ADR-004"
                        ? "bg-[#1E1B4B] border-purple-500 shadow-purple-500/30 scale-110"
                        : "bg-[#141822] border-[#2B3242] hover:border-purple-400"
                    }`}
                  >
                    <FileText size={16} className="text-purple-300" />
                    <span className="font-mono text-[10px] font-bold text-white">ADR-004</span>
                    <span className="text-[8px] font-mono text-[#94A3B8]">:ADR</span>
                  </div>

                  {/* Node 3: Pull Request Node (:PullRequest #88) */}
                  <div
                    onClick={() => setSelectedGraphNode("PR-88")}
                    className={`absolute left-[44%] top-[60%] p-3 rounded-2xl border transition-all cursor-pointer shadow-md z-10 flex flex-col items-center gap-1 ${
                      selectedGraphNode === "PR-88"
                        ? "bg-[#172554] border-blue-500 shadow-blue-500/30 scale-110"
                        : "bg-[#141822] border-[#2B3242] hover:border-blue-400"
                    }`}
                  >
                    <GitPullRequest size={16} className="text-blue-400" />
                    <span className="font-mono text-[10px] font-bold text-white">PR #88</span>
                    <span className="text-[8px] font-mono text-[#94A3B8]">:PullRequest</span>
                  </div>

                  {/* Node 4: Commit Node (:Commit e91c2b) */}
                  <div
                    onClick={() => setSelectedGraphNode("COMMIT-e91c2b")}
                    className={`absolute left-[74%] top-[60%] p-3 rounded-2xl border transition-all cursor-pointer shadow-md z-10 flex flex-col items-center gap-1 ${
                      selectedGraphNode === "COMMIT-e91c2b"
                        ? "bg-[#064E3B] border-[#3ECF8E] shadow-emerald-500/30 scale-110"
                        : "bg-[#141822] border-[#2B3242] hover:border-emerald-400"
                    }`}
                  >
                    <GitCommit size={16} className="text-[#3ECF8E]" />
                    <span className="font-mono text-[10px] font-bold text-white">e91c2b</span>
                    <span className="text-[8px] font-mono text-[#94A3B8]">:Commit</span>
                  </div>

                  {/* Node 5: Arch Doc Node (:Doc Invoicing Arch) */}
                  <div
                    onClick={() => setSelectedGraphNode("DOC-ARCH")}
                    className={`absolute left-[74%] top-[16%] p-3 rounded-2xl border transition-all cursor-pointer shadow-md z-10 flex flex-col items-center gap-1 ${
                      selectedGraphNode === "DOC-ARCH"
                        ? "bg-[#1E1B4B] border-purple-500 shadow-purple-500/30 scale-110"
                        : "bg-[#141822] border-[#2B3242] hover:border-purple-400"
                    }`}
                  >
                    <FolderGit2 size={16} className="text-purple-300" />
                    <span className="font-mono text-[10px] font-bold text-white">Invoicing.md</span>
                    <span className="text-[8px] font-mono text-[#94A3B8]">:Doc</span>
                  </div>
                </div>

                {/* Node Inspector Floating Drawer */}
                <div className="absolute bottom-3 right-3 p-3 rounded-xl bg-[#11151F]/90 backdrop-blur-md border border-[#2B3242] text-[11px] font-mono shadow-xl max-w-xs space-y-1">
                  <div className="flex items-center justify-between text-white font-bold pb-1 border-b border-white/[0.08]">
                    <span>Selected: {selectedGraphNode}</span>
                    <span className="text-[#3ECF8E] text-[10px]">VERIFIED 100%</span>
                  </div>
                  {selectedGraphNode === "BILL-204" && (
                    <div className="text-[#94A3B8] space-y-0.5 pt-0.5 text-[10px]">
                      <div>Title: Recurring Invoicing Webhooks</div>
                      <div>Author: Rahul Sharma &rarr; Aman Verma</div>
                      <div className="text-amber-400">Anomaly: HW-03 State Mismatch</div>
                    </div>
                  )}
                  {selectedGraphNode === "ADR-004" && (
                    <div className="text-[#94A3B8] space-y-0.5 pt-0.5 text-[10px]">
                      <div>Decision: Switch to Idempotent Webhook Queue</div>
                      <div>Status: APPROVED_PRODUCTION</div>
                      <div className="text-purple-300">Superseded: ADR-001 Sync Polling</div>
                    </div>
                  )}
                  {selectedGraphNode === "PR-88" && (
                    <div className="text-[#94A3B8] space-y-0.5 pt-0.5 text-[10px]">
                      <div>Repository: snapmeet/billing-service</div>
                      <div>Status: OPEN (3 Commits, 1 Anomaly)</div>
                      <div className="text-blue-300">Target Branch: main</div>
                    </div>
                  )}
                  {selectedGraphNode === "COMMIT-e91c2b" && (
                    <div className="text-[#94A3B8] space-y-0.5 pt-0.5 text-[10px]">
                      <div>Message: feat(billing): add stripe webhook retries</div>
                      <div>Author: rahul@snapmeet.com</div>
                      <div className="text-[#3ECF8E]">CI Status: Pytest Passing</div>
                    </div>
                  )}
                  {selectedGraphNode === "DOC-ARCH" && (
                    <div className="text-[#94A3B8] space-y-0.5 pt-0.5 text-[10px]">
                      <div>Path: docs/architecture/invoicing.md</div>
                      <div>OCR Extracted: 4 Microservice Blocks</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Dynamic Cypher Query Output Console */}
              <div className="p-3.5 rounded-xl bg-[#090C10] border border-[#1E232F] font-mono text-xs space-y-1.5 text-slate-300">
                <div className="flex items-center justify-between text-[#94A3B8] text-[10px]">
                  <span>CYPHER QUERY ENGINE</span>
                  <span className="text-[#3ECF8E]">EXECUTION TIME: 2.1ms</span>
                </div>
                <div className="text-purple-400">
                  MATCH (t:Task &#123;key: &quot;{selectedGraphNode}&quot;&#125;)-[r:SUPERSEDES|IMPLEMENTED_BY|CONTAINS*1..3]-&gt;(n)
                </div>
                <div className="text-slate-400">
                  RETURN t, r, n ORDER BY n.timestamp DESC LIMIT 25;
                </div>
              </div>
            </div>
          )}

          {/* Active Tab Content 4: Desktop HUD */}
          {activeStudioTab === "hud" && (
            <div className="p-6 rounded-2xl bg-[#090C10] border border-[#1E232F] space-y-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-white">Local Git Watcher Stream</span>
                <span className="text-[#3ECF8E] font-bold">STREAMING ACTIVE</span>
              </div>
              <p className="text-xs text-[#94A3B8]">
                Tauri 2.0 Rust HUD floating on engineer screen. Active repository <code className="text-blue-400">snapmeet/billing-service</code> detected on branch <code className="text-[#3ECF8E]">feat/invoicing-retry</code>.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 5: KICKSTART WITH PRODUCTION READY TEMPLATES (SUPABASE STYLE)     */}
      {/* ========================================================================= */}
      <section id="templates" className="py-24 px-6 max-w-7xl mx-auto w-full space-y-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-3">
            <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
              Kickstart your next transition <br />
              with production ready playbooks
            </h2>
            <p className="text-sm text-[#94A3B8]">
              Grounded handover starters for lead departures, pod re-architectures, and incident root-cause provenance.
            </p>
          </div>
          <a href="#studio" className="text-xs font-bold text-[#3ECF8E] hover:underline flex items-center gap-1">
            <span>View all playbooks</span>
            <ArrowRight size={13} />
          </a>
        </div>

        {/* 2 Big Template Cards (Exact Supabase Stripe + Next.js Starter Layout) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Lead Engineer Offboarding Starter */}
          <div className="p-8 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-6">
            <div className="space-y-2">
              <span className="text-xs font-mono font-bold text-[#3ECF8E]">github + jira starter</span>
              <h3 className="font-bold text-lg text-white">Lead Engineer Offboarding Playbook</h3>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                The all-in-one offboarding starter for engineering leaders: reconciles unmerged PRs, extracts active ADRs, and generates verified briefings for incoming leads.
              </p>
            </div>

            {/* Wireframe Briefing Preview */}
            <div className="p-5 rounded-xl bg-[#090C10] border border-[#1B202A] space-y-3 font-mono text-[11px]">
              <div className="flex items-center justify-between text-xs text-white">
                <span>Offboarding Lead: Rahul Sharma</span>
                <span className="text-[#3ECF8E]">100% CITED</span>
              </div>
              <div className="space-y-1.5 text-[#94A3B8] text-[10px]">
                <div className="flex items-center gap-2">
                  <Check size={12} className="text-[#3ECF8E]" />
                  <span>3 Microservices indexed (Billing, Auth, Transcoder)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check size={12} className="text-[#3ECF8E]" />
                  <span>Day-1 Action Checklist generated for Aman Verma</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Pod Ownership Reassignment Starter */}
          <div className="p-8 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-6">
            <div className="space-y-2">
              <span className="text-xs font-mono font-bold text-[#3B82F6]">microservices starter</span>
              <h3 className="font-bold text-lg text-white">Pod Re-Architecture & Ownership Transfer</h3>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Rebalance code ownership across squads while maintaining Bus Factor &gt; 1 safety margins and eliminating orphaned dependency bottlenecks.
              </p>
            </div>

            {/* Wireframe Grid Preview */}
            <div className="p-5 rounded-xl bg-[#090C10] border border-[#1B202A] space-y-3 font-mono text-[11px]">
              <div className="flex items-center justify-between text-xs text-white">
                <span>Pod Rebalance: Payments Squad</span>
                <span className="text-blue-400">BALANCED</span>
              </div>
              <div className="space-y-1.5 text-[#94A3B8] text-[10px]">
                <div className="flex items-center gap-2">
                  <Check size={12} className="text-[#3ECF8E]" />
                  <span>Calculated code ownership across 14 team members</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check size={12} className="text-[#3ECF8E]" />
                  <span>Zero unowned services or orphaned repositories</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 4 Small Template Cards Below (Exact Supabase 4-Grid Style) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-3">
            <div className="flex items-center gap-2 text-purple-400">
              <Sparkles size={16} />
              <h4 className="font-bold text-xs text-white">AI Grounded Briefing</h4>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              OpenAI & Gemini grounded briefing engine with strictly verified commit citations.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-3">
            <div className="flex items-center gap-2 text-[#3ECF8E]">
              <Database size={16} />
              <h4 className="font-bold text-xs text-white">pgvector Semantic Search</h4>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Tenant-isolated PostgreSQL vector embeddings for code and decision queries.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-3">
            <div className="flex items-center gap-2 text-[#3B82F6]">
              <Cpu size={16} />
              <h4 className="font-bold text-xs text-white">Tauri 2.0 Rust HUD</h4>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Native cross-platform desktop overlay client for instant screen briefings.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-[#11151F] border border-[#1E232F] hover:border-[#2B3242] transition-all space-y-3">
            <div className="flex items-center gap-2 text-amber-400">
              <Radio size={16} />
              <h4 className="font-bold text-xs text-white">Slack Anomaly Bot</h4>
            </div>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Automated webhook bot dispatching instant HW-03 warnings to team channels.
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 6: DEVELOPER CLI EXPERIENCE (SUPABASE CLI STYLE)                  */}
      {/* ========================================================================= */}
      <section id="cli" className="py-24 px-6 max-w-7xl mx-auto w-full space-y-12">
        <div className="rounded-3xl border border-[#1E232F] bg-[#11151F] p-8 sm:p-12 space-y-8">
          <div className="max-w-2xl space-y-3">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
              Manage your continuity directly from the terminal
            </h2>
            <p className="text-sm text-[#94A3B8]">
              The KAIRO CLI gives developers local anomaly evaluation, git history parsing, and offline handover generation.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#090C10] border border-[#1B202A] font-mono text-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#1B202A] pb-3">
              <div className="flex items-center gap-2">
                <Terminal size={15} className="text-[#3ECF8E]" />
                <span className="text-slate-300">Terminal — bash</span>
              </div>
              <button
                onClick={handleCopyCli}
                className="flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-white px-2 py-1 rounded bg-[#161B26] border border-[#232936] cursor-pointer"
              >
                {copiedCli ? <Check size={12} className="text-[#3ECF8E]" /> : <Copy size={12} />}
                <span>{copiedCli ? "Copied!" : "Copy"}</span>
              </button>
            </div>

            <div className="space-y-2 text-slate-300">
              <div className="text-[#94A3B8]"># 1. Initialize KAIRO in your repository</div>
              <div className="text-white">&gt; npx kairo@latest init</div>
              <div className="text-[#94A3B8] pt-2"># 2. Run local deterministic anomaly scan (HW-01..HW-05)</div>
              <div className="text-white">&gt; kairo scan --rule HW-03</div>
              <div className="text-[#3ECF8E]">[✓] 0 anomalies detected. Git tree and Jira state in 100% agreement.</div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 7: FREQUENTLY ASKED QUESTIONS (FAQ)                               */}
      {/* ========================================================================= */}
      <section id="faq" className="py-24 px-6 max-w-4xl mx-auto w-full space-y-12">
        <div className="text-center space-y-3">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="space-y-3">
          {[
            {
              q: "How does KAIRO avoid LLM hallucinations during handover?",
              a: "KAIRO uses deterministic Python anomaly rules (HW-01 to HW-05) for state estimation and constrains the LLM synthesizer to inline citations referencing concrete commit SHAs and PR numbers.",
            },
            {
              q: "Does KAIRO track developer productivity or surveillance metrics?",
              a: "Never. KAIRO is explicitly designed with zero surveillance. We do not count lines of code, measure active typing hours, or rank engineers. Our engine focuses entirely on work item truth and knowledge continuity.",
            },
            {
              q: "How do we connect our GitHub repositories to KAIRO?",
              a: "Every organization receives a dedicated webhook endpoint (e.g. /webhooks/github/{org_id}). When you paste this into GitHub, any push, PR, or ping event automatically auto-discovers and links that repository to your live continuity map.",
            },
            {
              q: "What platforms does the Desktop HUD support?",
              a: "The Desktop HUD is built on Tauri 2.0 and Rust, providing native, ultra-lightweight binaries for Windows (.msi), macOS (.dmg), and Linux (.AppImage).",
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-[#1E232F] bg-[#11151F] overflow-hidden transition-all"
            >
              <button
                onClick={() => toggleFaq(idx)}
                className="w-full p-5 text-left flex items-center justify-between font-bold text-sm text-white cursor-pointer hover:bg-white/[0.02]"
              >
                <span>{item.q}</span>
                <ChevronDown
                  size={16}
                  className={`text-[#94A3B8] transition-transform ${openFaq === idx ? "rotate-180 text-[#3ECF8E]" : ""}`}
                />
              </button>
              {openFaq === idx && (
                <div className="px-5 pb-5 text-xs text-[#94A3B8] leading-relaxed border-t border-[#1B202A] pt-3">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 8: HIGH IMPACT CLOSING CTA BANNER                                  */}
      {/* ========================================================================= */}
      <section className="py-20 px-6 max-w-7xl mx-auto w-full">
        <div className="rounded-3xl border border-[#1E232F] bg-[#11151F] p-10 sm:p-16 text-center space-y-6 shadow-2xl relative overflow-hidden">
          <h2 className="text-3xl sm:text-5xl font-black tracking-tight text-white max-w-2xl mx-auto leading-tight">
            Build in a weekend. <br />
            <span className="text-[#3ECF8E]">Scale your work continuity.</span>
          </h2>
          <p className="text-sm sm:text-base text-[#94A3B8] max-w-xl mx-auto">
            Deploy KAIRO across your engineering pods in under 5 minutes. No code surveillance, 100% grounded truth.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-3">
            <Link
              href="/auth?mode=register"
              className="w-full sm:w-auto px-8 py-3.5 bg-[#3ECF8E] hover:bg-[#34B27B] text-black font-bold text-xs rounded-lg shadow-md transition-all"
            >
              Start your project
            </Link>
            <Link
              href="/auth?mode=login"
              className="w-full sm:w-auto px-8 py-3.5 bg-[#161B26] hover:bg-[#1E232F] text-white font-semibold text-xs rounded-lg border border-[#2B3242] transition-all"
            >
              Sign in to existing workspace
            </Link>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SECTION 9: CLEAN ENTERPRISE FOOTER                                        */}
      {/* ========================================================================= */}
      <footer className="border-t border-[#1E232F] bg-[#090C10] px-6 py-14 text-[#94A3B8] text-xs mt-auto">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10">
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <img src="/kairo.png" alt="KAIRO" className="w-6 h-6 object-contain" />
              <div className="flex flex-col leading-none">
                <span className="font-extrabold text-white text-base">KAIRO</span>
                <span className="text-[8px] font-mono tracking-widest text-[#94A3B8] uppercase mt-0.5">enterprise</span>
              </div>
            </div>
            <p className="text-[#94A3B8] text-xs leading-relaxed">
              Enterprise AI work continuity and temporal knowledge engine. Eliminates engineering context loss during offboarding and pod reassignments.
            </p>
            <div className="flex items-center gap-2 text-[#3ECF8E] font-mono text-[11px]">
              <span className="w-2 h-2 rounded-full bg-[#3ECF8E] animate-pulse" />
              <span>FastAPI Gateway: Operational (Port 8000)</span>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-white text-xs uppercase tracking-wider font-mono">Product & Engines</h4>
            <ul className="space-y-2 text-[#94A3B8]">
              <li><a href="#product" className="hover:text-white transition-colors">Postgres Truth Database</a></li>
              <li><a href="#anomalies" className="hover:text-white transition-colors">Deterministic Anomaly Radar</a></li>
              <li><a href="#studio" className="hover:text-white transition-colors">Manager Studio</a></li>
              <li><a href="#templates" className="hover:text-white transition-colors">Handoff Playbooks</a></li>
            </ul>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-white text-xs uppercase tracking-wider font-mono">Security & Isolation</h4>
            <ul className="space-y-2 text-[#94A3B8]">
              <li>Row-Level Security (RLS) Policies</li>
              <li>HMAC SHA-256 Webhook Verification</li>
              <li>Pre-Retrieval ACL Guard</li>
              <li>Zero Employee Surveillance Guarantee</li>
            </ul>
          </div>

          <div className="space-y-3">
            <h4 className="font-bold text-white text-xs uppercase tracking-wider font-mono">Developer Resources</h4>
            <ul className="space-y-2 text-[#94A3B8]">
              <li>
                <a href={API_BASE.replace(/\/api\/v1$/, "") + "/docs"} target="_blank" rel="noreferrer" className="hover:text-white flex items-center gap-1">
                  <span>FastAPI OpenAPI Specs</span>
                  <ExternalLink size={11} />
                </a>
              </li>
              <li><Link href="/auth?mode=register" className="hover:text-white">Register Organization</Link></li>
              <li><Link href="/dashboard" className="hover:text-white">Manager Dashboard</Link></li>
            </ul>
          </div>
        </div>

        <div className="max-w-7xl mx-auto border-t border-[#1B202A] mt-12 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-[#64748B]">
          <span>© 2026 KAIRO Technologies Inc. All rights reserved. Zero-Surveillance Work Continuity Engine.</span>
          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-[#94A3B8]">Privacy Policy</a>
            <a href="#" className="hover:text-[#94A3B8]">Terms of Service</a>
            <a href="#" className="hover:text-[#94A3B8]">Trust Center</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
