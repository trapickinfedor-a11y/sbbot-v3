import { describe, expect, it } from "vitest";
import { adminRoutes } from "../App";
import { pageMeta, resolvePageKey } from "./Operations";

describe("admin panel route mapping", () => {
  it("registers all major admin routes as separate entries", () => {
    expect(adminRoutes).toEqual([
      "/",
      "/imported-data",
      "/jobs",
      "/proxy",
      "/workers",
      "/billing",
      "/revenue",
      "/logs",
      "/log-chat",
      "/metrics",
      "/telemetry",
      "/system",
      "/safe-bench",
      "/bot-texts",
      "/broadcasts",
    ]);
  });

  it("maps each operations path to the expected module key", () => {
    expect(resolvePageKey("/jobs")).toBe("jobs");
    expect(resolvePageKey("/proxy")).toBe("proxy");
    expect(resolvePageKey("/workers")).toBe("workers");
    expect(resolvePageKey("/billing")).toBe("billing");
    expect(resolvePageKey("/revenue")).toBe("revenue");
    expect(resolvePageKey("/logs")).toBe("logs");
    expect(resolvePageKey("/log-chat")).toBe("logchat");
    expect(resolvePageKey("/metrics")).toBe("telemetry");
    expect(resolvePageKey("/telemetry")).toBe("telemetry");
    expect(resolvePageKey("/system")).toBe("system");
    expect(resolvePageKey("/safe-bench")).toBe("safebench");
    expect(resolvePageKey("/bot-texts")).toBe("bottexts");
    expect(resolvePageKey("/broadcasts")).toBe("broadcasts");
  });

  it("keeps a dedicated metadata entry for each typed-query operations section", () => {
    expect(Object.keys(pageMeta).sort()).toEqual([
      "billing",
      "bottexts",
      "broadcasts",
      "jobs",
      "logchat",
      "logs",
      "proxy",
      "revenue",
      "safebench",
      "system",
      "telemetry",
      "workers",
    ]);
    expect(pageMeta.jobs.title).toBe("Jobs");
    expect(pageMeta.proxy.title).toBe("Proxy");
    expect(pageMeta.workers.title).toBe("Workers");
    expect(pageMeta.billing.title).toBe("Billing");
    expect(pageMeta.revenue.title).toBe("Revenue");
    expect(pageMeta.logs.title).toBe("Logs");
    expect(pageMeta.logchat.title).toBe("All Logs Chat");
    expect(pageMeta.telemetry.title).toBe("Metrics");
    expect(pageMeta.bottexts.title).toBe("Bot Texts");
    expect(pageMeta.broadcasts.title).toBe("Broadcasts");
    expect(pageMeta.system.title).toBe("System");
    expect(pageMeta.safebench.title).toBe("Safe Bench");
  });
});
