/* ═══════════════════════════════════════════════════════
   OrdersTab — Order management + Dispute UI
   Obsidian Glass design

   Tab description: Approved goods warehouse + full history.
   Active orders are your inventory in progress.

   DISPUTE FLOW (seller side):
   1. Seller opens dispute on a completed order (within window)
   2. OR buyer opens dispute → seller sees it and can respond
   3. Seller can: Accept (refund) / Respond with evidence / Escalate to admin

   BADGE NOTE: Badge count is already correct — AppContext's
   refreshOrdersCount uses the "active" filter, so the badge
   only reflects active orders (approved + in_progress), not
   the full order history.
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect } from "react";
import { cn, fmtMoney, fmtDateTime, fmtStatus, statusBg, truncate } from "@/lib/utils";
import { apiFetch, type Order } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import {
  Package, AlertTriangle, CheckCircle, Clock, ChevronLeft,
  ChevronDown, ChevronUp, MessageSquare, Shield, Send,
  X, Info, Flag, Warehouse,
} from "lucide-react";

/* ─── Types ───────────────────────────────────────────── */

// "Done" renamed to "History" to better reflect it's the order history/archive
type Filter = "active" | "all" | "completed" | "disputed";

interface DisputeMessage {
  id: number;
  sender: "buyer" | "seller" | "admin";
  text: string;
  created_at: string;
  attachments?: string[];
}

interface DisputeDetail {
  id: number;
  order_id: number;
  reason: string;
  status: "open" | "seller_responded" | "escalated" | "resolved_seller" | "resolved_buyer";
  opened_by: "buyer" | "seller";
  opened_at: string;
  messages: DisputeMessage[];
  buyer_evidence?: string;
  resolution?: string;
}


const FILTERS: { id: Filter; label: string }[] = [
  { id: "active",    label: "Active" },
  { id: "all",       label: "All" },
  { id: "completed", label: "History" }, // was "Done" — renamed to "History" (order archive)
  { id: "disputed",  label: "Disputed" },
];

/* ─── Helpers ─────────────────────────────────────────── */

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 2) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/* ─── Dispute Screen ──────────────────────────────────── */

