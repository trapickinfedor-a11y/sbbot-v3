/**
 * Evomi proxy adapter — session-sticky IPs with health monitoring and bandwidth tracking.
 */
import { ProxyConfig } from "./proxyManager";
import { randomBytes } from "crypto";

export interface EvomiProxyAdapterConfig extends ProxyConfig {
  apiKey: string;
  healthCheckIntervalMs: number;
}

export interface EvomiSession {
  sessionId: string;
  assignedIp: string;
  expiresAt: Date;
  bandwidthUsedMb: number;
}

export class EvomiProxyAdapter {
  private sessions: Map<string, EvomiSession> = new Map();
  private healthCheckTimer: NodeJS.Timeout | null = null;

  constructor(private config: EvomiProxyAdapterConfig) {}

  createSession(country?: string): EvomiSession {
    const sessionId = randomBytes(16).toString("hex");
    const session: EvomiSession = {
      sessionId,
      assignedIp: `evomi-${sessionId.slice(0, 12)}`,
      expiresAt: new Date(Date.now() + 10 * 60 * 1000),
      bandwidthUsedMb: 0,
    };
    this.sessions.set(sessionId, session);
    return session;
  }

  getProxyUrl(sessionId: string): string | null {
    const session = this.sessions.get(sessionId);
    if (!session) return null;
    const { host, port, username, password, protocol, country } = this.config;
    const user = `${username}-country-${country ?? this.config.country}-session-${sessionId}`;
    return `${protocol}://${user}:${password}@${host}:${port}`;
  }

  getAssignedIp(sessionId: string): string | null {
    return this.sessions.get(sessionId)?.assignedIp ?? null;
  }

  recordBandwidth(sessionId: string, mb: number): void {
    const session = this.sessions.get(sessionId);
    if (session) session.bandwidthUsedMb += mb;
  }

  getHealthStatus(): { activeSessions: number; totalBandwidthMb: number } {
    let total = 0;
    Array.from(this.sessions.values()).forEach(s => { total += s.bandwidthUsedMb; });
    return { activeSessions: this.sessions.size, totalBandwidthMb: total };
  }

  startHealthChecks(): void {
    this.stopHealthChecks();
    const interval = this.config.healthCheckIntervalMs ?? 30000;
    this.healthCheckTimer = setInterval(() => {
      const now = Date.now();
      Array.from(this.sessions.entries()).forEach(([id, session]) => {
        if (session.expiresAt.getTime() < now) this.sessions.delete(id);
      });
    }, interval);
  }

  stopHealthChecks(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }
}