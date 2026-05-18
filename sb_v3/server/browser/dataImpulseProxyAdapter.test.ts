import { describe, expect, it } from "vitest";
import { DataImpulseProxyAdapter } from "./dataImpulseProxyAdapter";

function makeConfig() {
  return {
    host: "proxy.dataimpulse.com",
    port: 3128,
    username: "diuser",
    password: "dipass",
    protocol: "http" as const,
    country: "us",
    rotateOnSuccess: 3,
    sessionDuration: 10,
    sticky: true,
  };
}

describe("DataImpulseProxyAdapter", () => {
  it("newSessionId generates unique IDs", () => {
    const adapter = new DataImpulseProxyAdapter(makeConfig());
    const id1 = adapter.newSessionId();
    const id2 = adapter.newSessionId();
    expect(id1).not.toBe(id2);
    expect(id1.length).toBe(24);
  });

  it("getStickyProxyUrl includes session ID in username", () => {
    const adapter = new DataImpulseProxyAdapter(makeConfig());
    const url = adapter.getStickyProxyUrl("abc123");
    expect(url).toContain("diuser-session-abc123");
    expect(url).toContain("proxy.dataimpulse.com:3128");
  });

  it("getRotatingProxyUrl does not include session ID", () => {
    const adapter = new DataImpulseProxyAdapter(makeConfig());
    const url = adapter.getRotatingProxyUrl();
    expect(url).not.toContain("session-");
    expect(url).toContain("diuser:dipass");
    expect(url).toContain("proxy.dataimpulse.com:3128");
  });

  it("getStickyProxyUrl reflects country in URL", () => {
    const config = makeConfig();
    config.country = "gb";
    const adapter = new DataImpulseProxyAdapter(config);
    expect(adapter.getStickyProxyUrl("test")).toContain("country-gb");
  });

  it("getStickyProxyUrl uses correct protocol", () => {
    const config = makeConfig();
    config.protocol = "socks5";
    const adapter = new DataImpulseProxyAdapter(config);
    expect(adapter.getStickyProxyUrl("test")).toContain("socks5://");
  });
});