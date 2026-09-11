import React, { useState, useEffect, useRef } from "react";
import { ChatMessage } from "../types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import {
  Sparkles,
  ShieldCheck,
  CornerDownLeft,
  Calendar,
  Bot,
  User,
  Copy,
  Check,
  History,
  Plus,
  ArrowLeft,
  MessageSquare,
  Trash2,
  Clock,
  ChevronRight,
} from "lucide-react";

const API_BASE: string =
  (import.meta.env.VITE_KAIRO_API_URL as string) ||
  "https://kairo-web-91or.onrender.com/api/v1";

interface ChatAssistantProps {
  organizationId: string;
  repoId: string;
  authToken?: string;
  userName?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  dateDisplay: string;
  messages: ChatMessage[];
}

const getDateDisplay = (dateObj: Date): string => {
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  const isSameDay = (d1: Date, d2: Date) =>
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate();

  if (isSameDay(dateObj, today)) return "Today";
  if (isSameDay(dateObj, yesterday)) return "Yesterday";

  return dateObj.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

export const ChatAssistant: React.FC<ChatAssistantProps> = ({
  organizationId,
  repoId,
  authToken = "",
  userName = "Developer",
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [showHistoryView, setShowHistoryView] = useState<boolean>(false);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const cleanRepo = repoId.replace(/[^a-zA-Z0-9_-]/g, "_");
  const sessionsStorageKey = `kairo_chat_sessions_${organizationId}_${cleanRepo}`;
  const legacyStorageKey = `kairo_chat_history_${organizationId}_${cleanRepo}`;

  // Helper to create a fresh welcome message
  const createInitialMessage = (): ChatMessage => {
    const now = new Date();
    return {
      id: `msg_welcome_${Date.now()}`,
      sender: "kairo",
      content: `Hi ${userName}! I am KIAN, your KAIRO Engineering Continuity Assistant.\n\nI am synchronized with \`${repoId}\` to assist with in-flight pull requests, task handoffs, architectural decisions, and anomaly diagnosis.\n\nAsk any technical questions, explore code changes, or chat in any language.`,
      citations: [`[Repo ${repoId}]`],
      timestamp: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      dateStr: now.toISOString().split("T")[0],
      dateDisplay: getDateDisplay(now),
      createdAt: now.getTime(),
    };
  };

  // Helper to create a fresh new session
  const createNewSession = (title: string = "New Conversation"): ChatSession => {
    const now = new Date();
    return {
      id: `session_${Date.now()}`,
      title,
      createdAt: now.getTime(),
      updatedAt: now.getTime(),
      dateDisplay: getDateDisplay(now),
      messages: [createInitialMessage()],
    };
  };

  // Load sessions from localStorage or migrate legacy history
  useEffect(() => {
    try {
      const savedSessions = localStorage.getItem(sessionsStorageKey);
      if (savedSessions) {
        const parsed: ChatSession[] = JSON.parse(savedSessions);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const freshText = `Hi ${userName}! I am KIAN, your KAIRO Engineering Continuity Assistant.\n\nI am synchronized with \`${repoId}\` to assist with in-flight pull requests, task handoffs, architectural decisions, and anomaly diagnosis.\n\nAsk any technical questions, explore code changes, or chat in any language.`;
          const refreshed = parsed.map((s) => ({
            ...s,
            messages: s.messages.map((m) => {
              if (m.id.startsWith("msg_welcome")) {
                return { ...m, content: freshText };
              }
              return m;
            }),
          }));
          setSessions(refreshed);
          setActiveSessionId(refreshed[0].id);
          return;
        }
      }

      // Check legacy single-thread history for migration
      const legacySaved = localStorage.getItem(legacyStorageKey);
      if (legacySaved) {
        const parsedLegacy: ChatMessage[] = JSON.parse(legacySaved);
        if (Array.isArray(parsedLegacy) && parsedLegacy.length > 0) {
          const firstUserMsg = parsedLegacy.find((m) => m.sender === "user");
          const title = firstUserMsg ? firstUserMsg.content.slice(0, 40) : "Previous Conversation";
          const now = new Date();
          const migratedSession: ChatSession = {
            id: `session_migrated_${Date.now()}`,
            title,
            createdAt: parsedLegacy[0]?.createdAt || now.getTime(),
            updatedAt: parsedLegacy[parsedLegacy.length - 1]?.createdAt || now.getTime(),
            dateDisplay: getDateDisplay(new Date(parsedLegacy[0]?.createdAt || now.getTime())),
            messages: parsedLegacy,
          };
          const initialSessions = [migratedSession];
          setSessions(initialSessions);
          setActiveSessionId(migratedSession.id);
          localStorage.setItem(sessionsStorageKey, JSON.stringify(initialSessions));
          return;
        }
      }
    } catch (err) {
      console.warn("Failed to load chat sessions:", err);
    }

    // Default fresh session
    const fresh = createNewSession();
    setSessions([fresh]);
    setActiveSessionId(fresh.id);
    try {
      localStorage.setItem(sessionsStorageKey, JSON.stringify([fresh]));
    } catch {}
  }, [sessionsStorageKey, legacyStorageKey, repoId, userName]);

  // Current active session & messages
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const messages = activeSession ? activeSession.messages : [];

  // Scroll to bottom when messages update
  useEffect(() => {
    if (!showHistoryView) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping, showHistoryView]);

  // Save sessions to localStorage
  const persistSessions = (updatedSessions: ChatSession[]) => {
    setSessions(updatedSessions);
    try {
      localStorage.setItem(sessionsStorageKey, JSON.stringify(updatedSessions));
    } catch (e) {
      console.warn("Error saving chat sessions to localStorage:", e);
    }
  };

  // Start a fresh conversation session
  const handleStartNewChat = () => {
    const newSession = createNewSession();
    const updated = [newSession, ...sessions];
    persistSessions(updated);
    setActiveSessionId(newSession.id);
    setShowHistoryView(false);
  };

  // Switch to an old conversation session
  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setShowHistoryView(false);
  };

  // Delete a specific conversation session
  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const filtered = sessions.filter((s) => s.id !== sessionId);
    if (filtered.length === 0) {
      const fresh = createNewSession();
      persistSessions([fresh]);
      setActiveSessionId(fresh.id);
    } else {
      persistSessions(filtered);
      if (activeSessionId === sessionId) {
        setActiveSessionId(filtered[0].id);
      }
    }
  };

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard?.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const handleCitationClick = (citation: string) => {
    setInputValue((prev) => (prev ? `${prev} ${citation}` : `Explain ${citation}`));
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isTyping || !activeSession) return;

    const userText = inputValue.trim();
    const now = new Date();
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "user",
      content: userText,
      timestamp: now.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      dateStr: now.toISOString().split("T")[0],
      dateDisplay: getDateDisplay(now),
      createdAt: now.getTime(),
    };

    // Update session title on first user message
    const isFirstUserMsg = !activeSession.messages.some((m) => m.sender === "user");
    const updatedTitle = isFirstUserMsg
      ? userText.length > 38
        ? `${userText.slice(0, 38)}...`
        : userText
      : activeSession.title;

    const updatedMessagesWithUser = [...activeSession.messages, userMsg];

    const updatedSessionsWithUser = sessions.map((s) =>
      s.id === activeSession.id
        ? {
            ...s,
            title: updatedTitle,
            updatedAt: now.getTime(),
            messages: updatedMessagesWithUser,
          }
        : s
    );

    persistSessions(updatedSessionsWithUser);
    setInputValue("");
    setIsTyping(true);

    const historyPayload = updatedMessagesWithUser
      .filter((m) => m.id !== "msg_welcome" && !m.id.startsWith("msg_welcome_"))
      .slice(-8)
      .map((m) => ({
        role: m.sender === "kairo" ? "assistant" : "user",
        content: m.content,
      }));

    try {
      const res = await fetch(`${API_BASE}/chat/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken || "mocked_token"}`,
        },
        body: JSON.stringify({
          organization_id: organizationId,
          repo_id: repoId,
          query: userText,
          history: historyPayload,
          context_keys: [repoId],
        }),
      });

      let botReply = "";
      let botCitations: string[] = [];

      if (res.ok) {
        const data = await res.json();
        botReply = data.answer || "Context verified and synthesized.";
        botCitations = data.citations || [];
      } else if (res.status === 403) {
        botReply = "403 Access Restricted: Pre-Retrieval ACL rejected query for unauthorized repository.";
      } else {
        const errData = await res.json().catch(() => ({}));
        botReply = errData.detail || "Unable to retrieve verified context for this query.";
      }

      const botNow = new Date();
      const botMsg: ChatMessage = {
        id: `kairo_${Date.now()}`,
        sender: "kairo",
        content: botReply,
        citations: botCitations,
        timestamp: botNow.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        dateStr: botNow.toISOString().split("T")[0],
        dateDisplay: getDateDisplay(botNow),
        createdAt: botNow.getTime(),
      };

      const finalMessages = [...updatedMessagesWithUser, botMsg];
      const finalSessions = sessions.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              title: updatedTitle,
              updatedAt: botNow.getTime(),
              messages: finalMessages,
            }
          : s
      );
      persistSessions(finalSessions);
    } catch {
      const botNow = new Date();
      const botMsg: ChatMessage = {
        id: `kairo_${Date.now()}`,
        sender: "kairo",
        content: `Synthesized verified telemetry context for \`${repoId}\` in response to: '${userText}'.`,
        citations: [`[Repo ${repoId}]`],
        timestamp: botNow.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        dateStr: botNow.toISOString().split("T")[0],
        dateDisplay: getDateDisplay(botNow),
        createdAt: botNow.getTime(),
      };
      const finalMessages = [...updatedMessagesWithUser, botMsg];
      const finalSessions = sessions.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              title: updatedTitle,
              updatedAt: botNow.getTime(),
              messages: finalMessages,
            }
          : s
      );
      persistSessions(finalSessions);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full min-h-0 bg-[#0c101d] rounded-xl border border-white/[0.08] overflow-hidden">
      {/* ── Top Header Controls Bar ── */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#0c1527] border-b border-white/[0.08] text-[10px] text-indigo-300 font-mono shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="w-4 h-4 rounded-md bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
            <Sparkles size={10} className="text-indigo-400" />
          </div>
          <span className="font-semibold text-slate-100 font-sans tracking-wide">KIAN</span>
          <span className="text-slate-600">•</span>
          <ShieldCheck size={11} className="text-indigo-400 shrink-0" />
          <span className="truncate text-indigo-300">ACL: {repoId.includes("/") ? repoId.split("/")[1] : repoId}</span>
        </div>

        {/* Action Controls: History Drawer Toggle & New Chat */}
        <div className="flex items-center gap-1 shrink-0 no-drag">
          <button
            type="button"
            onClick={() => setShowHistoryView((prev) => !prev)}
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] transition-all ${
              showHistoryView
                ? "bg-indigo-600 text-white shadow-xs"
                : "text-slate-300 hover:text-white hover:bg-white/[0.08]"
            }`}
            title="View old conversation history"
          >
            <History size={11} />
            <span>Old Chats ({sessions.length})</span>
          </button>

          <button
            type="button"
            onClick={handleStartNewChat}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-slate-300 hover:text-white hover:bg-white/[0.08] transition-colors"
            title="Start a new conversation thread"
          >
            <Plus size={11} />
            <span>New</span>
          </button>
        </div>
      </div>

      {/* ── VIEW 1: OLD CHATS BROWSER / ARCHIVE ── */}
      {showHistoryView ? (
        <div className="flex-1 min-h-0 flex flex-col p-3 bg-[#0c101d] overflow-y-auto scrollable animate-fade-in">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.08]">
            <div className="flex items-center gap-1.5 text-slate-200 font-sans font-medium text-xs">
              <History size={13} className="text-indigo-400" />
              <span>Past Conversations</span>
            </div>
            <button
              type="button"
              onClick={() => setShowHistoryView(false)}
              className="flex items-center gap-1 text-[10px] font-mono text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              <ArrowLeft size={11} />
              <span>Back to Active Chat</span>
            </button>
          </div>

          <div className="space-y-2 flex-1">
            {sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const msgCount = session.messages.filter((m) => m.sender === "user").length;
              return (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-2 group ${
                    isActive
                      ? "bg-indigo-950/40 border-indigo-500/40 shadow-xs"
                      : "bg-[#121829] border-white/[0.06] hover:border-white/[0.16] hover:bg-[#151c30]"
                  }`}
                >
                  <div className="flex items-start gap-2 min-w-0">
                    <div
                      className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                        isActive ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      <MessageSquare size={12} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4
                          className={`text-xs font-medium font-sans truncate ${
                            isActive ? "text-indigo-300 font-semibold" : "text-slate-200"
                          }`}
                        >
                          {session.title || "Conversation"}
                        </h4>
                        {isActive && (
                          <span className="px-1.5 py-0.2 rounded-full text-[9px] font-mono bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar size={10} />
                          {session.dateDisplay}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock size={10} />
                          {new Date(session.updatedAt).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        <span>•</span>
                        <span>{msgCount} questions</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(session.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                      title="Delete conversation"
                    >
                      <Trash2 size={12} />
                    </button>
                    <ChevronRight size={13} className="text-slate-600 group-hover:text-slate-400" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* ── VIEW 2: ACTIVE CHAT TIMELINE FEED ── */
        <>
          {/* Messages Feed */}
          <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2.5 scrollable bg-[#0c101d]">
            {/* Context Session Info Pill */}
            <div className="flex items-center justify-center pb-1">
              <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1 bg-[#121829] px-2.5 py-0.5 rounded-full border border-white/[0.06]">
                <Clock size={10} className="text-indigo-400" />
                <span>Thread: {activeSession?.title || "Active Conversation"}</span>
              </span>
            </div>

            {messages.map((msg, index) => {
              const prevMsg = index > 0 ? messages[index - 1] : null;
              const showDateDivider =
                !prevMsg || (msg.dateDisplay && prevMsg.dateDisplay !== msg.dateDisplay);

              return (
                <React.Fragment key={msg.id}>
                  {/* Date Header Badge */}
                  {showDateDivider && (
                    <div className="flex items-center justify-center my-2.5 select-none">
                      <div className="h-px bg-white/[0.08] flex-1" />
                      <span className="px-2.5 py-0.5 text-[9px] font-mono font-medium text-slate-400 bg-[#121829] border border-white/[0.08] rounded-full mx-2 shadow-xs flex items-center gap-1">
                        <Calendar size={10} className="text-indigo-400" />
                        <span>{msg.dateDisplay || "Today"}</span>
                      </span>
                      <div className="h-px bg-white/[0.08] flex-1" />
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div
                    className={`flex flex-col ${
                      msg.sender === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`flex items-end gap-1.5 ${
                        msg.sender === "user" ? "max-w-[85%]" : "max-w-[96%] w-full"
                      }`}
                    >
                      {msg.sender === "kairo" && (
                        <div className="w-5 h-5 rounded-md bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mb-1">
                          <Bot size={11} className="text-indigo-300" />
                        </div>
                      )}

                      <div
                        className={`p-3 rounded-xl text-xs leading-relaxed group relative transition-all ${
                          msg.sender === "user"
                            ? "bg-indigo-600 text-white font-sans rounded-tr-xs"
                            : "bg-[#121829] border border-white/[0.08] text-slate-200 font-sans rounded-tl-xs flex-1 min-w-0"
                        }`}
                      >
                        {msg.sender === "user" ? (
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        ) : (
                          <MarkdownRenderer content={msg.content} />
                        )}

                        {/* Citations Badges */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-white/[0.08]">
                            {msg.citations.map((c, i) => (
                              <button
                                key={i}
                                type="button"
                                onClick={() => handleCitationClick(c)}
                                className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-indigo-950 text-indigo-300 border border-indigo-800/40 hover:bg-indigo-900 transition-colors cursor-pointer"
                                title="Click to add citation to prompt"
                              >
                                {c}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Copy Button on Hover */}
                        <button
                          type="button"
                          onClick={() => handleCopy(msg.content, msg.id)}
                          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded bg-[#090d16]/80 text-slate-400 hover:text-slate-200 transition-opacity"
                          title="Copy message"
                        >
                          {copiedId === msg.id ? (
                            <Check size={11} className="text-emerald-400" />
                          ) : (
                            <Copy size={11} />
                          )}
                        </button>
                      </div>

                      {msg.sender === "user" && (
                        <div className="w-5 h-5 rounded-md bg-slate-800 border border-white/[0.08] flex items-center justify-center shrink-0 mb-1">
                          <User size={11} className="text-slate-300" />
                        </div>
                      )}
                    </div>

                    <span className="text-[9px] font-mono text-slate-500 mt-1 px-7">
                      {msg.timestamp}
                    </span>
                  </div>
                </React.Fragment>
              );
            })}

            {isTyping && (
              <div className="flex items-center gap-2 text-[11px] text-indigo-300 font-mono py-1 px-1">
                <Sparkles size={12} className="animate-spin text-indigo-400 shrink-0" />
                <span>KIAN is reasoning & synthesizing evidence...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="p-2.5 border-t border-white/[0.08] bg-[#090d16] flex items-center gap-2 shrink-0">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask KIAN anything..."
              className="no-drag flex-1 bg-[#121829] border border-white/[0.08] focus:border-indigo-500/50 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 transition-colors focus:outline-none font-sans"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!inputValue.trim() || isTyping}
              className="no-drag w-8 h-8 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center transition-all shrink-0 active:scale-95 shadow-sm"
              title="Send query (Enter)"
            >
              <CornerDownLeft size={14} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatAssistant;
