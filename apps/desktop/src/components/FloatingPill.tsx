import React from "react";
import { ActiveContext } from "../types";
import { ChevronDown, ShieldAlert, GripVertical, Minimize2 } from "lucide-react";

interface FloatingPillProps {
  context: ActiveContext;
  hasAnomalies: boolean;
  isOpen: boolean;
  onToggle: () => void;
  isEmbedded?: boolean;
}

export const FloatingPill: React.FC<FloatingPillProps> = ({
  context,
  hasAnomalies,
  isOpen,
  onToggle,
  isEmbedded = false,
}) => {
  return (
    <div
      className={`w-full flex items-center justify-between pl-2 pr-3 py-2.5 select-none transition-all duration-150 ${
        isEmbedded
          ? `bg-[#0c101d] ${isOpen ? "border-b border-white/[0.08]" : ""}`
          : `glass-pill rounded-2xl ${
              isOpen ? "border-indigo-500/40 bg-[#0c101d]" : "hover:border-white/[0.14] bg-[#0c101d]"
            }`
      }`}
    >
      {/* Dedicated Drag Handle */}
      <div
        data-tauri-drag-region
        className="drag-region flex items-center justify-center px-1.5 py-1 text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing transition-colors"
        title="Drag HUD to move"
      >
        <GripVertical size={14} />
      </div>

      {/* Main Clickable Area to Toggle */}
      <div
        onClick={onToggle}
        className="no-drag flex-1 flex items-center gap-2.5 min-w-0 cursor-pointer px-1"
      >
        {/* Brand Icon with Status Ring */}
        <div className="relative flex items-center justify-center shrink-0">
          <img
            src="/kairo.png"
            alt="KAIRO"
            className="w-5 h-5 object-contain"
          />
          <span
            className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-[#0c101d] ${
              hasAnomalies ? "bg-amber-400" : "bg-emerald-400"
            }`}
          />
        </div>

        {/* Text Details */}
        <div className="flex flex-col text-left truncate min-w-0">
          {/* Org & Repo Path */}
          <div className="flex items-center gap-1 font-mono text-[11px] leading-tight text-slate-400 truncate">
            <span className="text-slate-300 font-medium">{context.organization}</span>
            <span className="text-slate-600">/</span>
            <span className="text-slate-200 font-medium truncate">{context.repo}</span>
            <span className="text-slate-500 ml-1 font-sans text-[10px]">({context.branch})</span>
          </div>

          {/* Task Key & Title */}
          <div className="flex items-center gap-1.5 text-xs truncate mt-0.5">
            <span className="font-mono font-semibold text-indigo-400 shrink-0">
              {context.taskKey}
            </span>
            <span className="text-slate-300 truncate font-normal">
              {context.taskTitle}
            </span>
          </div>
        </div>
      </div>

      {/* Right Side: Alerts Badge & Toggle Button */}
      <div className="no-drag flex items-center gap-2 pl-2 shrink-0">
        {hasAnomalies && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 animate-pulse">
            <ShieldAlert size={11} />
            Anomaly
          </span>
        )}

        <button
          type="button"
          onClick={onToggle}
          className="w-6 h-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-indigo-400 hover:bg-white/[0.06] transition-all"
          title={isOpen ? "Minimize to Logo Icon (Ctrl+Space)" : "Expand HUD (Ctrl+Space)"}
        >
          {isOpen ? (
            <Minimize2 size={13} />
          ) : (
            <ChevronDown size={14} />
          )}
        </button>
      </div>
    </div>
  );
};

export default FloatingPill;
