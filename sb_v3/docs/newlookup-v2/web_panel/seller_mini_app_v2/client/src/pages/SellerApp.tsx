/* ═══════════════════════════════════════════════════════
   SellerApp — Main page shell
   Design: Obsidian Glass (dark, glassmorphism)
   ═══════════════════════════════════════════════════════ */

import { AnimatePresence, motion } from "framer-motion";
import { AppProvider, useApp } from "@/contexts/AppContext";
import AppHeader from "@/components/AppHeader";
import BottomNav from "@/components/BottomNav";
import ChatsTab from "@/components/tabs/ChatsTab";
import OrdersTab from "@/components/tabs/OrdersTab";
import UploadsTab from "@/components/tabs/UploadsTab";
import AnalyticsTab from "@/components/tabs/AnalyticsTab";
import FinanceTab from "@/components/tabs/FinanceTab";
import SettingsTab from "@/components/tabs/SettingsTab";
import TeamTab from "@/components/tabs/TeamTab";
import ModerationStatusTab from "@/components/tabs/ModerationStatusTab";
import {
  MessageSquare, Package, Upload, BarChart2,
  DollarSign, Bell, ChevronRight, Zap, ClipboardCheck,
} from "lucide-react";

/* ─── Onboarding Screen ─────────────────────────────── */

const ONBOARDING_STEPS = [
  {
    icon: MessageSquare,
    color: "oklch(0.62 0.22 258)",
    title: "Chats & Orders",
    desc: "Manage buyer conversations and track all your orders in real time.",
  },
  {
    icon: Upload,
    color: "oklch(0.70 0.18 196)",
    title: "Upload Inventory",
    desc: "Submit Banks, Brute, CC, NFC, OTP, Enrollment, and Selfreg BA — single or bulk.",
  },
  {
    icon: BarChart2,
    color: "oklch(0.72 0.22 145)",
    title: "Analytics & Finance",
    desc: "Track revenue, conversion, disputes, and manage payouts with full CSV export.",
  },
  {
    icon: Bell,
    color: "oklch(0.80 0.18 60)",
    title: "Notifications",
    desc: "Instant alerts for new orders, disputes, moderation results, and payouts.",
  },
];

function OnboardingScreen() {
  const { completeOnboarding, seller } = useApp();

  return (
    <motion.div
      className="app-shell items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Ambient blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
        <div
          className="absolute -top-32 -left-32 w-80 h-80 rounded-full opacity-[0.07]"
          style={{ background: "radial-gradient(circle, oklch(0.62 0.22 258), transparent)" }}
        />
        <div
          className="absolute -bottom-32 -right-32 w-80 h-80 rounded-full opacity-[0.06]"
          style={{ background: "radial-gradient(circle, oklch(0.70 0.18 196), transparent)" }}
        />
      </div>

      <div className="w-full max-w-sm px-6 flex flex-col gap-6 relative z-10">
        {/* Logo + greeting */}
        <div className="flex flex-col items-center gap-3 pt-6">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center shadow-[0_0_32px_oklch(0.62_0.22_258/0.4)]"
            style={{ background: "linear-gradient(135deg, oklch(0.62 0.22 258), oklch(0.70 0.18 196))" }}
          >
            <Zap className="w-8 h-8 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-[22px] font-bold text-white leading-tight">Seller Hub</h1>
            <p className="text-[13px] text-zinc-500 mt-1">
              {seller ? `Welcome, ${seller.display_name}!` : "Welcome!"}
            </p>
          </div>
        </div>

        {/* Feature list */}
        <div className="flex flex-col gap-3">
          {ONBOARDING_STEPS.map(({ icon: Icon, color, title, desc }, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + i * 0.08, duration: 0.25 }}
              className="flex items-start gap-3 glass-card p-3.5"
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: `${color}22`, border: `1px solid ${color}33` }}
              >
                <Icon className="w-4.5 h-4.5" style={{ color }} />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-white">{title}</div>
                <div className="text-[11px] text-zinc-500 mt-0.5 leading-relaxed">{desc}</div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.button
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.25 }}
          onClick={completeOnboarding}
          className="w-full py-3.5 rounded-2xl text-white font-bold text-[15px] flex items-center justify-center gap-2 shadow-[0_0_24px_oklch(0.62_0.22_258/0.4)] transition-all active:scale-[0.98]"
          style={{ background: "linear-gradient(135deg, oklch(0.62 0.22 258), oklch(0.70 0.18 196))" }}
        >
          Get Started
          <ChevronRight className="w-5 h-5" />
        </motion.button>

        {/* Package / version note */}
        <p className="text-center text-[10px] text-zinc-700 pb-4">
          Seller Hub v2 · Obsidian Glass
        </p>
      </div>
    </motion.div>
  );
}

/* ─── App Shell ─────────────────────────────────────── */

function AppShell() {
  const { activeTab, isLoading, hasSeenOnboarding } = useApp();

  if (isLoading) {
    return (
      <div className="app-shell items-center justify-center gap-4">
        {/* Animated logo */}
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl gradient-avatar flex items-center justify-center shadow-[0_0_32px_oklch(0.62_0.22_258/0.4)]">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M8 16L14 22L24 10" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="absolute inset-0 rounded-2xl animate-ping opacity-20 gradient-avatar" />
        </div>
        <div className="text-[14px] text-zinc-500">Loading Seller Hub…</div>
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      {!hasSeenOnboarding ? (
        <OnboardingScreen key="onboarding" />
      ) : (
        <motion.div
          key="app"
          className="app-shell"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
        >
          {/* Ambient background blobs */}
          <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden>
            <div
              className="absolute -top-32 -left-32 w-64 h-64 rounded-full opacity-[0.06]"
              style={{ background: "radial-gradient(circle, oklch(0.62 0.22 258), transparent)" }}
            />
            <div
              className="absolute -bottom-32 -right-32 w-64 h-64 rounded-full opacity-[0.05]"
              style={{ background: "radial-gradient(circle, oklch(0.70 0.18 196), transparent)" }}
            />
          </div>

          <AppHeader />

          <main className="app-main">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={activeTab}
                className="tab-pane"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
              >
                {activeTab === "chats"     && <ChatsTab />}
                {activeTab === "orders"    && <OrdersTab />}
                {activeTab === "uploads"   && <UploadsTab />}
                {activeTab === "analytics" && <AnalyticsTab />}
                {activeTab === "finance"   && <FinanceTab />}
                {activeTab === "moderation" && <ModerationStatusTab />}
                {activeTab === "team"      && <TeamTab />}
                {activeTab === "settings"  && <SettingsTab />}
              </motion.div>
            </AnimatePresence>
          </main>

          <BottomNav />
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function SellerApp() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
