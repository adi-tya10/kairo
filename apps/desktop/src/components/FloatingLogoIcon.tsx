import React from "react";
import { ActiveContext } from "../types";
import { GripVertical, Maximize2, ShieldAlert } from "lucide-react";

interface FloatingLogoIconProps {
  context: ActiveContext;
  hasAnomalies: boolean;
  onExpand: () => void;
}

export const FloatingLogoIcon: React.FC<FloatingLogoIconProps> = ({
  context,
  hasAnomalies,
  onExpand,
}) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#0c101d",
        borderRadius: "16px",
        border: "1px solid rgba(255, 255, 255, 0.12)",
      }}
      className="flex items-center justify-between px-2.5 py-1.5 select-none animate-fade-in font-sans overflow-hidden"
    >
      {/* Drag Handle */}
      <div
        data-tauri-drag-region
        className="drag-region flex items-center justify-center p-1 text-slate-500 hover:text-slate-300 cursor-grab active:cursor-grabbing transition-colors"
        title="Drag HUD"
      >
        <GripVertical size={14} />
      </div>

      {/* Clickable Logo & Status to Expand */}
      <div
        onClick={onExpand}
        className="no-drag flex-1 flex items-center gap-2 cursor-pointer px-1.5 min-w-0"
        title="Click to open KAIRO Boxcard (Ctrl+Space)"
      >
        {/* Logo Emblem with Live Status Glow */}
        <div className="relative flex items-center justify-center shrink-0">
          <img src="/kairo.png" alt="KAIRO" className="w-6 h-6 object-contain" />
          <span
            className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full ring-2 ring-[#0c101d] ${
              hasAnomalies ? "bg-amber-400 animate-pulse" : "bg-emerald-400"
            }`}
          />
        </div>

        {/* Task key / Status */}
        <div className="flex flex-col text-left truncate min-w-0">
          <span className="font-display font-bold text-xs text-slate-100 leading-none tracking-tight">
            KAIRO
          </span>
          <span className="font-mono text-[10px] text-indigo-400 font-medium truncate mt-0.5">
            {context.taskKey || "ACTIVE"}
          </span>
        </div>
      </div>

      {/* Expand Action & Anomaly Badge */}
      <div className="no-drag flex items-center gap-1 shrink-0">
        {hasAnomalies && (
          <span
            className="w-5 h-5 rounded-full flex items-center justify-center bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px]"
            title="Anomaly Detected"
          >
            <ShieldAlert size={12} />
          </span>
        )}
        <button
          type="button"
          onClick={onExpand}
          className="w-6 h-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-indigo-400 hover:bg-white/[0.06] transition-all"
          title="Expand HUD (Ctrl+Space)"
        >
          <Maximize2 size={12} />
        </button>
      </div>
    </div>
  );
};

export default FloatingLogoIcon;
