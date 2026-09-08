import React, { useState, useEffect, useCallback } from "react";
import { FloatingPill } from "./components/FloatingPill";
import { HandoffDrawer } from "./components/HandoffDrawer";
import { FloatingLogoIcon } from "./components/FloatingLogoIcon";
import { ActiveContext, AnomalyAlert, ActionStep } from "./types";
import { Lock, Mail, ArrowRight, Loader2, AlertCircle, GripVertical, Minimize2, Zap } from "lucide-react";

const API_BASE = "http://localhost:8000/api/v1";

const STORAGE_KEY_TOKEN = "kairo_jwt_token";
const STORAGE_KEY_USER = "kairo_cached_user_context";
const STORAGE_KEY_ACTIVE = "kairo_cached_active_context";
const STORAGE_KEY_REPOS = "kairo_cached_repos";
const STORAGE_KEY_ANOMALIES = "kairo_cached_anomalies";
const STORAGE_KEY_CHECKLIST = "kairo_cached_checklist";

interface UserIdentityContext {
  user_id: string;
  name: string;
  email: string;
  organization_id: string;
  company_name: string;
  role: string;
  status: string;
  teams: { id: string; name: string }[];
  allowed_repos: string[];
  devices: { id: string; device_name: string; platform: string; status: string }[];
  external_identities: { provider: string; external_username: string }[];
  active_device_id?: string;
}

