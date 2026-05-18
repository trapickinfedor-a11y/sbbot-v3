import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { EvomiProxyAdapter } from "./evomiProxyAdapter";

function makeConfig() {
  return {
    host: "proxy.evomi.com",
    port: 8080,
    username: "evomiuser",
    password: "evomipass",
    protocol: "http" as const,
    country: "us",
    rotateOnSuccess: 3,
    apiKey: "test_key",
    healthCheckIntervalMs: 30000,
  };
}

describe("EvomiProxyAdapter", () => {
  it("createSession returns session with id and ip", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    const session = adapter.createSession();
    expect(session.sessionId).toBeDefined();
    expect(session.sessionId.length).toBe(32);
    expect(session.assignedIp).toContain("evomi-");
    expect(session.bandwidthUsedMb).toBe(0);
  });

  it("getProxyUrl builds correct URL with session ID", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    const session = adapter.createSession();
    const url = adapter.getProxyUrl(session.sessionId);
    expect(url).toContain("proxy.evomi.com:8080");
    expect(url).toContain(`session-${session.sessionId}`);
  });

  it("getProxyUrl returns null for unknown session", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    expect(adapter.getProxyUrl("unknown-id")).toBeNull();
  });

  it("getAssignedIp returns ip for known session", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    const session = adapter.createSession();
    expect(adapter.getAssignedIp(session.sessionId)).toBe(session.assignedIp);
  });

  it("recordBandwidth accumulates bandwidth", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    const session = adapter.createSession();
    adapter.recordBandwidth(session.sessionId, 5.5);
    adapter.recordBandwidth(session.sessionId, 3.0);
    expect(adapter.getHealthStatus().totalBandwidthMb).toBe(8.5);
  });

  it("getHealthStatus returns accurate counts", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    adapter.createSession(); adapter.createSession();
    const status = adapter.getHealthStatus();
    expect(status.activeSessions).toBe(2);
    expect(status.totalBandwidthMb).toBe(0);
  });

  it("startHealthChecks / stopHealthChecks are idempotent", () => {
    const adapter = new EvomiProxyAdapter(makeConfig());
    adapter.startHealthChecks();
    adapter.startHealthChecks();
    adapter.stopHealthChecks();
    adapter.stopHealthChecks();
    expect(() => adapter.stopHealthChecks()).not.toThrow();
  });
});