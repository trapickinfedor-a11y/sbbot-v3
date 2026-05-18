import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = {
  queries: {
    overview: { data: null as any, isLoading: false, error: null as Error | null },
    telemetry: { data: null as any, isLoading: false, error: null as Error | null },
    jobs: { data: [] as any[], isLoading: false, error: null as Error | null },
    proxies: { data: null as any, isLoading: false, error: null as Error | null },
    workers: { data: null as any, isLoading: false, error: null as Error | null },
    billing: { data: null as any, isLoading: false, error: null as Error | null },
  },
};

vi.mock("@/components/DashboardLayout", () => ({
  default: ({ children }: { children: React.ReactNode }) => React.createElement("div", { "data-testid": "dashboard-layout" }, children),
}));

vi.mock("wouter", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => React.createElement("a", { href }, children),
}));

vi.mock("@/lib/trpc", () => ({
  trpc: {
    platform: {
      overview: {
        useQuery: () => state.queries.overview,
      },
    },
    telemetry: {
      summary: {
        useQuery: () => state.queries.telemetry,
      },
    },
    jobs: {
      list: {
        useQuery: () => state.queries.jobs,
      },
    },
    proxies: {
      summary: {
        useQuery: () => state.queries.proxies,
      },
    },
    workers: {
      summary: {
        useQuery: () => state.queries.workers,
      },
    },
    billing: {
      summary: {
        useQuery: () => state.queries.billing,
      },
    },
  },
}));

import Overview from "./Overview";

function resetState() {
  state.queries.overview = {
    data: {
      metrics: [
        { key: "success", title: "Success Rate", value: "98.4%", delta: "+1.2% vs 24h" },
        { key: "queue", title: "Queue Depth", value: "12", delta: "3 VIP / 4 bulk / 5 default" },
      ],
      health: {
        status: "healthy",
        queues: {
          default: { depth: 5, lagSeconds: 12 },
        },
        providers: {
          evomi: { status: "healthy", successRate: 0.981, avgLeaseMs: 320 },
        },
      },
      auditTrail: [],
      safeTestScenarios: [
        {
          code: "safe-import-preview",
          title: "Safe import preview",
          description: "Preview incoming rows without runtime side effects.",
          expectedOutcome: "Preview renders normalized records.",
        },
      ],
    },
    isLoading: false,
    error: null,
  };

  state.queries.telemetry = {
    data: {
      successRate: 1,
      health: {
        status: "healthy",
        queues: {
          default: { depth: 5, lagSeconds: 12 },
        },
        providers: {
          evomi: { status: "healthy", successRate: 0.981, avgLeaseMs: 320 },
        },
      },
      recentAudit: [],
    },
    isLoading: false,
    error: null,
  };

  state.queries.jobs = {
    data: [],
    isLoading: false,
    error: null,
  };

  state.queries.proxies = {
    data: {
      providers: [],
    },
    isLoading: false,
    error: null,
  };

  state.queries.workers = {
    data: {
      workers: [],
    },
    isLoading: false,
    error: null,
  };

  state.queries.billing = {
    data: {
      plans: [],
      payments: [],
      subscriptions: [],
      usageSummary: null,
    },
    isLoading: false,
    error: null,
  };
}

function renderPage() {
  return renderToStaticMarkup(React.createElement(Overview));
}

describe("overview page", () => {
  beforeEach(() => {
    resetState();
  });

  it("renders operator incident snapshot with escalation path to All Logs Chat", () => {
    state.queries.jobs.data = [
      {
        publicId: "job_1",
        targetLabel: "Alice Example",
        requestMode: "single",
        source: "api",
        status: "failed",
        resultJson: null,
        queueName: "default",
      },
      {
        publicId: "job_2",
        targetLabel: "Bob Example",
        requestMode: "bulk",
        source: "admin",
        status: "waiting_retry",
        resultJson: null,
        queueName: "bulk",
      },
    ];

    state.queries.telemetry.data.recentAudit = [
      {
        action: "api_key.revoked",
        resourceType: "api_key",
        resourceId: "key_9",
        status: "denied",
        createdAt: "2026-04-03T09:05:00.000Z",
      },
    ];

    const html = renderPage();

    expect(html).toContain("Operator incident snapshot");
    expect(html).toContain("Attention required");
    expect(html).toContain("Failed jobs");
    expect(html).toContain("Waiting retry");
    expect(html).toContain("Denied audit");
    expect(html).toContain("Operator action queue");
    expect(html).toContain("Investigate failed jobs");
    expect(html).toContain("Review retry backlog");
    expect(html).toContain("Confirm denied audit events");
    expect(html).toContain("Open All Logs Chat");
    expect(html).toContain("Open Metrics");
    expect(html).toContain("Open System");
    expect(html).toContain("Open live log focus");
    expect(html).toContain("href=\"/log-chat\"");
    expect(html).toContain("All Logs Chat");
    expect(html).toContain("Metrics");
    expect(html).toContain("System");
    expect(html).toContain("href=\"/safe-bench\"");
  });

  it("keeps overview quick jumps visible in stable posture", () => {
    state.queries.jobs.data = [
      {
        publicId: "job_ok",
        targetLabel: "Charlie Example",
        requestMode: "single",
        source: "api",
        status: "succeeded",
        resultJson: {
          oneCsResult: {
            creditScore: 701,
            productScore: 16,
            dataQualityScore: 8,
            status: "approved",
          },
        },
        queueName: "vip",
      },
    ];

    const html = renderPage();

    expect(html).toContain("Stable");
    expect(html).toContain("href=\"/logs\"");
    expect(html).toContain("Logs");
    expect(html).toContain("Safe Bench");
    expect(html).toContain("href=\"/safe-bench\"");
    expect(html).toContain("href=\"/system\"");
    expect(html).toContain("Operator action queue");
    expect(html).toContain("No immediate actions");
    expect(html).toContain("Quick operator jumps");
  });
});
