/* ═══════════════════════════════════════════════════════
   TeamTab — Team Management
   Design: Obsidian Glass

   ROLES (combinable per helper):
   • upload_helper  — can upload products
   • support_helper — can reply to buyer chats
   • manager_helper — analytics + listings management

   ADD: by Telegram numeric ID or @username
   AUDIT: full action log per helper
   NOTIFICATIONS: bot notifies helper on add/role change/remove
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { useApp } from "@/contexts/AppContext";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import {
  UserPlus, Shield, Upload, MessageCircle, BarChart2,
  Trash2, ChevronDown, ChevronUp, RefreshCw, Clock,
  AlertCircle, Plus, X, Check, ChevronLeft, Info,
} from "lucide-react";

/* ─── Types ───────────────────────────────────────────── */

type HelperRole = "upload_helper" | "support_helper" | "manager_helper";

interface Helper {
  id: number;
  telegram_id: string;
  display_name: string;
  username: string | null;
  roles: HelperRole[];           // multi-role
  is_active: boolean;
  invited_at: string;
  last_action_at: string | null;
  actions_count: number;
}

interface AuditEntry {
  id: number;
  action_type: string;
  description: string;
  created_at: string;
}

/* ─── Role definitions ────────────────────────────────── */

const ROLE_META: Record<HelperRole, {
  label: string;
  color: string;
  bg: string;
  icon: React.ComponentType<{ className?: string }>;
  perms: string[];
}> = {
  upload_helper: {
    label: "Upload",
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
    icon: Upload,
    perms: ["Upload products", "View own batches"],
  },
  support_helper: {
    label: "Support",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    icon: MessageCircle,
    perms: ["Reply to buyer chats", "View orders"],
  },
  manager_helper: {
    label: "Manager",
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    icon: BarChart2,
    perms: ["Analytics", "Manage listings", "View all stats"],
  },
};

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

function RolePill({ role }: { role: HelperRole }) {
  const m = ROLE_META[role];
  const Icon = m.icon;
  return (
    <span className={cn("inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-lg border font-semibold", m.color, m.bg)}>
      <Icon className="w-2.5 h-2.5" /> {m.label}
    </span>
  );
}

/* ─── Add Helper Form ─────────────────────────────────── */

