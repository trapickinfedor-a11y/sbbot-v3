/**
 * FSM — session store for Telegram bot state machine.
 */
import { Locale } from "./i18n";

export type BotState = "idle" | "awaiting_name" | "awaiting_state" | "processing" | "error";

export interface UserSession {
  state: BotState;
  locale: Locale;
  userId: number;
  name?: string;
  state_?: string;
  lastResult?: { score: number | null; productScore: number; dataQuality: number; status: string };
  isAdmin: boolean;
  createdAt: Date;
}

const SESSION_TTL_MS = 30 * 60 * 1000;

export class SessionStore {
  private sessions = new Map<number, UserSession>();

  get(userId: number): UserSession | undefined { return this.sessions.get(userId); }
  set(userId: number, session: UserSession): void { this.sessions.set(userId, session); }
  update(userId: number, patch: Partial<UserSession>): void {
    const existing = this.sessions.get(userId);
    if (existing) this.sessions.set(userId, { ...existing, ...patch });
  }
  clear(userId: number): void { this.sessions.delete(userId); }
  gc(): void {
    const cutoff = Date.now() - SESSION_TTL_MS;
    Array.from(this.sessions.entries()).forEach(([userId, session]) => {
      if (session.createdAt.getTime() < cutoff) this.sessions.delete(userId);
    });
  }
}

export const sessionStore = new SessionStore();