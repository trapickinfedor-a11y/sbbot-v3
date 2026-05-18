/* ═══════════════════════════════════════════════════════
   SettingsTab — Seller profile, vacation, notifications, language
   Obsidian Glass design
   ═══════════════════════════════════════════════════════ */

import { useState } from "react";
import { cn, getInitials, fmtStatus, statusBg } from "@/lib/utils";
import { useApp, type AppLanguage, LANGUAGE_LABELS } from "@/contexts/AppContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  User, Umbrella, Bell, DollarSign, Shield,
  Clock, Globe,
} from "lucide-react";

export default function SettingsTab() {
  const { seller, refreshSeller, isDemoMode, language, setLanguage } = useApp();
  const [vacationLoading, setVacationLoading] = useState(false);
  const [autoPayoutLoading, setAutoPayoutLoading] = useState(false);
  const [quietFrom, setQuietFrom] = useState(seller?.quiet_hours_start ?? "");
  const [quietTo, setQuietTo] = useState(seller?.quiet_hours_end ?? "");
  const [quietLoading, setQuietLoading] = useState(false);

  const toggleVacation = async () => {
    if (!seller) return;
    setVacationLoading(true);
    try {
      if (!isDemoMode) {
        await api.setVacation(!seller.is_on_vacation, null);
      } else {
        await new Promise((r) => setTimeout(r, 400));
      }
      await refreshSeller();
      toast.success(seller.is_on_vacation ? "Vacation mode disabled" : "Vacation mode enabled");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setVacationLoading(false);
    }
  };

  const toggleAutoPayout = async () => {
    if (!seller) return;
    setAutoPayoutLoading(true);
    try {
      if (!isDemoMode) {
        await api.setAutoPayout(!seller.auto_payout_enabled);
      } else {
        await new Promise((r) => setTimeout(r, 400));
      }
      await refreshSeller();
      toast.success("Auto-payout setting updated");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setAutoPayoutLoading(false);
    }
  };

  const saveQuietHours = async () => {
    setQuietLoading(true);
    try {
      if (!isDemoMode) {
        await api.setQuietHours(quietFrom || null, quietTo || null);
      } else {
        await new Promise((r) => setTimeout(r, 400));
      }
      await refreshSeller();
      toast.success("Quiet hours saved");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setQuietLoading(false);
    }
  };

  if (!seller) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  const initials = getInitials(seller.display_name);

  return (
    <div className="section-gap">
      {/* Profile card */}
      <div
        className="glass-card p-5 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, oklch(0.62 0.22 258 / 0.12), oklch(0.70 0.18 196 / 0.08))",
          borderColor: "oklch(0.62 0.22 258 / 0.2)",
        }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-bold text-xl shadow-lg flex-shrink-0"
            style={{ background: "linear-gradient(135deg, oklch(0.62 0.22 258), oklch(0.70 0.18 196))" }}
          >
            {initials}
          </div>
          <div className="min-w-0">
            <div className="font-bold text-[18px] text-white truncate">{seller.display_name}</div>
            <div className="text-[12px] text-zinc-400 mt-0.5">
              {seller.actor_role.replace(/_/g, " ")}
              {seller.is_helper && (
                <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400">Helper</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium", statusBg(seller.access_status))}>
                {fmtStatus(seller.access_status)}
              </span>
              <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium", statusBg(seller.security_deposit_status))}>
                Deposit: {fmtStatus(seller.security_deposit_status)}
              </span>
            </div>
          </div>
        </div>

        {seller.allowed_categories.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/[0.06]">
            <div className="text-[10px] text-zinc-600 uppercase tracking-wide mb-2">Allowed Categories</div>
            <div className="flex flex-wrap gap-1.5">
              {seller.allowed_categories.map((cat) => (
                <span key={cat} className="text-[11px] px-2 py-0.5 rounded-full bg-white/[0.06] text-zinc-300 border border-white/[0.08]">
                  {cat.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Vacation mode */}
      <SettingRow
        icon={Umbrella}
        iconColor="amber"
        title="Vacation Mode"
        subtitle={seller.is_on_vacation ? "Your listings are hidden" : "Listings are visible to buyers"}
        action={
          <Toggle
            checked={seller.is_on_vacation}
            onChange={toggleVacation}
            loading={vacationLoading}
          />
        }
      />

      {/* Auto-payout */}
      <SettingRow
        icon={DollarSign}
        iconColor="green"
        title="Auto-Payout"
        subtitle={
          seller.auto_payout_enabled
            ? `Auto-withdraw at $${seller.auto_payout_threshold}`
            : "Manual withdrawals only"
        }
        action={
          <Toggle
            checked={seller.auto_payout_enabled}
            onChange={toggleAutoPayout}
            loading={autoPayoutLoading}
          />
        }
      />

      {/* Quiet hours */}
      <div className="glass-card p-4 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-violet-500/10 flex items-center justify-center flex-shrink-0">
            <Bell className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <div className="text-[14px] font-medium text-white">Quiet Hours</div>
            <div className="text-[11px] text-zinc-500">Pause notifications during these hours</div>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <input
            type="time"
            value={quietFrom}
            onChange={(e) => setQuietFrom(e.target.value)}
            className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500/40"
          />
          <span className="text-zinc-600 text-sm">to</span>
          <input
            type="time"
            value={quietTo}
            onChange={(e) => setQuietTo(e.target.value)}
            className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-blue-500/40"
          />
        </div>
        <button
          onClick={saveQuietHours}
          disabled={quietLoading}
          className="w-full py-2.5 rounded-xl bg-violet-500/15 text-violet-400 border border-violet-500/20 text-[13px] font-medium disabled:opacity-50 transition-all hover:bg-violet-500/25"
        >
          {quietLoading ? "Saving…" : "Save Quiet Hours"}
        </button>
      </div>

      {/* Language selector */}
      <div className="glass-card p-4 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
            <Globe className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <div className="text-[14px] font-medium text-white">Interface Language</div>
            <div className="text-[11px] text-zinc-500">Choose your preferred language</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {(Object.entries(LANGUAGE_LABELS) as [AppLanguage, string][]).map(([code, label]) => (
            <button
              key={code}
              onClick={() => {
                setLanguage(code);
                toast.success(`Language set to ${label}`);
              }}
              className={cn(
                "py-2.5 px-3 rounded-xl text-[12px] font-medium border transition-all text-left",
                language === code
                  ? "bg-cyan-500/20 border-cyan-500/30 text-cyan-300"
                  : "bg-white/[0.03] border-white/[0.06] text-zinc-400 hover:border-white/[0.12]"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Info rows */}
      <div className="glass-card overflow-hidden">
        <InfoRow icon={User} label="Seller ID" value={`${String(seller.seller_id).padStart(2, "0")} #${seller.seller_id}`} />
        <InfoRow icon={Shield} label="Telegram ID" value={`${seller.telegram_id}`} />
        <InfoRow icon={Clock} label="Deposit Status" value={fmtStatus(seller.security_deposit_status)} />
        {seller.vacation_ends_at && (
          <InfoRow icon={Umbrella} label="Vacation ends" value={new Date(seller.vacation_ends_at).toLocaleDateString()} />
        )}
      </div>


    </div>
  );
}

function SettingRow({
  icon: Icon, iconColor, title, subtitle, action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  title: string;
  subtitle: string;
  action: React.ReactNode;
}) {
  const colorMap: Record<string, string> = {
    amber: "bg-amber-500/10 text-amber-400",
    green: "bg-emerald-500/10 text-emerald-400",
    blue:  "bg-blue-500/10 text-blue-400",
    cyan:  "bg-cyan-500/10 text-cyan-400",
  };
  const cls = colorMap[iconColor] ?? "bg-white/[0.06] text-zinc-400";

  return (
    <div className="glass-card p-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0", cls)}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <div className="text-[14px] font-medium text-white">{title}</div>
          <div className="text-[11px] text-zinc-500 mt-0.5 truncate">{subtitle}</div>
        </div>
      </div>
      {action}
    </div>
  );
}

function InfoRow({
  icon: Icon, label, value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/[0.05] last:border-0">
      <div className="flex items-center gap-2.5 text-zinc-500">
        <Icon className="w-4 h-4" />
        <span className="text-[13px]">{label}</span>
      </div>
      <span className="text-[13px] text-zinc-300 font-medium tabular">{value}</span>
    </div>
  );
}

function Toggle({
  checked, onChange, loading,
}: {
  checked: boolean;
  onChange: () => void;
  loading: boolean;
}) {
  return (
    <button
      onClick={onChange}
      disabled={loading}
      className={cn(
        "w-12 h-6 rounded-full transition-all duration-200 relative flex-shrink-0 disabled:opacity-60",
        checked ? "bg-blue-500" : "bg-white/[0.10]"
      )}
    >
      <div
        className={cn(
          "absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all duration-200",
          checked ? "left-6" : "left-0.5"
        )}
      />
    </button>
  );
}