function AddHelperForm({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (h: Helper) => void;
}) {
  const { isDemoMode } = useApp();
  const [identifier, setIdentifier] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<HelperRole[]>([]);
  const [loading, setLoading] = useState(false);

  const toggleRole = (role: HelperRole) =>
    setSelectedRoles(prev =>
      prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
    );

  const submit = async () => {
    if (!identifier.trim()) { toast.error("Enter Telegram ID or @username"); return; }
    if (selectedRoles.length === 0) { toast.error("Select at least one role"); return; }
    setLoading(true);
    try {
      let helper: Helper;
      if (isDemoMode) {
        helper = {
          id: Date.now(), telegram_id: identifier.replace("@", ""),
          display_name: identifier.startsWith("@") ? identifier.slice(1) : `User ${identifier}`,
          username: identifier.startsWith("@") ? identifier.slice(1) : null,
          roles: selectedRoles, is_active: true,
          invited_at: new Date().toISOString(), last_action_at: null, actions_count: 0,
        };
      } else {
        helper = await apiFetch<Helper>("/team/add", {
          method: "POST",
          json: { identifier: identifier.trim(), roles: selectedRoles },
        });
      }
      toast.success("Helper added — notification sent via Seller Bot");
      onAdded(helper);
      onClose();
    } catch (e) { toast.error((e as Error).message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={onClose}
          className="w-8 h-8 rounded-xl bg-white/[0.05] flex items-center justify-center hover:bg-white/[0.10] transition-colors">
          <ChevronLeft className="w-4 h-4 text-zinc-400" />
        </button>
        <div>
          <div className="text-[15px] font-bold text-white">Add Helper</div>
          <div className="text-[11px] text-zinc-600">By Telegram ID or @username</div>
        </div>
      </div>

      {/* Info */}
      <div className="flex items-start gap-2.5 bg-blue-500/[0.07] border border-blue-500/20 rounded-2xl p-3">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <p className="text-[12px] text-blue-300/80 leading-relaxed">
          Helper must have started the Seller Bot at least once. They will receive a notification with their assigned roles.
        </p>
      </div>

      {/* Identifier */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
          Telegram ID or @username <span className="text-rose-400">*</span>
        </label>
        <input
          value={identifier}
          onChange={e => setIdentifier(e.target.value)}
          placeholder="123456789  or  @username"
          className="w-full bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-[13px] text-white placeholder:text-zinc-700 outline-none focus:border-blue-500/40 transition-colors"
        />
        <span className="text-[10px] text-zinc-700">Numeric ID is preferred — usernames can change</span>
      </div>

      {/* Roles — multi-select */}
      <div className="flex flex-col gap-2">
        <label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
          Roles <span className="text-rose-400">*</span>
          <span className="text-zinc-700 normal-case font-normal ml-1">(select one or more)</span>
        </label>
        {(Object.entries(ROLE_META) as [HelperRole, typeof ROLE_META[HelperRole]][]).map(([role, meta]) => {
          const Icon = meta.icon;
          const selected = selectedRoles.includes(role);
          return (
            <button key={role} onClick={() => toggleRole(role)}
              className={cn(
                "flex items-center gap-3 px-3.5 py-3 rounded-2xl border transition-all text-left",
                selected ? cn(meta.bg, "border-opacity-40") : "bg-white/[0.03] border-white/[0.07]"
              )}>
              <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0",
                selected ? cn(meta.bg) : "bg-zinc-800")}>
                <Icon className={cn("w-4 h-4", selected ? meta.color : "text-zinc-600")} />
              </div>
              <div className="flex-1 min-w-0">
                <div className={cn("text-[13px] font-semibold", selected ? "text-white" : "text-zinc-500")}>
                  {meta.label}
                </div>
                <div className="text-[11px] text-zinc-600">{meta.perms.join(" · ")}</div>
              </div>
              <div className={cn(
                "w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all flex-shrink-0",
                selected ? cn("border-transparent", meta.bg) : "border-zinc-600 bg-transparent"
              )}>
                {selected && <Check className={cn("w-3 h-3", meta.color)} />}
              </div>
            </button>
          );
        })}
      </div>

      <button onClick={submit} disabled={loading}
        className="w-full py-3 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[14px] transition-all disabled:opacity-50 flex items-center justify-center gap-2">
        {loading
          ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          : <Plus className="w-4 h-4" />}
        {loading ? "Adding…" : "Add Helper"}
      </button>
    </div>
  );
}

/* ─── Helper Row (expanded) ───────────────────────────── */

function HelperRow({
  helper,
  onRemove,
  onRolesChange,
}: {
  helper: Helper;
  onRemove: (id: number) => void;
  onRolesChange: (id: number, roles: HelperRole[]) => void;
}) {
  const { isDemoMode } = useApp();
  const [expanded, setExpanded] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [editRoles, setEditRoles] = useState<HelperRole[]>(helper.roles);
  const [savingRoles, setSavingRoles] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);

  const rolesChanged = JSON.stringify(editRoles.sort()) !== JSON.stringify([...helper.roles].sort());

  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      if (isDemoMode) { setAudit([]); }
      else { setAudit(await apiFetch<AuditEntry[]>(`/team/helpers/${helper.id}/audit`)); }
    } catch (e) { toast.error((e as Error).message); setAudit([]); }
    finally { setAuditLoading(false); }
  }, [helper.id, isDemoMode]);

  useEffect(() => {
    if (expanded) loadAudit();
  }, [expanded, loadAudit]);

  const toggleRole = (role: HelperRole) =>
    setEditRoles(prev => prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]);

  const saveRoles = async () => {
    if (editRoles.length === 0) { toast.error("At least one role required"); return; }
    setSavingRoles(true);
    try {
      if (!isDemoMode) {
        await apiFetch(`/team/helpers/${helper.id}/roles`, {
          method: "PATCH", json: { roles: editRoles },
        });
      }
      onRolesChange(helper.id, editRoles);
      toast.success("Roles updated — helper notified via bot");
    } catch (e) { toast.error((e as Error).message); }
    finally { setSavingRoles(false); }
  };

  const doRemove = async () => {
    setRemoving(true);
    try {
      if (!isDemoMode) await apiFetch(`/team/helpers/${helper.id}`, { method: "DELETE" });
      onRemove(helper.id);
      toast.success(`${helper.display_name} removed`);
    } catch (e) { toast.error((e as Error).message); }
    finally { setRemoving(false); }
  };

  return (
    <div className={cn("bg-white/[0.04] border rounded-2xl overflow-hidden transition-all",
      expanded ? "border-blue-500/20" : "border-white/[0.07]")}>
      {/* Main row */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-3 p-3.5 text-left">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-violet-500/15 border border-white/[0.08] flex items-center justify-center flex-shrink-0">
          <span className="text-[14px] font-bold text-white">
            {helper.display_name.charAt(0).toUpperCase()}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[13px] font-semibold text-white">{helper.display_name}</span>
            {!helper.is_active && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700">
                Inactive
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {helper.roles.map(r => <RolePill key={r} role={r} />)}
          </div>
          {helper.username && (
            <div className="text-[10px] text-zinc-700 mt-0.5">@{helper.username} · ID {helper.telegram_id}</div>
          )}
        </div>

        {/* Stats + chevron */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="text-right">
            <div className="text-[12px] font-bold text-white tabular-nums">{helper.actions_count}</div>
            <div className="text-[9px] text-zinc-700">actions</div>
          </div>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-zinc-600" />
            : <ChevronDown className="w-4 h-4 text-zinc-600" />}
        </div>
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="border-t border-white/[0.06] p-3.5 flex flex-col gap-4">
          {/* Last active */}
          {helper.last_action_at && (
            <div className="flex items-center gap-1.5 text-[11px] text-zinc-600">
              <Clock className="w-3 h-3" />
              <span>Last active: {timeAgo(helper.last_action_at)}</span>
            </div>
          )}

          {/* Edit roles */}
          <div>
            <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-2">Roles</div>
            <div className="flex flex-col gap-1.5">
              {(Object.entries(ROLE_META) as [HelperRole, typeof ROLE_META[HelperRole]][]).map(([role, rm]) => {
                const RI = rm.icon;
                const active = editRoles.includes(role);
                return (
                  <button key={role} onClick={() => toggleRole(role)}
                    className={cn(
                      "flex items-center gap-2.5 px-3 py-2 rounded-xl border text-left transition-all",
                      active ? cn(rm.bg) : "bg-white/[0.02] border-white/[0.06] hover:border-white/[0.12]"
                    )}>
                    <RI className={cn("w-3.5 h-3.5 flex-shrink-0", active ? rm.color : "text-zinc-600")} />
                    <div className="flex-1 min-w-0">
                      <div className={cn("text-[12px] font-medium", active ? "text-white" : "text-zinc-500")}>
                        {rm.label}
                      </div>
                      <div className="text-[10px] text-zinc-700 truncate">{rm.perms.join(" · ")}</div>
                    </div>
                    <div className={cn("w-4 h-4 rounded border-2 transition-all flex-shrink-0 flex items-center justify-center",
                      active ? cn("border-transparent", rm.bg) : "border-zinc-600")}>
                      {active && <Check className={cn("w-2.5 h-2.5", rm.color)} />}
                    </div>
                  </button>
                );
              })}
            </div>
            {rolesChanged && (
              <button onClick={saveRoles} disabled={savingRoles}
                className="mt-2 w-full py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-[12px] font-semibold transition-all disabled:opacity-50 flex items-center justify-center gap-1.5">
                {savingRoles
                  ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  : <Check className="w-3.5 h-3.5" />}
                {savingRoles ? "Saving…" : "Save Roles"}
              </button>
            )}
          </div>

          {/* Audit log */}
          <div>
            <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider mb-1.5">
              Recent Actions
            </div>
            {auditLoading ? (
              <div className="flex justify-center py-3">
                <div className="w-4 h-4 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              </div>
            ) : audit.length === 0 ? (
              <div className="text-[12px] text-zinc-700 text-center py-2">No actions yet</div>
            ) : (
              <div className="flex flex-col gap-0 max-h-36 overflow-y-auto">
                {audit.map(entry => (
                  <div key={entry.id}
                    className="flex items-start gap-2 py-1.5 border-b border-white/[0.04] last:border-0">
                    <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                      entry.action_type === "upload"      ? "bg-blue-400" :
                      entry.action_type === "chat"        ? "bg-emerald-400" :
                      entry.action_type === "role_change" ? "bg-amber-400" : "bg-zinc-600"
                    )} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] text-zinc-400 truncate">{entry.description}</div>
                      <div className="text-[10px] text-zinc-700">{timeAgo(entry.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Remove */}
          {!confirmRemove ? (
            <button onClick={() => setConfirmRemove(true)}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-rose-500/[0.07] border border-rose-500/20 text-rose-400 text-[12px] font-medium hover:bg-rose-500/[0.12] transition-all">
              <Trash2 className="w-3.5 h-3.5" /> Remove from Team
            </button>
          ) : (
            <div className="bg-rose-500/[0.07] border border-rose-500/20 rounded-xl p-3 flex flex-col gap-2">
              <div className="text-[12px] text-rose-300 font-medium">
                Remove {helper.display_name}?
              </div>
              <div className="text-[11px] text-zinc-600">
                They will lose all access and be notified via bot.
              </div>
              <div className="grid grid-cols-2 gap-2 mt-1">
                <button onClick={() => setConfirmRemove(false)}
                  className="py-2 rounded-xl bg-white/[0.05] text-zinc-400 text-[12px] font-medium hover:bg-white/[0.10] transition-all">
                  Cancel
                </button>
                <button onClick={doRemove} disabled={removing}
                  className="py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-[12px] font-semibold transition-all disabled:opacity-50 flex items-center justify-center gap-1">
                  {removing
                    ? <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    : <><X className="w-3.5 h-3.5" /> Confirm</>}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Main TeamTab ────────────────────────────────────── */

export default function TeamTab() {
  const { isDemoMode } = useApp();
  const [helpers, setHelpers] = useState<Helper[]>([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<"list" | "add">("list");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isDemoMode) { setHelpers([]); }
      else { setHelpers(await apiFetch<Helper[]>("/team/helpers")); }
    } catch (e) { toast.error((e as Error).message); setHelpers([]); }
    finally { setLoading(false); }
  }, [isDemoMode]);

  useEffect(() => { load(); }, [load]);

  const handleAdded = (h: Helper) => setHelpers(prev => [h, ...prev]);
  const handleRemove = (id: number) => setHelpers(prev => prev.filter(x => x.id !== id));
  const handleRolesChange = (id: number, roles: HelperRole[]) =>
    setHelpers(prev => prev.map(x => x.id === id ? { ...x, roles } : x));

  if (view === "add") {
    return (
      <div className="px-4 pt-4 pb-8">
        <AddHelperForm
          onClose={() => setView("list")}
          onAdded={h => { handleAdded(h); setView("list"); }}
        />
      </div>
    );
  }

  const activeCount = helpers.filter(h => h.is_active).length;

  return (
    <div className="flex flex-col gap-4 px-4 pt-4 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[16px] font-bold text-white">Team</h2>
          <p className="text-[12px] text-zinc-600 mt-0.5">
            {activeCount} active helper{activeCount !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load}
            className="w-8 h-8 rounded-xl bg-white/[0.05] flex items-center justify-center hover:bg-white/[0.10] transition-colors">
            <RefreshCw className={cn("w-3.5 h-3.5 text-zinc-500", loading && "animate-spin")} />
          </button>
          <button onClick={() => setView("add")}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 text-white text-[12px] font-semibold hover:bg-blue-500 transition-all">
            <UserPlus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
      </div>

      {/* Role legend */}
      <div className="flex items-center gap-2 flex-wrap">
        {(Object.entries(ROLE_META) as [HelperRole, typeof ROLE_META[HelperRole]][]).map(([role, meta]) => {
          const Icon = meta.icon;
          return (
            <div key={role} className={cn("flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg border font-semibold", meta.color, meta.bg)}>
              <Icon className="w-3 h-3" /> {meta.label}
            </div>
          );
        })}
        <span className="text-[10px] text-zinc-700 ml-1">combinable</span>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      ) : helpers.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
          <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center">
            <Shield className="w-6 h-6 text-zinc-600" />
          </div>
          <div className="text-[14px] font-semibold text-zinc-500">No helpers yet</div>
          <div className="text-[12px] text-zinc-700 max-w-[200px]">
            Add helpers by Telegram ID to delegate uploads, support, and management.
          </div>
          <button onClick={() => setView("add")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-blue-600 text-white text-[13px] font-semibold hover:bg-blue-500 transition-all mt-2">
            <Plus className="w-4 h-4" /> Add First Helper
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {helpers.map(helper => (
            <HelperRow
              key={helper.id}
              helper={helper}
              onRemove={handleRemove}
              onRolesChange={handleRolesChange}
            />
          ))}
        </div>
      )}

      {/* Info note */}
      <div className="flex items-start gap-2.5 bg-white/[0.03] border border-white/[0.06] rounded-2xl p-3.5">
        <AlertCircle className="w-4 h-4 text-zinc-600 flex-shrink-0 mt-0.5" />
        <div className="text-[11px] text-zinc-600 leading-relaxed">
          Helpers authenticate via Seller Bot. All their actions are logged. Notifications are sent automatically on add, role change, and removal.
        </div>
      </div>
    </div>
  );
}
