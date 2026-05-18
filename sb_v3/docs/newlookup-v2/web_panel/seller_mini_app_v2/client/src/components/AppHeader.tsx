/* ═══════════════════════════════════════════════════════
   AppHeader — Obsidian Glass design
   Notifications bell: click → dropdown with unread count
   ═══════════════════════════════════════════════════════ */

import { useState, useRef, useEffect } from "react";
import { cn, getInitials, fmtTime } from "@/lib/utils";
import { useApp, type AppNotification } from "@/contexts/AppContext";
import { Bell, Package, AlertTriangle, CheckCircle, DollarSign, Info, X } from "lucide-react";

/* ─── Notification icon by type ─────────────────────── */

function NotifIcon({ type }: { type: AppNotification["type"] }) {
  const map: Record<AppNotification["type"], { icon: React.ComponentType<{ className?: string }>; color: string; bg: string }> = {
    order:      { icon: Package,       color: "text-blue-400",    bg: "bg-blue-500/15"    },
    dispute:    { icon: AlertTriangle, color: "text-rose-400",    bg: "bg-rose-500/15"    },
    moderation: { icon: CheckCircle,   color: "text-emerald-400", bg: "bg-emerald-500/15" },
    finance:    { icon: DollarSign,    color: "text-amber-400",   bg: "bg-amber-500/15"   },
    system:     { icon: Info,          color: "text-zinc-400",    bg: "bg-zinc-700/50"    },
  };
  const { icon: Icon, color, bg } = map[type];
  return (
    <div className={cn("w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0", bg)}>
      <Icon className={cn("w-3.5 h-3.5", color)} />
    </div>
  );
}

/* ─── Notifications Dropdown ─────────────────────────── */

function NotificationsDropdown({
  onClose,
}: {
  onClose: () => void;
}) {
  const { notifications, markNotificationRead, markAllNotificationsRead, setTab, unreadNotifications } = useApp();

  const handleClick = (n: AppNotification) => {
    markNotificationRead(n.id);
    if (n.tab) setTab(n.tab);
    onClose();
  };

  return (
    <div
      className="absolute top-full right-0 mt-2 w-[320px] max-h-[420px] rounded-2xl border border-white/[0.08] shadow-2xl overflow-hidden flex flex-col"
      style={{ background: "oklch(0.11 0.014 260)", zIndex: 100 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-bold text-white">Notifications</span>
          {unreadNotifications > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-500 text-white font-bold">
              {unreadNotifications}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {unreadNotifications > 0 && (
            <button
              onClick={markAllNotificationsRead}
              className="text-[11px] text-blue-400 hover:text-blue-300 transition-colors"
            >
              Mark all read
            </button>
          )}
          <button onClick={onClose} className="text-zinc-600 hover:text-zinc-400 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="overflow-y-auto flex-1">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2 text-zinc-600">
            <Bell className="w-8 h-8 opacity-30" />
            <span className="text-[12px]">No notifications</span>
          </div>
        ) : (
          notifications.map(n => (
            <button
              key={n.id}
              onClick={() => handleClick(n)}
              className={cn(
                "w-full flex items-start gap-3 px-4 py-3 text-left border-b border-white/[0.04] last:border-0 transition-all",
                n.read
                  ? "hover:bg-white/[0.03]"
                  : "bg-blue-500/[0.05] hover:bg-blue-500/[0.08]"
              )}
            >
              <NotifIcon type={n.type} />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <span className={cn("text-[12px] font-semibold leading-tight", n.read ? "text-zinc-400" : "text-white")}>
                    {n.title}
                  </span>
                  <span className="text-[10px] text-zinc-700 flex-shrink-0">{fmtTime(n.timestamp)}</span>
                </div>
                <p className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed line-clamp-2">{n.body}</p>
              </div>
              {!n.read && (
                <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1" />
              )}
            </button>
          ))
        )}
      </div>
    </div>
  );
}

/* ─── AppHeader ──────────────────────────────────────── */

export default function AppHeader() {
  const { seller, unreadTotal, unreadNotifications } = useApp();
  const [showNotifs, setShowNotifs] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  const name = seller?.display_name ?? "Loading…";
  const initials = seller ? getInitials(name) : "S";
  const isOnVacation = seller?.is_on_vacation ?? false;
  const isOnline = !isOnVacation && !!seller;

  // Close dropdown on outside click
  useEffect(() => {
    if (!showNotifs) return;
    const handler = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setShowNotifs(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNotifs]);

  return (
    <header className="app-header">
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div className="relative flex-shrink-0">
          <div
            className="gradient-avatar w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm text-white shadow-lg"
            style={{ background: "linear-gradient(135deg, oklch(0.62 0.22 258), oklch(0.70 0.18 196))" }}
          >
            {initials}
          </div>
          {/* Status dot */}
          <span
            className={cn(
              "absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[oklch(0.09_0.012_260)] transition-all duration-300",
              isOnVacation
                ? "bg-amber-400 shadow-[0_0_6px_oklch(0.80_0.18_60)]"
                : isOnline
                ? "bg-emerald-400 shadow-[0_0_6px_oklch(0.72_0.18_145)]"
                : "bg-zinc-600"
            )}
          />
        </div>

        {/* Info */}
        <div className="min-w-0">
          <div className="font-semibold text-[15px] leading-tight text-white truncate max-w-[160px]">
            {name}
          </div>
          <div className="text-[11px] text-zinc-500 leading-tight mt-0.5">
            {isOnVacation ? "On vacation" : seller ? "Seller Hub" : "Connecting…"}
          </div>
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Notifications bell */}
        <div ref={bellRef} className="relative">
          <button
            onClick={() => setShowNotifs(v => !v)}
            className={cn(
              "relative w-9 h-9 rounded-xl flex items-center justify-center transition-all",
              showNotifs
                ? "bg-blue-500/20 text-blue-400"
                : "bg-white/[0.05] text-zinc-400 hover:bg-white/[0.10] hover:text-zinc-200"
            )}
          >
            <Bell className="w-4.5 h-4.5" />
            {unreadNotifications > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[16px] h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center px-1 shadow-lg">
                {unreadNotifications > 9 ? "9+" : unreadNotifications}
              </span>
            )}
          </button>

          {showNotifs && (
            <NotificationsDropdown onClose={() => setShowNotifs(false)} />
          )}
        </div>

        {/* Unread chats badge (when not showing bell count) */}
        {unreadTotal > 0 && unreadNotifications === 0 && (
          <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-rose-500/15 border border-rose-500/20">
            <span className="text-[11px] text-rose-400 font-bold">{unreadTotal}</span>
          </div>
        )}

        {/* Access status badge */}
        {seller?.access_status && seller.access_status !== "active" && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-medium border border-amber-500/20">
            {seller.access_status.replace(/_/g, " ")}
          </span>
        )}
      </div>
    </header>
  );
}
