/**
 * Proxy manager with session-based IP rotation.
 * Ported from legacy Python credit_score_bot.
 *
 * Features:
 * - Session-sticky IPs (rotates after N successful requests)
 * - Immediate rotation on failure
 * - Proxy URL construction with session ID
 */

import { randomBytes } from "crypto";

export interface ProxyConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  protocol: "http" | "socks5";
  country: string;
  rotateOnSuccess: number;
}

export interface ProxyLease {
  proxyUrl: string;
  sessionId: string;
  config: ProxyConfig;
}

export class ProxyManager {
  private _sessionId: string;
  private _successfulAttempts = 0;

  constructor(private config: ProxyConfig) {
    this._sessionId = this._newSessionId();
  }

  getProxyUrl(): string {
    const { host, port, username, password, protocol, country } = this.config;
    const user = `${username}-country-${country}-session-${this._sessionId}`;
    return `${protocol}://${user}:${password}@${host}:${port}`;
  }

  get sessionId(): string {
    return this._sessionId;
  }

  onSuccess(): void {
    this._successfulAttempts++;
    if (this._successfulAttempts >= this.config.rotateOnSuccess) {
      this._rotate();
    }
  }

  onFailure(): void {
    this._rotate();
  }

  private _rotate(): void {
    const old = this._sessionId;
    this._sessionId = this._newSessionId();
    this._successfulAttempts = 0;
    console.log(`[ProxyManager] IP rotated: ${old} → ${this._sessionId}`);
  }

  private _newSessionId(length = 8): string {
    return randomBytes(length)
      .toString("hex")
      .slice(0, length);
  }

  /** Build playwright-compatible proxy object */
  toPlaywrightProxy(): { server: string; username: string; password: string } {
    const { host, port, username, password, protocol, country } = this.config;
    const user = `${username}-country-${country}-session-${this._sessionId}`;
    return {
      server: `${protocol}://${host}:${port}`,
      username: user,
      password,
    };
  }
}

/** Pool of proxy managers — one per worker */
export class ProxyPool {
  private managers: Map<number, ProxyManager> = new Map();

  constructor(
    configs: ProxyConfig[],
    private workersPerProxy = 2,
  ) {
    for (let i = 0; i < configs.length; i++) {
      const proxyConfig = configs[i];
      for (let w = 0; w < this.workersPerProxy; w++) {
        const workerId = i * this.workersPerProxy + w;
        this.managers.set(workerId, new ProxyManager(proxyConfig));
      }
    }
  }

  get(workerId: number): ProxyManager | undefined {
    return this.managers.get(workerId);
  }

  get size(): number {
    return this.managers.size;
  }
}

/** Singleton proxy pool — initialized from env */
let _pool: ProxyPool | null = null;

export function initProxyPool(configs: ProxyConfig[]): ProxyPool {
  _pool = new ProxyPool(configs);
  return _pool;
}

export function getProxyPool(): ProxyPool | null {
  return _pool;
}

export function proxyConfigFromEnv(): ProxyConfig | null {
  const host = process.env.PROXY_HOST;
  const port = parseInt(process.env.PROXY_PORT ?? "0", 10);
  const username = process.env.PROXY_USERNAME;
  const password = process.env.PROXY_PASSWORD;

  if (!host || !port || !username || !password) {
    return null;
  }

  return {
    host,
    port,
    username,
    password,
    protocol: (process.env.PROXY_PROTOCOL as "http" | "socks5") ?? "http",
    country: (process.env.PROXY_COUNTRY || "us") as string,
    rotateOnSuccess: (() => { const r = process.env.WORKER_ROTATE_ON_SUCCESS; return r && r !== "" ? parseInt(r, 10) : 3; })(),
  };
}