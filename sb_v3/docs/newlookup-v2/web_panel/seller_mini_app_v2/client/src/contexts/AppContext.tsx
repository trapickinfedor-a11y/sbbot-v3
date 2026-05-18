/* ═══════════════════════════════════════════════════════
   App Context — Global state for Seller Hub Mini App v2
   Demo mode: uses mock data when backend is unavailable
   ═══════════════════════════════════════════════════════ */

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type Conversation, type SellerMe, type Order } from "@/lib/api";
import { initTelegram } from "@/lib/telegram";
import {
  MOCK_SELLER,
  MOCK_CONVERSATIONS,
} from "@/lib/mockData";

export type TabId = "chats" | "orders" | "uploads" | "analytics" | "finance" | "moderation" | "team" | "settings";
export type AppLanguage = "en" | "ru" | "es" | "zh";

/* ─── Notification type ─────────────────────────────── */

export interface AppNotification {
  id: string;
  type: "order" | "dispute" | "moderation" | "finance" | "system";
  title: string;
  body: string;
  timestamp: string;
  read: boolean;
  tab?: TabId;
}

const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: "n1",
    type: "order",
    title: "New Order #1006",
    body: "Buyer #7723 purchased Chase Business — $120",
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    read: false,
    tab: "orders",
  },
  {
    id: "n2",
    type: "dispute",
    title: "Dispute Opened",
    body: "Buyer #5590 opened a dispute on Order #1003",
    timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
    read: false,
    tab: "orders",
  },
  {
    id: "n3",
    type: "moderation",
    title: "Batch Approved",
    body: "Your Wells Fargo Brute batch (50 items) was approved",
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    read: true,
    tab: "uploads",
  },
  {
    id: "n4",
    type: "finance",
    title: "Payout Processed",
    body: "Auto-payout of $500 sent to your wallet",
    timestamp: new Date(Date.now() - 6 * 3600000).toISOString(),
    read: true,
    tab: "finance",
  },
  {
    id: "n5",
    type: "system",
    title: "System Update",
    body: "Seller Hub v2.4 — new CC single form with structured fields",
    timestamp: new Date(Date.now() - 24 * 3600000).toISOString(),
    read: true,
  },
];

/* ─── Language labels ───────────────────────────────── */

export const LANGUAGE_LABELS: Record<AppLanguage, string> = {
  en: "🇺🇸 EN",
  ru: "🇷🇺 RU",
  es: "🇪🇸 ES",
  zh: "🇨🇳 ZH",
};

/* ─── State & Actions interfaces ────────────────────── */

interface AppState {
  seller: SellerMe | null;
  conversations: Conversation[];
  unreadTotal: number;
  activeTab: TabId;
  isLoading: boolean;
  error: string | null;
  isDemoMode: boolean;
  // Notifications
  notifications: AppNotification[];
  unreadNotifications: number;
  // Orders badge
  activeOrdersCount: number;
  // Language
  language: AppLanguage;
  // Onboarding
  hasSeenOnboarding: boolean;
}

interface AppActions {
  setTab: (tab: TabId) => void;
  refreshConversations: () => Promise<void>;
  refreshSeller: () => Promise<void>;
  // Notifications
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  // Language
  setLanguage: (lang: AppLanguage) => void;
  // Onboarding
  completeOnboarding: () => void;
}

const AppContext = createContext<(AppState & AppActions) | null>(null);

/* ─── Provider ──────────────────────────────────────── */

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [seller, setSeller] = useState<SellerMe | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("chats");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>(MOCK_NOTIFICATIONS);
  const [activeOrdersCount, setActiveOrdersCount] = useState(0);
  const [language, setLanguageState] = useState<AppLanguage>(() => {
    const saved = localStorage.getItem("seller_hub_lang");
    return (saved as AppLanguage) ?? "en";
  });
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState(() => {
    return localStorage.getItem("seller_hub_onboarded") === "1";
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshSeller = useCallback(async () => {
    try {
      const data = await api.me();
      setSeller(data);
      setIsDemoMode(false);
    } catch {
      setSeller(MOCK_SELLER);
      setIsDemoMode(true);
    }
  }, []);

  const refreshConversations = useCallback(async () => {
    if (isDemoMode) {
      setConversations(MOCK_CONVERSATIONS);
      return;
    }
    try {
      const data = await api.conversations();
      setConversations(data);
    } catch {
      setConversations(MOCK_CONVERSATIONS);
      setIsDemoMode(true);
    }
  }, [isDemoMode]);

  // Fetch active orders count for BottomNav badge
  const refreshOrdersCount = useCallback(async () => {
    if (isDemoMode) {
      setActiveOrdersCount(0);
      return;
    }
    try {
      const data = await api.orders("active");
      const count = data.items.filter(o => ["approved", "in_progress"].includes(o.status)).length;
      setActiveOrdersCount(count);
    } catch {
      setActiveOrdersCount(0);
    }
  }, [isDemoMode]);

  useEffect(() => {
    initTelegram();
    const init = async () => {
      setIsLoading(true);
      try {
        await refreshSeller();
        await refreshConversations();
        await refreshOrdersCount();
      } finally {
        setIsLoading(false);
      }
    };
    init();

    // Poll conversations every 15s
    pollRef.current = setInterval(() => {
      refreshConversations();
    }, 15000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unreadTotal = conversations.reduce((a, c) => a + (c.unread_count || 0), 0);
  const unreadNotifications = notifications.filter(n => !n.read).length;

  const setTab = useCallback((tab: TabId) => {
    setActiveTab(tab);
  }, []);

  const markNotificationRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const markAllNotificationsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const setLanguage = useCallback((lang: AppLanguage) => {
    setLanguageState(lang);
    localStorage.setItem("seller_hub_lang", lang);
  }, []);

  const completeOnboarding = useCallback(() => {
    setHasSeenOnboarding(true);
    localStorage.setItem("seller_hub_onboarded", "1");
  }, []);

  return (
    <AppContext.Provider
      value={{
        seller,
        conversations,
        unreadTotal,
        activeTab,
        isLoading,
        error,
        isDemoMode,
        notifications,
        unreadNotifications,
        activeOrdersCount,
        language,
        hasSeenOnboarding,
        setTab,
        refreshConversations,
        refreshSeller,
        markNotificationRead,
        markAllNotificationsRead,
        setLanguage,
        completeOnboarding,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
