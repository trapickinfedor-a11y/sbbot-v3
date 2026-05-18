/* ═══════════════════════════════════════════════════════
   ChatsTab — Buyer-Seller messaging
   Obsidian Glass design
   ═══════════════════════════════════════════════════════ */

import { useState, useRef, useEffect, useCallback } from "react";
import { cn, fmtTime, fmtStatus, statusBg, truncate } from "@/lib/utils";
import { useApp } from "@/contexts/AppContext";
import { api, apiFetch, type ChatMessage, type MessagesPayload } from "@/lib/api";
import { MOCK_MESSAGES } from "@/lib/mockData";
import { haptic } from "@/lib/telegram";
import { toast } from "sonner";
import { Search, ChevronLeft, Paperclip, Send, X, MessageSquare, AlertTriangle } from "lucide-react";

export default function ChatsTab() {
  const { conversations, refreshConversations, isDemoMode } = useApp();
  const [search, setSearch] = useState("");
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [payload, setPayload] = useState<MessagesPayload | null>(null);
  const [loadingChat, setLoadingChat] = useState(false);
  const [mobileView, setMobileView] = useState<"list" | "chat">("list");
  const [messageText, setMessageText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const filtered = search
    ? conversations.filter(
        (c) =>
          (c.product_label ?? "").toLowerCase().includes(search.toLowerCase()) ||
          (c.buyer_label ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : conversations;

  // Position of the active conversation in the filtered list (1-based)
  const activePosition = activeConvId
    ? filtered.findIndex((c) => c.id === activeConvId) + 1
    : 0;

  const openConversation = useCallback(async (id: number) => {
    setActiveConvId(id);
    setMobileView("chat");
    setLoadingChat(true);
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 300));
        setPayload(MOCK_MESSAGES);
      } else {
        const data = await api.messages(id);
        setPayload(data);
      }
    } catch {
      setPayload(MOCK_MESSAGES);
    } finally {
      setLoadingChat(false);
    }
  }, [isDemoMode]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [payload]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeConvId || (!messageText.trim() && !file)) return;
    setSending(true);
    haptic("light");

    if (isDemoMode) {
      await new Promise((r) => setTimeout(r, 400));
      const newMsg: ChatMessage = {
        id: Date.now(),
        sender_type: "seller",
        message_text: messageText.trim() || "[File attached]",
        created_at: new Date().toISOString(),
      };
      setPayload((prev) => prev ? { ...prev, messages: [...prev.messages, newMsg] } : prev);
      setMessageText("");
      setFile(null);
      setSending(false);
      return;
    }

    const fd = new FormData();
    fd.append("conversation_id", String(activeConvId));
    if (messageText.trim()) fd.append("message_text", messageText.trim());
    if (file) fd.append("file", file);
    try {
      await api.send(fd);
      setMessageText("");
      setFile(null);
      await openConversation(activeConvId);
      await refreshConversations();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  const handleOpenDispute = async () => {
    if (!payload?.conversation.latest_order_id) return;
    haptic("medium");
    if (isDemoMode) {
      toast.info("Dispute functionality available in Orders tab");
      return;
    }
    try {
      await apiFetch<void>(`/orders/${payload.conversation.latest_order_id}/dispute/open`, {
        method: "POST",
        json: { reason: "Opened from chat" },
      });
      toast.success("Dispute opened — check the Orders tab");
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessageText(e.target.value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  };

  return (
    <div className="flex h-full">
      {/* ── Sidebar ── */}
      <div
        className={cn(
          "flex flex-col border-r border-white/[0.06]",
          "w-full md:w-[280px] md:flex-shrink-0",
          mobileView === "chat" ? "hidden md:flex" : "flex"
        )}
      >
        {/* Search */}
        <div className="px-3 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2 bg-white/[0.05] rounded-xl px-3 py-2.5">
            <Search className="w-4 h-4 text-zinc-500 flex-shrink-0" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats…"
              className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-600 outline-none"
            />
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2 text-zinc-600">
              <MessageSquare className="w-8 h-8 opacity-40" />
              <span className="text-sm">No chats yet</span>
            </div>
          ) : (
            filtered.map((c, index) => (
              <button
                key={c.id}
                onClick={() => openConversation(c.id)}
                className={cn(
                  "w-full text-left px-3 py-3 mx-1 rounded-xl transition-all duration-150 relative",
                  "hover:bg-white/[0.04]",
                  activeConvId === c.id
                    ? "bg-blue-500/10 border border-blue-500/20"
                    : "border border-transparent"
                )}
                style={{ width: "calc(100% - 8px)" }}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="font-semibold text-[13px] text-white truncate">
                    {c.product_label || c.buyer_label || "Buyer chat"}
                  </span>
                  <span className="text-[11px] text-zinc-600 flex-shrink-0">
                    {fmtTime(c.latest_message_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] text-zinc-500 truncate">
                    {truncate(c.latest_message ?? "—", 40)}
                  </span>
                  {c.unread_count > 0 && (
                    <span className="min-w-[20px] h-5 rounded-full bg-blue-500 text-white text-[10px] font-bold flex items-center justify-center px-1.5 flex-shrink-0">
                      {c.unread_count}
                    </span>
                  )}
                </div>
                {c.latest_order_status && (
                  <span className={cn("mt-1.5 inline-block text-[10px] px-2 py-0.5 rounded-full font-medium", statusBg(c.latest_order_status))}>
                    {fmtStatus(c.latest_order_status)}
                  </span>
                )}
                {c.latest_order_id && (
                  <div className="mt-1 flex items-center gap-1.5">
                    <span className="text-[10px] text-zinc-500 font-medium">
                      #{c.latest_order_id}
                    </span>
                    <span className="text-[10px] text-zinc-600">·</span>
                    <span className="text-[10px] text-zinc-600">
                      pos {index + 1}/{filtered.length}
                    </span>
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Chat view ── */}
      <div
        className={cn(
          "flex-1 flex flex-col min-w-0",
          mobileView === "list" ? "hidden md:flex" : "flex"
        )}
      >
        {!payload ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-zinc-600">
            <MessageSquare className="w-14 h-14 opacity-20" />
            <span className="text-sm">
              {loadingChat ? "Loading…" : "Select a chat"}
            </span>
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06] bg-[oklch(0.09_0.012_260/0.9)] flex-shrink-0">
              <button
                onClick={() => setMobileView("list")}
                className="md:hidden text-blue-400 p-1 -ml-1"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-[15px] text-white truncate">
                    {payload.conversation.buyer_label || "Buyer chat"}
                  </span>
                  {activePosition > 0 && filtered.length > 0 && (
                    <span className="text-[10px] text-zinc-600 flex-shrink-0">
                      Chat {activePosition} of {filtered.length}
                    </span>
                  )}
                </div>
                {payload.conversation.latest_order_status && (
                  <div className="text-[11px] text-zinc-500 mt-0.5">
                    Order #{payload.conversation.latest_order_id} ·{" "}
                    <span className={cn(statusBg(payload.conversation.latest_order_status), "px-1.5 py-0.5 rounded text-[10px]")}>
                      {fmtStatus(payload.conversation.latest_order_status)}
                    </span>
                  </div>
                )}
              </div>
              {/* Dispute button */}
              {payload.conversation.latest_order_id &&
                payload.conversation.latest_order_status !== "completed" && (
                  <button
                    type="button"
                    onClick={handleOpenDispute}
                    className="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/[0.08] border border-rose-500/20 text-rose-400 text-[11px] font-medium"
                  >
                    <AlertTriangle className="w-3 h-3" />
                    Dispute
                  </button>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-2.5">
              {payload.messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Send form */}
            <form
              onSubmit={handleSend}
              className="flex-shrink-0 px-3 pb-3 pt-2 border-t border-white/[0.06] bg-[oklch(0.09_0.012_260/0.95)]"
            >
              {file && (
                <div className="flex items-center gap-2 mb-2 px-3 py-1.5 bg-white/[0.05] rounded-lg text-sm text-zinc-300">
                  <Paperclip className="w-3.5 h-3.5 text-blue-400" />
                  <span className="flex-1 truncate text-[12px]">{file.name}</span>
                  <button type="button" onClick={() => setFile(null)}>
                    <X className="w-3.5 h-3.5 text-zinc-500" />
                  </button>
                </div>
              )}
              <div className="flex items-end gap-2 bg-white/[0.05] rounded-2xl px-3 py-2">
                <label className="flex-shrink-0 cursor-pointer text-zinc-500 hover:text-blue-400 transition-colors self-end pb-0.5">
                  <Paperclip className="w-5 h-5" />
                  <input
                    type="file"
                    accept=".txt,.pdf,.zip,.csv,.json"
                    hidden
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <textarea
                  ref={textareaRef}
                  value={messageText}
                  onChange={autoResize}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend(e as unknown as React.FormEvent);
                    }
                  }}
                  placeholder="Message…"
                  rows={1}
                  className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-600 outline-none resize-none max-h-[120px] leading-relaxed"
                />
                <button
                  type="submit"
                  disabled={sending || (!messageText.trim() && !file)}
                  className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white disabled:opacity-40 transition-all hover:bg-blue-400 self-end"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isBuyer = message.sender_type === "buyer";
  const isSystem = message.sender_type === "system";

  if (isSystem) {
    return (
      <div className="self-center text-[11px] text-zinc-600 bg-white/[0.03] px-3 py-1.5 rounded-full text-center max-w-[80%]">
        {message.message_text}
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col max-w-[80%]", isBuyer ? "self-start" : "self-end items-end")}>
      <div className="text-[10px] text-zinc-600 mb-1 px-1">
        {isBuyer ? "Buyer" : "You"} · {fmtTime(message.created_at)}
      </div>
      <div
        className={cn(
          "px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed",
          isBuyer
            ? "bg-white/[0.06] text-white rounded-tl-sm"
            : "bg-blue-500/20 text-white border border-blue-500/20 rounded-tr-sm"
        )}
      >
        {message.message_text}
        {message.files && message.files.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5 text-blue-400 text-[12px]">
            <Paperclip className="w-3.5 h-3.5" />
            <span>File attached</span>
          </div>
        )}
      </div>
    </div>
  );
}