function DisputeScreen({
  order,
  onBack,
}: {
  order: Order;
  onBack: () => void;
}) {
  const { isDemoMode } = useApp();
  const [dispute, setDispute] = useState<DisputeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [openingNew, setOpeningNew] = useState(false);
  const [newReason, setNewReason] = useState("");
  const [showOpenForm, setShowOpenForm] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (isDemoMode) {
          await new Promise(r => setTimeout(r, 300));
          setDispute(null);
        } else {
          const d = await apiFetch<DisputeDetail>(`/orders/${order.id}/dispute`);
          setDispute(d);
        }
      } catch (e) { toast.error((e as Error).message); setDispute(null); }
      finally { setLoading(false); }
    };
    load();
  }, [order.id, isDemoMode]);

  const sendReply = async () => {
    if (!replyText.trim()) return;
    setSending(true);
    try {
      if (!isDemoMode) {
        await apiFetch(`/orders/${order.id}/dispute/reply`, {
          method: "POST", json: { text: replyText },
        });
      }
      const newMsg: DisputeMessage = {
        id: Date.now(), sender: "seller", text: replyText,
        created_at: new Date().toISOString(),
      };
      setDispute(d => d ? { ...d, messages: [...d.messages, newMsg], status: "seller_responded" } : d);
      setReplyText("");
      toast.success("Response sent");
    } catch (e) { toast.error((e as Error).message); }
    finally { setSending(false); }
  };

  const acceptDispute = async () => {
    if (!confirm("Accept dispute and issue refund to buyer?")) return;
    setAccepting(true);
    try {
      if (!isDemoMode) {
        await apiFetch(`/orders/${order.id}/dispute/accept`, { method: "POST" });
      }
      setDispute(d => d ? { ...d, status: "resolved_buyer" } : d);
      toast.success("Dispute accepted — refund issued");
    } catch (e) { toast.error((e as Error).message); }
    finally { setAccepting(false); }
  };

  const escalateDispute = async () => {
    if (!confirm("Escalate to admin for manual review?")) return;
    setEscalating(true);
    try {
      if (!isDemoMode) {
        await apiFetch(`/orders/${order.id}/dispute/escalate`, { method: "POST" });
      }
      setDispute(d => d ? { ...d, status: "escalated" } : d);
      toast.success("Escalated to admin — you will be notified via bot");
    } catch (e) { toast.error((e as Error).message); }
    finally { setEscalating(false); }
  };

  const openNewDispute = async () => {
    if (!newReason.trim()) { toast.error("Describe the issue"); return; }
    setOpeningNew(true);
    try {
      if (!isDemoMode) {
        await apiFetch(`/orders/${order.id}/dispute/open`, {
          method: "POST", json: { reason: newReason },
        });
      }
      const newDispute: DisputeDetail = {
        id: Date.now(), order_id: order.id, reason: newReason,
        status: "open", opened_by: "seller",
        opened_at: new Date().toISOString(),
        messages: [{ id: 1, sender: "seller", text: newReason, created_at: new Date().toISOString() }],
      };
      setDispute(newDispute);
      setShowOpenForm(false);
      setNewReason("");
      toast.success("Dispute opened — admin notified");
    } catch (e) { toast.error((e as Error).message); }
    finally { setOpeningNew(false); }
  };

  const statusLabel: Record<string, { label: string; color: string }> = {
    open:              { label: "Open",           color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
    seller_responded:  { label: "Responded",      color: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
    escalated:         { label: "Escalated",      color: "text-violet-400 bg-violet-500/10 border-violet-500/20" },
    resolved_seller:   { label: "Resolved ✓",     color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
    resolved_buyer:    { label: "Refunded",        color: "text-rose-400 bg-rose-500/10 border-rose-500/20" },
  };

  return (
    <div className="flex flex-col gap-4 px-4 pt-4 pb-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onBack}
          className="w-8 h-8 rounded-xl bg-white/[0.05] flex items-center justify-center hover:bg-white/[0.10] transition-colors">
          <ChevronLeft className="w-4 h-4 text-zinc-400" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-[14px] font-bold text-white">
            Dispute — Order #{order.id}
          </div>
          <div className="text-[11px] text-zinc-600 truncate">
            {truncate(order.bank_name ?? order.product_type ?? "", 30)}
          </div>
        </div>
        {dispute && (
          <span className={cn("text-[10px] px-2 py-1 rounded-full border font-semibold",
            statusLabel[dispute.status]?.color ?? "text-zinc-500 bg-zinc-800 border-zinc-700")}>
            {statusLabel[dispute.status]?.label ?? dispute.status}
          </span>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-6 h-6 border-2 border-rose-500/30 border-t-rose-500 rounded-full animate-spin" />
        </div>
      ) : dispute ? (
        <>
          {/* Dispute info */}
          <div className="bg-rose-500/[0.07] border border-rose-500/20 rounded-2xl p-3.5 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span className="text-[12px] font-semibold text-rose-300">
                {dispute.opened_by === "buyer" ? "Buyer opened dispute" : "You opened dispute"}
              </span>
              <span className="text-[10px] text-zinc-700 ml-auto">{timeAgo(dispute.opened_at)}</span>
            </div>
            <p className="text-[12px] text-zinc-400 leading-relaxed">{dispute.reason}</p>
            {dispute.buyer_evidence && (
              <div className="mt-1 pt-2 border-t border-rose-500/10">
                <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-1">Buyer Evidence</div>
                <p className="text-[12px] text-zinc-500 leading-relaxed">{dispute.buyer_evidence}</p>
              </div>
            )}
          </div>

          {/* Messages thread */}
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">Messages</div>
            {dispute.messages.map(msg => (
              <div key={msg.id}
                className={cn("flex gap-2.5", msg.sender === "seller" ? "flex-row-reverse" : "flex-row")}>
                {/* Avatar */}
                <div className={cn("w-7 h-7 rounded-xl flex items-center justify-center flex-shrink-0 text-[10px] font-bold",
                  msg.sender === "buyer"  ? "bg-rose-500/15 text-rose-400" :
                  msg.sender === "seller" ? "bg-blue-500/15 text-blue-400" :
                  "bg-violet-500/15 text-violet-400")}>
                  {msg.sender === "buyer" ? "B" : msg.sender === "seller" ? "S" : "A"}
                </div>
                <div className={cn("flex flex-col gap-0.5 max-w-[75%]",
                  msg.sender === "seller" ? "items-end" : "items-start")}>
                  <div className={cn("px-3 py-2 rounded-2xl text-[12px] leading-relaxed",
                    msg.sender === "buyer"  ? "bg-white/[0.06] text-zinc-300 rounded-tl-sm" :
                    msg.sender === "seller" ? "bg-blue-600/80 text-white rounded-tr-sm" :
                    "bg-violet-500/15 text-violet-300 rounded-tl-sm border border-violet-500/20")}>
                    {msg.text}
                  </div>
                  <span className="text-[10px] text-zinc-700">{timeAgo(msg.created_at)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Actions — only if not resolved */}
          {!["resolved_seller", "resolved_buyer"].includes(dispute.status) && (
            <>
              {/* Reply input */}
              <div className="flex flex-col gap-2">
                <div className="text-[11px] font-semibold text-zinc-600 uppercase tracking-wider">Your Response</div>
                <div className="flex gap-2 items-end">
                  <textarea
                    value={replyText}
                    onChange={e => setReplyText(e.target.value)}
                    placeholder="Describe your position, provide evidence…"
                    rows={3}
                    className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors resize-none"
                  />
                  <button onClick={sendReply} disabled={sending || !replyText.trim()}
                    className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition-all disabled:opacity-50 flex-shrink-0">
                    {sending
                      ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      : <Send className="w-4 h-4 text-white" />}
                  </button>
                </div>
              </div>

              {/* Action buttons */}
              <div className="grid grid-cols-2 gap-2">
                <button onClick={acceptDispute} disabled={accepting}
                  className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-500/[0.08] border border-emerald-500/20 text-emerald-400 text-[12px] font-medium hover:bg-emerald-500/[0.15] transition-all disabled:opacity-50">
                  {accepting
                    ? <div className="w-3.5 h-3.5 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
                    : <CheckCircle className="w-3.5 h-3.5" />}
                  Accept & Refund
                </button>
                <button onClick={escalateDispute} disabled={escalating}
                  className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-violet-500/[0.08] border border-violet-500/20 text-violet-400 text-[12px] font-medium hover:bg-violet-500/[0.15] transition-all disabled:opacity-50">
                  {escalating
                    ? <div className="w-3.5 h-3.5 border-2 border-violet-400/30 border-t-violet-400 rounded-full animate-spin" />
                    : <Shield className="w-3.5 h-3.5" />}
                  Escalate to Admin
                </button>
              </div>
            </>
          )}

          {/* Resolved state */}
          {dispute.status === "resolved_seller" && (
            <div className="flex items-center gap-2.5 bg-emerald-500/[0.07] border border-emerald-500/20 rounded-2xl p-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <div className="text-[12px] text-emerald-300">Resolved in your favor. {dispute.resolution}</div>
            </div>
          )}
          {dispute.status === "resolved_buyer" && (
            <div className="flex items-center gap-2.5 bg-rose-500/[0.07] border border-rose-500/20 rounded-2xl p-3">
              <X className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <div className="text-[12px] text-rose-300">Refund issued to buyer.</div>
            </div>
          )}
        </>
      ) : (
        /* No dispute yet — seller can open one */
        <div className="flex flex-col gap-4">
          <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
            <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-zinc-600" />
            </div>
            <div className="text-[14px] font-semibold text-zinc-500">No active dispute</div>
            <div className="text-[12px] text-zinc-700 max-w-[220px]">
              If there is an issue with this order, you can open a dispute for admin review.
            </div>
          </div>

          {order.status === "completed" && !showOpenForm && (
            <button onClick={() => setShowOpenForm(true)}
              className="flex items-center justify-center gap-2 py-3 rounded-2xl border border-amber-500/20 bg-amber-500/[0.07] text-amber-400 text-[13px] font-medium hover:bg-amber-500/[0.12] transition-all">
              <Flag className="w-4 h-4" /> Open Dispute
            </button>
          )}

          {showOpenForm && (
            <div className="flex flex-col gap-3">
              <div className="flex items-start gap-2 bg-amber-500/[0.07] border border-amber-500/20 rounded-2xl p-3">
                <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-amber-300/80 leading-relaxed">
                  Describe the issue clearly. Admin will review within 24h and notify you via bot.
                </p>
              </div>
              <textarea
                value={newReason}
                onChange={e => setNewReason(e.target.value)}
                placeholder="Describe the issue with this order…"
                rows={4}
                className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-amber-500/40 transition-colors resize-none"
              />
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => { setShowOpenForm(false); setNewReason(""); }}
                  className="py-2.5 rounded-xl bg-white/[0.05] text-zinc-400 text-[13px] font-medium hover:bg-white/[0.10] transition-all">
                  Cancel
                </button>
                <button onClick={openNewDispute} disabled={openingNew || !newReason.trim()}
                  className="py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-[13px] font-semibold transition-all disabled:opacity-50 flex items-center justify-center gap-1.5">
                  {openingNew
                    ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    : <Flag className="w-4 h-4" />}
                  {openingNew ? "Opening…" : "Open Dispute"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Order Card ──────────────────────────────────────── */

function OrderCard({
  order,
  onOpenDispute,
}: {
  order: Order;
  onOpenDispute: (order: Order) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={cn("glass-card transition-all duration-200",
      order.status === "disputed" && "border-rose-500/20")}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <StatusIcon status={order.status} />
            <div className="min-w-0">
              <div className="font-semibold text-[14px] text-white truncate">
                {truncate(order.bank_name ?? order.product_type ?? `Order #${order.id}`, 28)}
              </div>
              <div className="text-[12px] text-zinc-500 mt-0.5">
                #{order.id} · {fmtDateTime(order.created_at)}
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
            <span className={cn("text-[11px] px-2 py-0.5 rounded-full font-medium", statusBg(order.status))}>
              {fmtStatus(order.status)}
            </span>
            {order.price_for_seller != null && (
              <span className="text-[13px] font-semibold text-emerald-400 tabular-nums">
                {fmtMoney(order.price_for_seller)}
              </span>
            )}
            {expanded
              ? <ChevronUp className="w-3.5 h-3.5 text-zinc-700" />
              : <ChevronDown className="w-3.5 h-3.5 text-zinc-700" />}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 flex flex-col gap-3">
          {/* Primary details grid */}
          <div className="pt-3 border-t border-white/[0.06] grid grid-cols-2 gap-2">
            {order.product_type && (
              <InfoRow label="Type" value={order.product_type.replace(/_/g, " ")} />
            )}
            {order.product_subtype && (
              <InfoRow label="Subtype" value={order.product_subtype.replace(/_/g, " ")} />
            )}
            {order.quantity != null && (
              <InfoRow label="Quantity" value={String(order.quantity)} />
            )}
            {order.price_for_buyer != null && (
              <InfoRow label="Buyer Price" value={fmtMoney(order.price_for_buyer)} />
            )}
            {order.taken_at && (
              <InfoRow label="Taken at" value={fmtDateTime(order.taken_at)} />
            )}
            {order.completed_at && (
              <InfoRow label="Completed" value={fmtDateTime(order.completed_at)} />
            )}
            {order.auto_complete_at && (
              <InfoRow label="Auto-complete" value={fmtDateTime(order.auto_complete_at)} />
            )}
            {order.dispute_deadline_at && (
              <InfoRow label="Dispute deadline" value={fmtDateTime(order.dispute_deadline_at)} />
            )}
          </div>

          {/* Seller notes */}
          {order.seller_notes && (
            <div className="flex flex-col gap-1">
              <div className="text-[10px] text-zinc-600 uppercase tracking-wide">Your notes</div>
              <div className="text-[12px] text-zinc-300 leading-relaxed bg-white/[0.03] rounded-xl px-3 py-2">
                {order.seller_notes}
              </div>
            </div>
          )}

          {/* Admin notes — special amber highlight section */}
          {order.admin_notes != null && (
            <div className="flex flex-col gap-1.5 bg-amber-500/[0.07] border border-amber-500/20 rounded-xl px-3 py-2.5">
              <div className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                <div className="text-[10px] font-semibold text-amber-400 uppercase tracking-wide">Notes from admin</div>
              </div>
              <div className="text-[12px] text-amber-200/80 leading-relaxed">
                {order.admin_notes}
              </div>
            </div>
          )}

          {/* Dispute button */}
          <button
            onClick={() => onOpenDispute(order)}
            className={cn(
              "flex items-center justify-center gap-2 py-2.5 rounded-xl border text-[12px] font-medium transition-all",
              order.status === "disputed"
                ? "bg-rose-500/[0.10] border-rose-500/25 text-rose-400 hover:bg-rose-500/[0.15]"
                : "bg-white/[0.04] border-white/[0.08] text-zinc-500 hover:border-amber-500/20 hover:text-amber-400 hover:bg-amber-500/[0.06]"
            )}>
            <AlertTriangle className="w-3.5 h-3.5" />
            {order.status === "disputed" ? "View Dispute" : "Open Dispute"}
          </button>
        </div>
      )}
    </div>
  );
}

/* ─── Main OrdersTab ──────────────────────────────────── */

export default function OrdersTab() {
  const { isDemoMode } = useApp();
  const [filter, setFilter] = useState<Filter>("active");
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [disputeOrder, setDisputeOrder] = useState<Order | null>(null);

  const loadOrders = async (f: Filter) => {
    setLoading(true);
    try {
      if (isDemoMode) {
        await new Promise(r => setTimeout(r, 200));
        setOrders([]);
      } else {
        const data = await apiFetch<{ items: Order[]; total: number }>(`/orders?status_filter=${f}`);
        setOrders(data.items);
      }
    } catch (e) { toast.error((e as Error).message); setOrders([]); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadOrders(filter); }, [filter, isDemoMode]);

  if (disputeOrder) {
    return <DisputeScreen order={disputeOrder} onBack={() => setDisputeOrder(null)} />;
  }

  const activeCount   = orders.filter(o => ["approved", "in_progress"].includes(o.status)).length;
  const disputedCount = orders.filter(o => o.status === "disputed").length;

  /* Label used in the order count header */
  const filterLabel = FILTERS.find(f => f.id === filter)?.label ?? filter;

  return (
    <div className="section-gap">
      {/* Tab header — warehouse description */}
      <div className="flex flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <Warehouse className="w-4 h-4 text-zinc-500 flex-shrink-0" />
          <span className="text-[12px] text-zinc-500">
            Approved goods warehouse + full history
          </span>
        </div>
        <span className="text-[11px] text-zinc-700 pl-6">
          Active orders are your inventory in progress
        </span>
      </div>

      {/* Stats chips */}
      {(activeCount > 0 || disputedCount > 0) && (
        <div className="flex gap-2 flex-wrap">
          {activeCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[12px] font-medium">
              <Clock className="w-3.5 h-3.5" /> {activeCount} active
            </div>
          )}
          {disputedCount > 0 && (
            <button onClick={() => setFilter("disputed")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[12px] font-medium hover:bg-rose-500/20 transition-all">
              <AlertTriangle className="w-3.5 h-3.5" /> {disputedCount} disputed
            </button>
          )}
        </div>
      )}

      {/* Filter bar */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-none">
        {FILTERS.map(f => (
          <button key={f.id} onClick={() => setFilter(f.id)}
            className={cn(
              "flex-shrink-0 px-4 py-2 rounded-xl text-[13px] font-medium transition-all duration-150",
              filter === f.id
                ? "bg-blue-500 text-white shadow-[0_0_12px_oklch(0.62_0.22_258/0.4)]"
                : "bg-white/[0.05] text-zinc-400 hover:text-white hover:bg-white/[0.08]"
            )}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Orders list */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-zinc-600">
          <div className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-600">
          <Package className="w-12 h-12 opacity-30" />
          <span className="text-sm">No orders found</span>
        </div>
      ) : (
        <>
          {/* Order count header for current filter */}
          <div className="text-[12px] text-zinc-600 font-medium px-0.5">
            {orders.length} {orders.length === 1 ? "order" : "orders"} · {filterLabel}
          </div>

          <div className="flex flex-col gap-2">
            {orders.map(o => (
              <OrderCard key={o.id} order={o} onOpenDispute={setDisputeOrder} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (["completed", "approved"].includes(status))
    return <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />;
  if (status === "disputed")
    return <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />;
  return <Clock className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-zinc-600 uppercase tracking-wide">{label}</div>
      <div className="text-[12px] text-zinc-300 mt-0.5">{value}</div>
    </div>
  );
}
