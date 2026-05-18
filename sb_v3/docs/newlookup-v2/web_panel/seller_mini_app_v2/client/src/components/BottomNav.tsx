/* ═══════════════════════════════════════════════════════
   BottomNav — Obsidian Glass design
   Orders badge: uses real activeOrdersCount from context
   ═══════════════════════════════════════════════════════ */

import { cn } from "@/lib/utils";
import { useApp, type TabId } from "@/contexts/AppContext";
import { haptic } from "@/lib/telegram";
import {
  MessageSquare,
  Package,
  Upload,
  BarChart2,
  DollarSign,
  ClipboardList,
  Users,
  Settings,
} from "lucide-react";

interface NavItem {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeKey?: "unread" | "orders";
}

const NAV_ITEMS: NavItem[] = [
  { id: "chats",     label: "Chats",    icon: MessageSquare, badgeKey: "unread" },
  { id: "orders",    label: "Orders",   icon: Package,       badgeKey: "orders" },
  { id: "uploads",   label: "Upload",   icon: Upload },
  { id: "analytics", label: "Stats",    icon: BarChart2 },
  { id: "finance",   label: "Finance",  icon: DollarSign },
  { id: "moderation", label: "Status",  icon: ClipboardList },
  { id: "team",      label: "Team",     icon: Users },
  { id: "settings",  label: "More",     icon: Settings },
];

export default function BottomNav() {
  const { activeTab, setTab, unreadTotal, activeOrdersCount, seller } = useApp();

  const canChat   = !seller?.is_helper || ["support_helper", "manager_helper"].includes(seller?.actor_role ?? "");
  const canUpload = !seller?.is_helper || ["upload_helper", "manager_helper"].includes(seller?.actor_role ?? "");

  const handleTab = (id: TabId) => {
    haptic("selection");
    setTab(id);
  };

  return (
    <nav className="bottom-nav">
      {NAV_ITEMS.map(({ id, label, icon: Icon, badgeKey }) => {
        if (id === "chats" && !canChat) return null;
        if (id === "uploads" && !canUpload) return null;

        // FIX: Use real activeOrdersCount for orders badge
        const badge =
          badgeKey === "unread"  ? unreadTotal :
          badgeKey === "orders"  ? activeOrdersCount :
          0;

        const isActive = activeTab === id;

        return (
          <button
            key={id}
            onClick={() => handleTab(id)}
            className={cn(
              "flex-shrink-0 min-w-[56px] flex flex-col items-center justify-center gap-1 py-2 px-1 rounded-xl transition-all duration-200 relative",
              "border border-transparent",
              isActive
                ? "text-blue-400"
                : "text-zinc-500 hover:text-zinc-300"
            )}
          >
            {/* Active indicator */}
            {isActive && (
              <span className="absolute top-1 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-blue-400 shadow-[0_0_8px_oklch(0.62_0.22_258)]" />
            )}

            <div className="relative">
              <Icon
                className={cn(
                  "w-5 h-5 transition-transform duration-200",
                  isActive && "scale-110"
                )}
              />
              {badge > 0 && (
                <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center px-1">
                  {badge > 99 ? "99+" : badge}
                </span>
              )}
            </div>

            <span className={cn("text-[10px] font-medium leading-none", isActive ? "text-blue-400" : "")}>
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
