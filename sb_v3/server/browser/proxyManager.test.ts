import { describe, expect, it, vi, afterEach } from "vitest";
import { ProxyManager, ProxyPool, proxyConfigFromEnv } from "./proxyManager";

const makeConfig = (overrides: Partial<{
  host: string;
  port: number;
  username: string;
  password: string;
  protocol: "http" | "socks5";
  country: string;
  rotateOnSuccess: number;
}> = {}) => ({
  host: "proxy.example.com",
  port: 8080,
  username: "testuser",
  password: "testpass",
  protocol: "http" as const,
  country: "us",
  rotateOnSuccess: 3,
  ...overrides,
});

describe("ProxyManager", () => {
  describe("constructor", () => {
    it("creates a new ProxyManager with a session ID", () => {
      const pm = new ProxyManager(makeConfig());
      expect(typeof pm.sessionId).toBe("string");
      expect(pm.sessionId.length).toBeGreaterThan(0);
    });

    it("each instance gets a unique session ID", () => {
      const pm1 = new ProxyManager(makeConfig());
      const pm2 = new ProxyManager(makeConfig());
      expect(pm1.sessionId).not.toBe(pm2.sessionId);
    });
  });

  describe("getProxyUrl", () => {
    it("builds correct proxy URL with session ID", () => {
      const config = makeConfig({ host: "proxy.test", port: 8080, username: "user", password: "pass" });
      const pm = new ProxyManager(config);
      const url = pm.getProxyUrl();
      expect(url).toContain("http://");
      expect(url).toContain("proxy.test:8080");
      expect(url).toContain("user-country-us-session-");
      expect(url).toContain("pass");
    });

    it("includes session ID in the username segment", () => {
      const pm = new ProxyManager(makeConfig());
      const url = pm.getProxyUrl();
      // Session ID is hex string, at least 8 chars
      expect(url).toMatch(/testuser-country-us-session-[a-f0-9]+/);
    });

    it("uses socks5 protocol when configured", () => {
      const config = makeConfig({ protocol: "socks5" });
      const pm = new ProxyManager(config);
      expect(pm.getProxyUrl()).toContain("socks5://");
    });

    it("reflects country in the URL", () => {
      const config = makeConfig({ country: "gb" });
      const pm = new ProxyManager(config);
      expect(pm.getProxyUrl()).toContain("country-gb");
    });
  });

  describe("onSuccess", () => {
    it("does not rotate before rotateOnSuccess threshold", () => {
      const config = makeConfig({ rotateOnSuccess: 3 });
      const pm = new ProxyManager(config);
      const initialSession = pm.sessionId;
      pm.onSuccess();
      pm.onSuccess();
      expect(pm.sessionId).toBe(initialSession);
    });

    it("rotates after rotateOnSuccess successful attempts", () => {
      const config = makeConfig({ rotateOnSuccess: 3 });
      const pm = new ProxyManager(config);
      const initialSession = pm.sessionId;
      pm.onSuccess();
      pm.onSuccess();
      expect(pm.sessionId).toBe(initialSession);
      pm.onSuccess();
      expect(pm.sessionId).not.toBe(initialSession);
    });

    it("rotates after rotateOnSuccess=1 (every request)", () => {
      const config = makeConfig({ rotateOnSuccess: 1 });
      const pm = new ProxyManager(config);
      const s1 = pm.sessionId;
      pm.onSuccess();
      expect(pm.sessionId).not.toBe(s1);
    });

    it("resets attempt counter after rotation", () => {
      const config = makeConfig({ rotateOnSuccess: 2 });
      const pm = new ProxyManager(config);
      pm.onSuccess();
      pm.onSuccess();
      const afterRotate = pm.sessionId;
      pm.onSuccess();
      expect(pm.sessionId).toBe(afterRotate);
      pm.onSuccess();
      expect(pm.sessionId).not.toBe(afterRotate);
    });
  });

  describe("onFailure", () => {
    it("rotates immediately on failure", () => {
      const pm = new ProxyManager(makeConfig());
      const initialSession = pm.sessionId;
      pm.onFailure();
      expect(pm.sessionId).not.toBe(initialSession);
    });

    it("resets attempt counter after rotation", () => {
      const config = makeConfig({ rotateOnSuccess: 5 });
      const pm = new ProxyManager(config);
      pm.onSuccess();
      pm.onSuccess();
      pm.onSuccess();
      pm.onFailure();
      const afterRotate = pm.sessionId;
      pm.onSuccess();
      pm.onSuccess();
      pm.onSuccess();
      pm.onSuccess();
      pm.onSuccess();
      expect(pm.sessionId).not.toBe(afterRotate);
    });

    it("can rotate multiple times on repeated failures", () => {
      const pm = new ProxyManager(makeConfig());
      const sessions = new Set<string>();
      sessions.add(pm.sessionId);
      for (let i = 0; i < 5; i++) {
        pm.onFailure();
        sessions.add(pm.sessionId);
      }
      expect(sessions.size).toBe(6);
    });
  });

  describe("toPlaywrightProxy", () => {
    it("returns correct structure with server, username, password", () => {
      const pm = new ProxyManager(makeConfig());
      const pw = pm.toPlaywrightProxy();
      expect(pw).toMatchObject({
        server: expect.stringContaining("http://"),
        username: expect.stringContaining("testuser"),
        password: "testpass",
      });
    });

    it("server contains host and port without auth", () => {
      const config = makeConfig({ host: "my.proxy.io", port: 3128 });
      const pm = new ProxyManager(config);
      const pw = pm.toPlaywrightProxy();
      expect(pw.server).toContain("my.proxy.io:3128");
    });

    it("username includes session ID for sticky routing", () => {
      const pm = new ProxyManager(makeConfig());
      expect(pm.toPlaywrightProxy().username).toContain("session-");
    });

    it("protocol is reflected in server URL", () => {
      const config = makeConfig({ protocol: "socks5" });
      const pm = new ProxyManager(config);
      expect(pm.toPlaywrightProxy().server).toContain("socks5://");
    });
  });
});

