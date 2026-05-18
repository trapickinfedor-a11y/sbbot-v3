/**
 * DataImpulse residential proxy adapter — sticky and rotating modes.
 */
import { ProxyConfig } from "./proxyManager";
import { randomBytes } from "crypto";

export interface DataImpulseProxyAdapterConfig extends ProxyConfig {
  sessionDuration: number;
  sticky: boolean;
}

export class DataImpulseProxyAdapter {
  constructor(private config: DataImpulseProxyAdapterConfig) {}

  newSessionId(): string {
    return randomBytes(12).toString("hex");
  }

  getStickyProxyUrl(sessionId: string): string {
    const { host, port, username, password, protocol, country } = this.config;
    const user = `${username}-session-${sessionId}-country-${country}`;
    return `${protocol}://${user}:${password}@${host}:${port}`;
  }

  getRotatingProxyUrl(): string {
    const { host, port, username, password, protocol } = this.config;
    return `${protocol}://${username}:${password}@${host}:${port}`;
  }
}