const resizeWindow = async (expanded: boolean) => {
  try {
    if ((window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__) {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("set_hud_window_size", {
        width: expanded ? 400.0 : 200.0,
        height: expanded ? 600.0 : 54.0,
      });
    }
  } catch (err) {
    console.warn("Tauri window resize error:", err);
  }
};

export const App: React.FC = () => {
  // Default to floating logo icon
  const [viewMode, setViewMode] = useState<"icon" | "boxcard">("icon");
  const [authToken, setAuthToken] = useState<string>("");
  const [userContext, setUserContext] = useState<UserIdentityContext | null>(null);
  const [activeContext, setActiveContext] = useState<ActiveContext | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyAlert[]>([]);
  const [checklist, setChecklist] = useState<ActionStep[]>([]);
  const [reposList, setReposList] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authenticating, setAuthenticating] = useState(false);

  const loadUserContext = useCallback(async (token: string, targetRepo?: string) => {
    try {
      let devId = localStorage.getItem("kairo_device_id");
      try {
        const enrollRes = await fetch(`${API_BASE}/identity/devices/enroll`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ device_name: "Desktop-HUD-Client", platform: "windows", app_version: "2.0.0" }),
        });
        if (enrollRes.ok) {
          const devData = await enrollRes.json();
          devId = devData.id;
          if (devId) localStorage.setItem("kairo_device_id", devId);
        }
      } catch { /* offline */ }

      const contextRes = await fetch(
        `${API_BASE}/me/context${devId ? `?device_id=${devId}` : ""}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!contextRes.ok) {
        if (contextRes.status === 401 && token !== "kairo_demo_token_authenticated") {
          localStorage.removeItem(STORAGE_KEY_TOKEN);
          localStorage.removeItem(STORAGE_KEY_USER);
          localStorage.removeItem(STORAGE_KEY_ACTIVE);
          setAuthToken(""); setUserContext(null); setActiveContext(null);
        }
        return;
      }

      const idContext: UserIdentityContext = await contextRes.json();
      setUserContext(idContext);
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(idContext));

      const intRes = await fetch(`${API_BASE}/team/${idContext.organization_id}/integrations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      let repos: string[] = idContext.allowed_repos || [];
      if (intRes.ok) {
        const intData = await intRes.json();
        if (intData.repositories?.length > 0)
          repos = Array.from(new Set([...repos, ...intData.repositories.map((r: any) => r.name)]));
      }
      if (repos.length === 0) repos = [`${idContext.organization_id}/primary-repo`];
      setReposList(repos);
      localStorage.setItem(STORAGE_KEY_REPOS, JSON.stringify(repos));

      let nativeGit: { repo?: string; branch?: string; task_key?: string } | null = null;
      try {
        if ((window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__) {
          const { invoke } = await import("@tauri-apps/api/core");
          nativeGit = await invoke("get_active_context");
        }
      } catch { /* browser */ }

      let activeRepo = targetRepo;
      if (!activeRepo) {
        if (nativeGit?.repo) {
          const matched = repos.find((r) => r.includes(nativeGit!.repo!));
          activeRepo = matched || `${idContext.organization_id}/${nativeGit.repo}`;
          if (!repos.includes(activeRepo)) { repos = [activeRepo, ...repos]; setReposList(repos); }
        } else activeRepo = repos[0];
      }
      setSelectedRepo(activeRepo);

      const repoShort = activeRepo.includes("/") ? activeRepo.split("/")[1] : activeRepo;
      const primaryTeam = idContext.teams?.length > 0 ? idContext.teams[0].name : "Engineering";
      const activeBranch = nativeGit?.branch || "main";
      const detectedTask = nativeGit?.task_key && nativeGit.task_key !== "ACTIVE" ? nativeGit.task_key : null;

      const anomRes = await fetch(`${API_BASE}/team/${idContext.organization_id}/anomalies`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      let realAnomalies: AnomalyAlert[] = [];
      if (anomRes.ok) {
        const anomData = await anomRes.json();
        const rawList = anomData.active_anomalies || anomData.anomalies || [];
        realAnomalies = rawList
          .filter((a: any) => !a.repo_name || a.repo_name === activeRepo || rawList.length <= 2)
          .map((a: any) => ({
            id: a.id || `anom_${a.rule_id}`,
            ruleId: a.rule_id,
            title: a.rule_id === "HW-03" ? "State Mismatch (Jira vs PR)"
              : a.rule_id === "HW-01" ? "Shadow Work / Unlinked Commits"
              : a.rule_id === "HW-05" ? "Orphaned Critical Dependency"
              : "Continuity Alert",
            severity: a.severity || "HIGH",
            description: a.summary || "Discrepancy detected between declared task state and git commits.",
            action: a.recommended_action || "Review pending PR and verify CI results.",
          }));
      }
      setAnomalies(realAnomalies);
      localStorage.setItem(STORAGE_KEY_ANOMALIES, JSON.stringify(realAnomalies));

      const handoffRes = await fetch(`${API_BASE}/team/${idContext.organization_id}/handoffs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      let activeHandoff: any = null;
      if (handoffRes.ok) {
        const hData = await handoffRes.json();
        const history = hData.history || hData.packages || [];
        if (history.length > 0)
          activeHandoff = history.find((h: any) => h.repo_name === activeRepo) || history[0];
      }

      const finalTaskKey =
        detectedTask || activeHandoff?.task_key ||
        idContext.organization_id.toUpperCase().slice(0, 4) + "-101";

      const newActiveContext: ActiveContext = {
        organization: idContext.organization_id,
        repo: repoShort,
        branch: activeBranch,
        taskKey: finalTaskKey,
        taskTitle: activeHandoff
          ? `${repoShort} Transition & Continuity`
          : `${repoShort} (${primaryTeam})`,
        status: realAnomalies.length > 0 ? "ANOMALY_DETECTED" : "ACTIVE",
        outgoingDev: { name: activeHandoff?.from_developer || "Primary Owner" },
        incomingDev: { name: activeHandoff?.to_developer || idContext.name },
        executiveSummary: `Commits on \`${activeRepo}\` (Branch: \`${activeBranch}\`) monitored for ${idContext.name} [${primaryTeam}].`,
        activeArtifacts: [{
          id: "art_main",
          type: activeHandoff ? "BRANCH" : "REPOSITORY",
          title: `${activeRepo}: ${activeBranch}`,
          status: realAnomalies.length > 0 ? "Anomaly Flagged" : "Synchronized",
        }],
      };

      setActiveContext(newActiveContext);
      localStorage.setItem(STORAGE_KEY_ACTIVE, JSON.stringify(newActiveContext));

      const steps: ActionStep[] =
        realAnomalies.length > 0
          ? realAnomalies.map((a, i) => ({
              id: i + 1,
              title: `Resolve ${a.ruleId}: ${a.title}`,
              description: a.action,
              completed: false,
            }))
          : [{
              id: 1,
              title: `Sync ${activeRepo} workspace`,
              description: `Git watcher indexing commits for device ${devId || "enrolled"}.`,
              completed: true,
            }];

      setChecklist(steps);
      localStorage.setItem(STORAGE_KEY_CHECKLIST, JSON.stringify(steps));
    } catch (e) {
      console.error("Context load error:", e);
    }
  }, []);

  // Hydrate session from localStorage to ensure user stays logged in across system sessions
  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEY_TOKEN);
    if (token) {
      setAuthToken(token);
      try {
        const cachedUser = localStorage.getItem(STORAGE_KEY_USER);
        if (cachedUser) setUserContext(JSON.parse(cachedUser));
        const cachedActive = localStorage.getItem(STORAGE_KEY_ACTIVE);
        if (cachedActive) setActiveContext(JSON.parse(cachedActive));
        const cachedRepos = localStorage.getItem(STORAGE_KEY_REPOS);
        if (cachedRepos) setReposList(JSON.parse(cachedRepos));
        const cachedAnom = localStorage.getItem(STORAGE_KEY_ANOMALIES);
        if (cachedAnom) setAnomalies(JSON.parse(cachedAnom));
        const cachedSteps = localStorage.getItem(STORAGE_KEY_CHECKLIST);
        if (cachedSteps) setChecklist(JSON.parse(cachedSteps));
      } catch (e) {
        console.warn("Cache parse error:", e);
      }
      setViewMode("icon");
      resizeWindow(false);
      loadUserContext(token);
    } else {
      setViewMode("icon");
      resizeWindow(false);
    }
  }, [loadUserContext]);

  const handleDeactivate = useCallback(async () => {
    setViewMode("icon");
    resizeWindow(false);
    try {
      if ((window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__) {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("hide_hud");
      }
    } catch (err) {
      console.warn("hide_hud invoke error:", err);
    }
  }, []);

  const handleExpandBoxcard = useCallback(() => {
    setViewMode("boxcard");
    resizeWindow(true);
  }, []);

  const handleCollapseToIcon = useCallback(() => {
    setViewMode("icon");
    resizeWindow(false);
  }, []);

  // Global Shortcut & Event Listeners (Ctrl+Space to toggle HUD, Escape to deactivate)
  useEffect(() => {
    // 1. Keyboard event listener when webview has focus
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.code === "Space" || e.key === " ")) {
        e.preventDefault();
        setViewMode((prev) => {
          if (prev === "boxcard") {
            handleDeactivate();
            return "icon";
          } else {
            resizeWindow(true);
            return "boxcard";
          }
        });
      } else if (e.key === "Escape") {
        e.preventDefault();
        // Deactivate & hide without logging out
        handleDeactivate();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    // 2. Native Win32 global hotkey events emitted by Tauri background thread
    let unlistenWake: (() => void) | undefined;
    let unlistenDeact: (() => void) | undefined;
    let unlistenToggle: (() => void) | undefined;

    const setupTauriListener = async () => {
      try {
        if ((window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__) {
          const { listen } = await import("@tauri-apps/api/event");
          unlistenWake = await listen("wake-hud-icon", () => {
            // Wake up as chota wala HUD
            setViewMode("icon");
            resizeWindow(false);
          });
          unlistenDeact = await listen("deactivate-hud", () => {
            // Deactivate / hide HUD
            setViewMode("icon");
            resizeWindow(false);
          });
          unlistenToggle = await listen("toggle-hud", () => {
            setViewMode("icon");
            resizeWindow(false);
          });
        }
      } catch (err) {
        console.warn("Tauri event listen error:", err);
      }
    };
    setupTauriListener();

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      if (unlistenWake) unlistenWake();
      if (unlistenDeact) unlistenDeact();
      if (unlistenToggle) unlistenToggle();
    };
  }, [handleDeactivate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setAuthenticating(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailInput.trim(), password: passwordInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setAuthToken(data.access_token);
        localStorage.setItem(STORAGE_KEY_TOKEN, data.access_token);
        await loadUserContext(data.access_token);
        setViewMode("icon");
        resizeWindow(false);
      } else {
        const err = await res.json().catch(() => ({}));
        setAuthError(err.detail || "Invalid credentials. Please try again.");
      }
    } catch {
      setAuthError("Cannot reach KAIRO API. Ensure backend is running on port 8000.");
    } finally {
      setAuthenticating(false);
    }
  };

  // 1-Click Dev / Demo Workspace
  const handleDemoLogin = () => {
    const demoToken = "kairo_demo_token_authenticated";
    const demoId: UserIdentityContext = {
      user_id: "usr_demo",
      name: "Aditya",
      email: "aditya@company.com",
      organization_id: "snapmeet",
      company_name: "SnapMeet Inc",
      role: "Lead Engineer",
      status: "ACTIVE",
      teams: [{ id: "eng", name: "Core Infrastructure" }],
      allowed_repos: ["snapmeet/billing-service", "snapmeet/auth-service"],
      devices: [{ id: "dev_win", device_name: "Desktop-HUD-Client", platform: "windows", status: "ONLINE" }],
      external_identities: [{ provider: "github", external_username: "adity" }],
    };
    const demoActive: ActiveContext = {
      organization: "snapmeet",
      repo: "billing-service",
      branch: "feat/BILL-204-razorpay-retry",
      taskKey: "BILL-204",
      taskTitle: "Razorpay Webhook Retry & Anomaly Engine",
      status: "ANOMALY_DETECTED",
      outgoingDev: { name: "Rahul Sharma" },
      incomingDev: { name: "Aditya" },
      executiveSummary: "Commits on `billing-service` [PR #88] implement webhook retry logic. State mismatch [HW-03] flagged against Jira BILL-204.",
      activeArtifacts: [
        { id: "art_1", type: "BRANCH", title: "billing-service: feat/BILL-204-razorpay-retry", status: "HW-03 Flagged" },
        { id: "art_2", type: "PR", title: "PR #88: Retry backoff algorithm", status: "Under Review" }
      ],
    };
    const demoAnomalies: AnomalyAlert[] = [
      {
        id: "anom_1",
        ruleId: "HW-03",
        title: "State Mismatch (Jira vs PR)",
        severity: "HIGH",
        description: "Jira task BILL-204 marked 'IN_PROGRESS' while PR #88 was merged without QA verification tag.",
        action: "Trigger automated verification run and update Jira status to RESOLVED.",
      },
      {
        id: "anom_2",
        ruleId: "HW-01",
        title: "Shadow Work Detected",
        severity: "MEDIUM",
        description: "3 unlinked commits observed on branch `feat/BILL-204-razorpay-retry` missing Jira ticket prefix.",
        action: "Link commit hashes to BILL-204 before merging to main.",
      }
    ];
    const demoChecklist: ActionStep[] = [
      { id: 1, title: "Resolve HW-03: State Mismatch", description: "Review PR #88 and update Jira ticket status", completed: false, targetFile: "billing/webhook.py" },
      { id: 2, title: "Verify idempotency keys", description: "Confirm Redis cache TTL for webhook event deduplication", completed: true, targetFile: "billing/idempotency.py" },
      { id: 3, title: "Audit dead-letter queue", description: "Run test payload against failed webhook queue", completed: false, targetFile: "workers/dlq.py" },
    ];

    setAuthToken(demoToken);
    setUserContext(demoId);
    setActiveContext(demoActive);
    setAnomalies(demoAnomalies);
    setChecklist(demoChecklist);
    setReposList(["snapmeet/billing-service", "snapmeet/auth-service"]);
    setSelectedRepo("snapmeet/billing-service");

    localStorage.setItem(STORAGE_KEY_TOKEN, demoToken);
    localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(demoId));
    localStorage.setItem(STORAGE_KEY_ACTIVE, JSON.stringify(demoActive));
    localStorage.setItem(STORAGE_KEY_ANOMALIES, JSON.stringify(demoAnomalies));
    localStorage.setItem(STORAGE_KEY_CHECKLIST, JSON.stringify(demoChecklist));
    localStorage.setItem(STORAGE_KEY_REPOS, JSON.stringify(["snapmeet/billing-service", "snapmeet/auth-service"]));

    setViewMode("boxcard");
    resizeWindow(true);
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    localStorage.removeItem(STORAGE_KEY_USER);
    localStorage.removeItem(STORAGE_KEY_ACTIVE);
    localStorage.removeItem(STORAGE_KEY_REPOS);
    localStorage.removeItem(STORAGE_KEY_ANOMALIES);
    localStorage.removeItem(STORAGE_KEY_CHECKLIST);
    setAuthToken(""); setUserContext(null); setActiveContext(null);
    setViewMode("boxcard");
    resizeWindow(true);
  };

  const toggleStep = (id: number) =>
    setChecklist((prev) => prev.map((s) => (s.id === id ? { ...s, completed: !s.completed } : s)));

  const handleRepoChange = (repo: string) => {
    setSelectedRepo(repo);
    if (authToken) loadUserContext(authToken, repo);
  };

  // Safe fallback context for Logo Icon
  const displayContext: ActiveContext = activeContext || {
    organization: "KAIRO",
    repo: "Workspace",
    branch: "main",
    taskKey: "KAIRO",
    taskTitle: "Click to Open HUD",
    status: "ACTIVE",
    outgoingDev: { name: "Developer" },
    incomingDev: { name: "Developer" },
  };

  // ─── State 1: Floating Logo Icon Trigger Mode ──────────────────────────────
  // (Always renders when viewMode is "icon", whether logged in or not)
  if (viewMode === "icon") {
    return (
      <FloatingLogoIcon
        context={displayContext}
        hasAnomalies={anomalies.length > 0}
        onExpand={handleExpandBoxcard}
      />
    );
  }

  // ─── State 2A: Connect Workspace Screen (when in Boxcard mode but not logged in)
  if (!authToken || !userContext || !activeContext) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#0c101d",
          borderRadius: "16px",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
        className="animate-fade-in font-sans"
      >
        {/* Drag Header with Minimize Button */}
        <div
          data-tauri-drag-region
          className="drag-region flex items-center justify-between px-4 py-3 border-b border-white/[0.08] bg-[#090d16] cursor-grab active:cursor-grabbing shrink-0"
        >
          <div className="flex items-center gap-2.5 pointer-events-none">
            <GripVertical size={14} className="text-slate-500" />
            <img src="/kairo.png" alt="KAIRO" className="w-5 h-5 object-contain" />
            <span className="font-display font-bold text-xs tracking-wider text-slate-100">KAIRO</span>
            <span className="text-[10px] text-slate-500 font-mono">HUD</span>
          </div>

          <div className="no-drag flex items-center gap-2">
            <span className="font-mono text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/25 px-2 py-0.5 rounded-md">
              v2.0
            </span>
            <button
              type="button"
              onClick={handleCollapseToIcon}
              className="w-6 h-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-indigo-400 hover:bg-white/[0.06] transition-all"
              title="Minimize to Logo Icon (Ctrl+Space)"
            >
              <Minimize2 size={13} />
            </button>
          </div>
        </div>

        {/* Auth Body */}
        <div className="flex-1 p-5 flex flex-col justify-between bg-[#0c101d]">
          <div>
            <div className="mb-4">
              <h1 className="font-display text-xl font-bold text-slate-100 tracking-tight mb-1">
                Connect Workspace
              </h1>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Sign in to sync your live repositories and stream continuity telemetry.
              </p>
            </div>

            {authError && (
              <div className="mb-3.5 p-2.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-xs text-rose-300 flex items-start gap-2 animate-fade-in">
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <span className="leading-snug">{authError}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-3">
              <div className="space-y-1">
                <label className="font-mono text-[10px] font-semibold text-slate-400 tracking-wider uppercase">
                  Work Email
                </label>
                <div className="no-drag flex items-center gap-2 px-3 py-2 rounded-xl bg-[#121829] border border-white/[0.08] focus-within:border-indigo-500/50 transition-colors">
                  <Mail size={13} className="text-slate-500 shrink-0" />
                  <input
                    type="email"
                    required
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="developer@company.com"
                    className="w-full bg-transparent border-none outline-none text-xs text-slate-100 placeholder-slate-500 font-sans"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-mono text-[10px] font-semibold text-slate-400 tracking-wider uppercase">
                  Password
                </label>
                <div className="no-drag flex items-center gap-2 px-3 py-2 rounded-xl bg-[#121829] border border-white/[0.08] focus-within:border-indigo-500/50 transition-colors">
                  <Lock size={13} className="text-slate-500 shrink-0" />
                  <input
                    type="password"
                    required
                    value={passwordInput}
                    onChange={(e) => setPasswordInput(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-transparent border-none outline-none text-xs text-slate-100 placeholder-slate-500 font-sans"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={authenticating}
                className="no-drag w-full mt-1.5 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-50 text-white text-xs font-semibold tracking-wide flex items-center justify-center gap-2 transition-all shadow-sm active:scale-[0.98]"
              >
                {authenticating ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <>
                    <span>Continue to HUD</span>
                    <ArrowRight size={13} />
                  </>
                )}
              </button>
            </form>

            {/* 1-Click Dev Demo Button */}
            <div className="mt-3 pt-3 border-t border-white/[0.06]">
              <button
                type="button"
                onClick={handleDemoLogin}
                className="no-drag w-full py-2 px-3 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/25 text-xs font-medium flex items-center justify-center gap-1.5 transition-all"
              >
                <Zap size={13} className="text-indigo-400" />
                <span>Launch Demo Workspace (1-Click)</span>
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-white/[0.06] text-center">
            <p className="text-[11px] text-slate-500">
              Shortcut: <span className="text-indigo-400 font-mono">Ctrl + Space</span> to toggle HUD
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ─── State 2B: Expanded Boxcard HUD Mode (Logged in) ────────────────────────
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        maxHeight: "600px",
        background: "#0c101d",
        borderRadius: "16px",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
      className="font-sans select-none animate-fade-in"
    >
      <FloatingPill
        context={activeContext}
        hasAnomalies={anomalies.length > 0}
        isOpen={true}
        onToggle={handleCollapseToIcon}
        isEmbedded={true}
      />
      <HandoffDrawer
        context={activeContext}
        anomalies={anomalies}
        checklist={checklist}
        reposList={reposList}
        selectedRepo={selectedRepo || reposList[0] || ""}
        onSelectRepo={handleRepoChange}
        authToken={authToken}
        onLogout={handleLogout}
        onRefresh={() => loadUserContext(authToken, selectedRepo)}
        onToggleStep={toggleStep}
        isEmbedded={true}
      />
    </div>
  );
};

export default App;
