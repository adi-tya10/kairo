import React, { useState } from "react";
import { ActiveContext, AnomalyAlert, ActionStep } from "../types";
import { ChatAssistant } from "./ChatAssistant";
import {
  AlertTriangle,
  FileCode2,
  GitPullRequest,
  Check,
  ShieldCheck,
  RefreshCw,
  LogOut,
  Sparkles,
} from "lucide-react";

interface HandoffDrawerProps {
  context: ActiveContext;
  anomalies: AnomalyAlert[];
  checklist: ActionStep[];
  reposList?: string[];
  selectedRepo?: string;
  onSelectRepo?: (repo: string) => void;
  authToken?: string;
  onLogout?: () => void;
  onRefresh?: () => void;
  onToggleStep: (id: number) => void;
  isEmbedded?: boolean;
}

export const HandoffDrawer: React.FC<HandoffDrawerProps> = ({
  context,
  anomalies,
  checklist,
  reposList = [],
  selectedRepo = "",
  onSelectRepo,
  authToken = "",
  onLogout,
  onRefresh,
  onToggleStep,
  isEmbedded = false,
}) => {
  const [activeTab, setActiveTab] = useState<"context" | "anomalies" | "checklist" | "chat">("context");
  const [refreshing, setRefreshing] = useState(false);

  const handleRefreshClick = () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    onRefresh();
    setTimeout(() => setRefreshing(false), 800);
  };

  const renderGroundedSummary = (text?: string) => {
    if (!text) {
      return (
        <span className="text-slate-500 italic">
          No handoff briefing available for the current work context.
        </span>
      );
    }

    const parts = text.split(/(\[[^\]]+\])/g);
    return parts.map((part, index) => {
      if (part.startsWith("[") && part.endsWith("]")) {
        return (
          <span
            key={index}
            className="inline-block mx-0.5 font-mono text-[10px] font-semibold text-indigo-300 bg-indigo-950 px-1.5 py-0.5 rounded border border-indigo-800/40 hover:bg-indigo-900 transition-colors"
          >
            {part}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  const completedCount = checklist.filter((c) => c.completed).length;

  return (
    <div
      className={`flex flex-col flex-1 h-full min-h-0 overflow-hidden animate-fade-in bg-[#0c101d] ${
        isEmbedded ? "" : "glass-panel mt-2 rounded-2xl border border-white/[0.08]"
      }`}
    >
      {/* ── Top Bar / Header ── */}
      <div className="p-3 border-b border-white/[0.08] bg-[#090d16] flex flex-col gap-2 shrink-0">
        <div className="flex items-center justify-between gap-2">
          {/* Task Badge & Title */}
          <div className="flex items-center gap-2 min-w-0">
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 shrink-0">
              {context.taskKey}
            </span>
            <h2 className="text-xs font-display font-semibold text-slate-100 truncate">
              {context.taskTitle}
            </h2>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-1.5 shrink-0 no-drag">
            {/* Repo Switcher */}
            {reposList.length > 1 && onSelectRepo && (
              <select
                value={selectedRepo}
                onChange={(e) => onSelectRepo(e.target.value)}
                className="bg-slate-900/90 border border-white/[0.08] hover:border-white/[0.16] text-[10px] font-mono text-slate-300 rounded-lg px-2 py-1 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
              >
                {reposList.map((r) => (
                  <option key={r} value={r} className="bg-slate-900 text-slate-200">
                    {r.includes("/") ? r.split("/")[1] : r}
                  </option>
                ))}
              </select>
            )}

            {/* Refresh Live Telemetry */}
            {onRefresh && (
              <button
                type="button"
                onClick={handleRefreshClick}
                title="Refresh Live Telemetry"
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-white/[0.06] transition-colors"
              >
                <RefreshCw size={12} className={refreshing ? "animate-spin text-indigo-400" : ""} />
              </button>
            )}

            {/* Sign Out */}
            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                title="Sign out of workspace"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Identity & Scope Breadcrumb */}
        <div className="flex items-center gap-2 text-[11px] text-slate-400 font-sans">
          <span>Org: <strong className="text-slate-200 font-mono font-normal">{context.organization}</strong></span>
          <span className="text-slate-600">•</span>
          <span>Assignee: <strong className="text-indigo-300 font-medium">{context.incomingDev.name}</strong></span>
        </div>
      </div>

      {/* ── Tabs Navigation ── */}
      <div className="flex border-b border-white/[0.08] bg-[#090d16] text-xs font-sans shrink-0">
        <button
          type="button"
          onClick={() => setActiveTab("context")}
          className={`flex-1 py-2.5 text-center font-medium transition-all no-drag ${
            activeTab === "context"
              ? "text-indigo-400 border-b-2 border-indigo-500 bg-[#121829]"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Context
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("anomalies")}
          className={`flex-1 py-2.5 text-center font-medium transition-all flex items-center justify-center gap-1.5 no-drag ${
            activeTab === "anomalies"
              ? "text-amber-400 border-b-2 border-amber-500 bg-[#121829]"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Anomalies</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
              anomalies.length > 0
                ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {anomalies.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("checklist")}
          className={`flex-1 py-2.5 text-center font-medium transition-all flex items-center justify-center gap-1.5 no-drag ${
            activeTab === "checklist"
              ? "text-indigo-400 border-b-2 border-indigo-500 bg-[#121829]"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Checklist</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300">
            {completedCount}/{checklist.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`flex-1 py-2.5 text-center font-medium transition-all flex items-center justify-center gap-1 no-drag ${
            activeTab === "chat"
              ? "text-indigo-400 border-b-2 border-indigo-500 bg-[#121829]"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Sparkles size={11} className={activeTab === "chat" ? "text-indigo-400" : "text-slate-500"} />
          <span>KIAN AI</span>
        </button>
      </div>

      {/* ── Tab Panels ── */}
      <div
        className={`flex-1 text-xs bg-[#0c101d] min-h-0 ${
          activeTab === "chat"
            ? "p-2.5 flex flex-col h-full overflow-hidden"
            : "p-3 overflow-y-auto scrollable"
        }`}
      >
        {/* TAB 1: CONTEXT & BRIEFING */}
        {activeTab === "context" && (
          <div className="space-y-3 animate-fade-in">
            <div className="p-3 rounded-xl bg-[#121829] border border-white/[0.08]">
              <h3 className="font-display font-semibold text-slate-200 mb-2 flex items-center gap-2 text-xs">
                <FileCode2 size={13} className="text-indigo-400" />
                <span>Executive Summary (Grounded)</span>
              </h3>
              <p className="text-slate-300 leading-relaxed text-[11px] font-sans">
                {renderGroundedSummary(context.executiveSummary)}
              </p>
            </div>

            {context.activeArtifacts && context.activeArtifacts.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                  Active Verified Artifacts
                </span>
                {context.activeArtifacts.map((art) => (
                  <div
                    key={art.id}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-[#121829] border border-white/[0.08] hover:border-white/[0.14] transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate min-w-0">
                      <GitPullRequest size={13} className="text-indigo-400 shrink-0" />
                      <span className="truncate text-slate-200 text-[11px] font-mono">
                        {art.title}
                      </span>
                    </div>
                    {art.status && (
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] shrink-0 font-mono font-medium ${
                          art.status.toLowerCase().includes("fail") || art.status.toLowerCase().includes("flag")
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        }`}
                      >
                        {art.status}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: ANOMALIES */}
        {activeTab === "anomalies" && (
          <div className="space-y-2.5 animate-fade-in">
            {anomalies.length === 0 ? (
              <div className="p-6 text-center text-slate-400 bg-[#121829] rounded-xl border border-white/[0.08]">
                <ShieldCheck size={24} className="mx-auto text-emerald-400 mb-2" />
                <p className="font-display font-semibold text-slate-200 text-xs">No active anomalies detected</p>
                <p className="text-[11px] text-slate-500 mt-1">Declared Jira state matches all observed commits & CI signals.</p>
              </div>
            ) : (
              anomalies.map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-xl bg-[#1c1610] border border-amber-500/35 text-amber-200 space-y-2"
                >
                  <div className="flex items-center justify-between font-semibold">
                    <div className="flex items-center gap-1.5 text-xs text-amber-300 font-display">
                      <AlertTriangle size={13} className="shrink-0" />
                      <span>{a.ruleId}: {a.title}</span>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-amber-500/20 rounded-full text-amber-300 border border-amber-500/30">
                      {a.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-amber-200/90 leading-relaxed font-sans">
                    {a.description}
                  </p>
                  <div className="text-[11px] font-sans text-amber-300 bg-[#291f13] p-2 rounded-lg border border-amber-500/25 flex items-start gap-1.5">
                    <span className="font-semibold shrink-0">Action:</span>
                    <span>{a.action}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 3: CHECKLIST */}
        {activeTab === "checklist" && (
          <div className="space-y-2 animate-fade-in">
            {checklist.length === 0 ? (
              <div className="p-6 text-center text-slate-400 bg-[#121829] rounded-xl border border-white/[0.08]">
                <Check size={24} className="mx-auto text-emerald-400 mb-2" />
                <p className="font-display font-semibold text-slate-200 text-xs">Checklist Complete</p>
                <p className="text-[11px] text-slate-500 mt-1">All handoff verification actions have been finalized.</p>
              </div>
            ) : (
              checklist.map((step) => (
                <div
                  key={step.id}
                  onClick={() => onToggleStep(step.id)}
                  className={`p-2.5 rounded-xl border flex items-start gap-3 cursor-pointer transition-all duration-150 no-drag select-none ${
                    step.completed
                      ? "bg-[#0e1c18] border-emerald-500/30 text-slate-400"
                      : "bg-[#121829] border-white/[0.08] text-slate-200 hover:border-white/[0.16]"
                  }`}
                >
                  <div
                    className={`mt-0.5 w-4 h-4 rounded-md flex items-center justify-center border transition-colors shrink-0 ${
                      step.completed
                        ? "bg-emerald-600 border-emerald-500 text-white"
                        : "border-slate-600 bg-[#080c14]"
                    }`}
                  >
                    {step.completed && <Check size={11} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4
                      className={`text-xs font-medium font-sans ${
                        step.completed ? "line-through text-slate-500" : "text-slate-100"
                      }`}
                    >
                      Step {step.id}: {step.title}
                    </h4>
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      {step.description}
                    </p>
                    {step.targetFile && (
                      <span className="inline-block mt-1.5 font-mono text-[10px] text-indigo-300 bg-[#080c14] px-1.5 py-0.5 rounded border border-white/[0.08]">
                        {step.targetFile}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: CHAT */}
        {activeTab === "chat" && (
          <div className="animate-fade-in flex-1 flex flex-col h-full min-h-0">
            <ChatAssistant
              organizationId={context.organization}
              repoId={selectedRepo || `${context.organization}/${context.repo}`}
              authToken={authToken}
              userName={context.incomingDev.name}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default HandoffDrawer;
