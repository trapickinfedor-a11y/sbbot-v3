/* ═══════════════════════════════════════════════════════
   ModerationStatusTab — Batch & Custom Request Status
   Design: Obsidian Glass

   SECTIONS:
   1. Upload Batches    — all submitted batches with per-item counts
   2. Custom Requests   — custom bank / portal moderation requests
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect } from "react";
import { cn, fmtDateTime } from "@/lib/utils";
import { api, type Batch, type ModerationRequest } from "@/lib/api";
import { MOCK_BATCHES } from "@/lib/mockData";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import {
  Layers, ClipboardList, CheckCircle, XCircle, Clock,
  AlertTriangle, RefreshCw, ChevronDown, ChevronUp,
  Package, Building2, Globe, MessageSquare,
} from "lucide-react";

/* ─── Status helpers ──────────────────────────────────── */

type BatchStatus = Batch["moderation_status"];
type RequestStatus = ModerationRequest["status"];

function batchStatusLabel(s: BatchStatus): string {
  const map: Record<string, string> = {
    pending_moderation: "Pending",
    approved:           "Approved",
    rejected:           "Rejected",
    changes_requested:  "Changes Requested",
    draft:              "Draft",
  };
  return map[s] ?? s.replace(/_/g, " ");
}

function requestStatusLabel(s: RequestStatus): string {
  const map: Record<RequestStatus, string> = {
    pending:  "Pending",
    approved: "Approved",
    rejected: "Rejected",
  };
  return map[s];
}

function batchStatusClasses(s: BatchStatus): string {
  const map: Record<string, string> = {
    pending_moderation: "bg-amber-500/15 text-amber-400 border border-amber-500/20",
    approved:           "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20",
    rejected:           "bg-rose-500/15 text-rose-400 border border-rose-500/20",
    changes_requested:  "bg-violet-500/15 text-violet-400 border border-violet-500/20",
    draft:              "bg-zinc-500/15 text-zinc-400 border border-zinc-500/20",
  };
  return map[s] ?? "bg-zinc-500/15 text-zinc-400 border border-zinc-500/20";
}

function requestStatusClasses(s: RequestStatus): string {
  const map: Record<RequestStatus, string> = {
    pending:  "bg-amber-500/15 text-amber-400 border border-amber-500/20",
    approved: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20",
    rejected: "bg-rose-500/15 text-rose-400 border border-rose-500/20",
  };
  return map[s];
}

function batchStatusIcon(s: BatchStatus): React.ReactNode {
  switch (s) {
    case "approved":
      return <CheckCircle className="w-3.5 h-3.5" />;
    case "rejected":
      return <XCircle className="w-3.5 h-3.5" />;
    case "changes_requested":
      return <AlertTriangle className="w-3.5 h-3.5" />;
    case "pending_moderation":
    default:
      return <Clock className="w-3.5 h-3.5" />;
  }
}

function requestTypeLabel(t: string): string {
  const map: Record<string, string> = {
    custom_bank:   "Custom Bank",
    custom_portal: "Custom Portal",
  };
  return map[t] ?? t.replace(/_/g, " ");
}

function itemTypeLabel(t: string): string {
  const map: Record<string, string> = {
    bank_log:   "Bank Log",
    brute:      "Brute",
    cc:         "CC",
    nfc:        "NFC",
    otp:        "OTP",
    selfreg_cc: "Selfreg CC",
    enrollment: "Enrollment",
    logs:       "Logs",
    checks:     "Checks",
    selfreg_ba: "Selfreg BA",
  };
  return map[t] ?? t.replace(/_/g, " ");
}

/* ─── timeAgo helper ──────────────────────────────────── */

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 2) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/* ─── BatchCard ───────────────────────────────────────── */