describe("ProxyPool", () => {
  it("creates one manager per worker based on workersPerProxy", () => {
    const configs = [makeConfig(), makeConfig()];
    const pool = new ProxyPool(configs, 2);
    expect(pool.size).toBe(4);
  });

  it("assigns managers to worker IDs sequentially", () => {
    const configs = [makeConfig({ host: "p1" }), makeConfig({ host: "p2" })];
    const pool = new ProxyPool(configs, 2);
    expect(pool.get(0)).toBeDefined();
    expect(pool.get(1)).toBeDefined();
    expect(pool.get(2)).toBeDefined();
    expect(pool.get(3)).toBeDefined();
  });

  it("returns undefined for unknown worker IDs", () => {
    const pool = new ProxyPool([makeConfig()], 1);
    expect(pool.get(999)).toBeUndefined();
  });

  it("each worker gets a manager with unique session", () => {
    const configs = [makeConfig()];
    const pool = new ProxyPool(configs, 3);
    const s0 = pool.get(0)!.sessionId;
    const s1 = pool.get(1)!.sessionId;
    const s2 = pool.get(2)!.sessionId;
    expect(new Set([s0, s1, s2]).size).toBe(3);
  });
});

describe("proxyConfigFromEnv", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when PROXY_HOST is not set", () => {
    vi.stubEnv("PROXY_HOST", "");
    expect(proxyConfigFromEnv()).toBeNull();
  });

  it("returns null when PROXY_PORT is invalid", () => {
    vi.stubEnv("PROXY_HOST", "proxy.test");
    vi.stubEnv("PROXY_PORT", "invalid");
    vi.stubEnv("PROXY_USERNAME", "user");
    vi.stubEnv("PROXY_PASSWORD", "pass");
    expect(proxyConfigFromEnv()).toBeNull();
  });

  it("returns null when username/password missing", () => {
    vi.stubEnv("PROXY_HOST", "proxy.test");
    vi.stubEnv("PROXY_PORT", "8080");
    vi.stubEnv("PROXY_USERNAME", "");
    vi.stubEnv("PROXY_PASSWORD", "");
    expect(proxyConfigFromEnv()).toBeNull();
  });

  it("returns full config when all required vars present", () => {
    vi.stubEnv("PROXY_HOST", "evomi.proxy.com");
    vi.stubEnv("PROXY_PORT", "8080");
    vi.stubEnv("PROXY_USERNAME", "evomiuser");
    vi.stubEnv("PROXY_PASSWORD", "evomipass");
    vi.stubEnv("PROXY_COUNTRY", "us");
    vi.stubEnv("WORKER_ROTATE_ON_SUCCESS", "5");
    const cfg = proxyConfigFromEnv();
    expect(cfg).toEqual({
      host: "evomi.proxy.com",
      port: 8080,
      username: "evomiuser",
      password: "evomipass",
      protocol: "http",
      country: "us",
      rotateOnSuccess: 5,
    });
  });

  it("defaults PROXY_COUNTRY to us when empty", () => {
    vi.stubEnv("PROXY_HOST", "proxy.test");
    vi.stubEnv("PROXY_PORT", "8080");
    vi.stubEnv("PROXY_USERNAME", "user");
    vi.stubEnv("PROXY_PASSWORD", "pass");
    vi.stubEnv("PROXY_COUNTRY", "");
    expect(proxyConfigFromEnv()?.country).toBe("us");
  });

  it("defaults WORKER_ROTATE_ON_SUCCESS to 3 when empty", () => {
    vi.stubEnv("PROXY_HOST", "proxy.test");
    vi.stubEnv("PROXY_PORT", "8080");
    vi.stubEnv("PROXY_USERNAME", "user");
    vi.stubEnv("PROXY_PASSWORD", "pass");
    vi.stubEnv("WORKER_ROTATE_ON_SUCCESS", "");
    expect(proxyConfigFromEnv()?.rotateOnSuccess).toBe(3);
  });
});