function BatchCard({ batch }: { batch: Batch }) {
  const [expanded, setExpanded] = useState(false);

  const total = batch.total_items ?? 0;
  const hasComment = !!batch.moderation_comment;

  return (
    <div className="glass-card overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        {/* Icon */}
        <div className="mt-0.5 w-9 h-9 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0">
          <Package className="w-4 h-4 text-blue-400" />
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-semibold text-white truncate">
              {batch.title ?? `Batch #${batch.id}`}
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-lg",
                batchStatusClasses(batch.moderation_status)
              )}
            >
              {batchStatusIcon(batch.moderation_status)}
              {batchStatusLabel(batch.moderation_status)}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] text-zinc-500">
              {itemTypeLabel(batch.item_type)}
            </span>
            {total > 0 && (
              <span className="text-[11px] text-zinc-600">
                {total} item{total !== 1 ? "s" : ""}
              </span>
            )}
            <span className="text-[11px] text-zinc-600">
              {timeAgo(batch.submitted_at)}
            </span>
          </div>
        </div>

        {/* Chevron */}
        <div className="text-zinc-600 shrink-0 mt-1">
          {expanded
            ? <ChevronUp className="w-4 h-4" />
            : <ChevronDown className="w-4 h-4" />
          }
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/[0.06] pt-3 flex flex-col gap-3">
          {/* Count breakdown */}
          {total > 0 && (
            <div className="grid grid-cols-4 gap-2">
              <CountPill
                label="Approved"
                value={batch.approved_items}
                color="emerald"
              />
              <CountPill
                label="Pending"
                value={batch.pending_items}
                color="amber"
              />
              <CountPill
                label="Changes"
                value={batch.changes_requested_items}
                color="violet"
              />
              <CountPill
                label="Rejected"
                value={batch.rejected_items}
                color="rose"
              />
            </div>
          )}

          {/* Dates */}
          <div className="flex flex-col gap-1">
            {batch.submitted_at && (
              <MetaRow label="Submitted" value={fmtDateTime(batch.submitted_at)} />
            )}
            {batch.reviewed_at && (
              <MetaRow label="Reviewed" value={fmtDateTime(batch.reviewed_at)} />
            )}
            {batch.resubmitted_from_batch_id && (
              <MetaRow
                label="Resubmitted from"
                value={`Batch #${batch.resubmitted_from_batch_id}`}
              />
            )}
          </div>

          {/* Comment from admin */}
          {hasComment && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <MessageSquare className="w-3.5 h-3.5 text-zinc-500 mt-0.5 shrink-0" />
              <p className="text-[12px] text-zinc-400 leading-relaxed">
                {batch.moderation_comment}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── ModerationRequestCard ───────────────────────────── */

function ModerationRequestCard({ req }: { req: ModerationRequest }) {
  const [expanded, setExpanded] = useState(false);
  const isPortal = req.request_type === "custom_portal";

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        {/* Icon */}
        <div
          className={cn(
            "mt-0.5 w-9 h-9 rounded-xl flex items-center justify-center shrink-0",
            isPortal ? "bg-violet-500/10" : "bg-cyan-500/10"
          )}
        >
          {isPortal
            ? <Globe className={cn("w-4 h-4", "text-violet-400")} />
            : <Building2 className={cn("w-4 h-4", "text-cyan-400")} />
          }
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-semibold text-white truncate">
              {req.name}
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-lg",
                requestStatusClasses(req.status)
              )}
            >
              {req.status === "approved"
                ? <CheckCircle className="w-3.5 h-3.5" />
                : req.status === "rejected"
                ? <XCircle className="w-3.5 h-3.5" />
                : <Clock className="w-3.5 h-3.5" />
              }
              {requestStatusLabel(req.status)}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] text-zinc-500">
              {requestTypeLabel(req.request_type)}
            </span>
            <span className="text-[11px] text-zinc-600">
              {timeAgo(req.created_at)}
            </span>
          </div>
        </div>

        {/* Chevron */}
        <div className="text-zinc-600 shrink-0 mt-1">
          {expanded
            ? <ChevronUp className="w-4 h-4" />
            : <ChevronDown className="w-4 h-4" />
          }
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/[0.06] pt-3 flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <MetaRow label="Created" value={fmtDateTime(req.created_at)} />
            {req.reviewed_at && (
              <MetaRow label="Reviewed" value={fmtDateTime(req.reviewed_at)} />
            )}
          </div>

          {req.admin_comment && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <MessageSquare className="w-3.5 h-3.5 text-zinc-500 mt-0.5 shrink-0" />
              <p className="text-[12px] text-zinc-400 leading-relaxed">
                {req.admin_comment}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ──────────────────────────────────── */

type CountColor = "emerald" | "amber" | "violet" | "rose";

function CountPill({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: CountColor;
}) {
  const colorMap: Record<CountColor, { text: string; bg: string }> = {
    emerald: { text: "text-emerald-400", bg: "bg-emerald-500/10" },
    amber:   { text: "text-amber-400",   bg: "bg-amber-500/10" },
    violet:  { text: "text-violet-400",  bg: "bg-violet-500/10" },
    rose:    { text: "text-rose-400",    bg: "bg-rose-500/10" },
  };
  const c = colorMap[color];

  return (
    <div className={cn("rounded-xl p-2 flex flex-col items-center gap-0.5", c.bg)}>
      <span className={cn("text-[15px] font-bold tabular leading-none", c.text)}>
        {value}
      </span>
      <span className="text-[9px] text-zinc-500 uppercase tracking-wide font-medium text-center">
        {label}
      </span>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] text-zinc-600">{label}</span>
      <span className="text-[11px] text-zinc-400 tabular">{value}</span>
    </div>
  );
}

function SectionHeader({
  icon: Icon,
  title,
  count,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  count: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-6 h-6 rounded-lg bg-white/[0.06] flex items-center justify-center">
        <Icon className="w-3.5 h-3.5 text-zinc-400" />
      </div>
      <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
        {title}
      </span>
      {count > 0 && (
        <span className="ml-auto text-[11px] text-zinc-600 font-medium">
          {count}
        </span>
      )}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="glass-card p-6 flex flex-col items-center gap-2 text-center">
      <ClipboardList className="w-7 h-7 text-zinc-700" />
      <p className="text-[12px] text-zinc-600">{label}</p>
    </div>
  );
}

/* ─── Main component ──────────────────────────────────── */

export default function ModerationStatusTab() {
  const { isDemoMode } = useApp();

  const [batches, setBatches] = useState<Batch[]>([]);
  const [requests, setRequests] = useState<ModerationRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      if (isDemoMode) {
        await new Promise((r) => setTimeout(r, 250));
        setBatches(MOCK_BATCHES);
        setRequests([]);
      } else {
        const [batchData, reqData] = await Promise.all([
          api.batches(),
          api.moderationRequests(),
        ]);
        setBatches(batchData);
        setRequests(reqData);
      }
    } catch (e) {
      toast.error((e as Error).message ?? "Failed to load moderation data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemoMode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="section-gap">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-white">Moderation Status</h3>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="w-8 h-8 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-zinc-400 hover:text-white hover:border-white/[0.14] transition-all disabled:opacity-50"
          aria-label="Refresh"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
        </button>
      </div>

      {/* ── Section 1: Upload Batches ─────────────────────── */}
      <div className="flex flex-col gap-3">
        <SectionHeader
          icon={Layers}
          title="Upload Batches"
          count={batches.length}
        />

        {batches.length === 0 ? (
          <EmptyState label="No batches submitted yet" />
        ) : (
          batches.map((batch) => (
            <BatchCard key={batch.id} batch={batch} />
          ))
        )}
      </div>

      {/* ── Section 2: Custom Requests ────────────────────── */}
      <div className="flex flex-col gap-3">
        <SectionHeader
          icon={ClipboardList}
          title="Custom Requests"
          count={requests.length}
        />

        {requests.length === 0 ? (
          <EmptyState label="No custom bank or portal requests" />
        ) : (
          requests.map((req) => (
            <ModerationRequestCard key={req.id} req={req} />
          ))
        )}
      </div>
    </div>
  );
}
