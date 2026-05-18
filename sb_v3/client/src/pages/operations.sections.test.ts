import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = {
  location: "/jobs",
  queries: {
    jobs: { data: [], isLoading: false, error: null },
    proxy: { data: null, isLoading: false, error: null },
    workers: { data: null, isLoading: false, error: null },
    billing: { data: null, isLoading: false, error: null },
    revenue: { data: null, isLoading: false, error: null },
    logs: { data: null, isLoading: false, error: null },
    apiKeys: { data: [], isLoading: false, error: null },
    telemetry: { data: null, isLoading: false, error: null },
    system: { data: null, isLoading: false, error: null },
    botTexts: { data: null, isLoading: false, error: null },
    broadcasts: { data: null, isLoading: false, error: null },
  },
};

vi.mock("wouter", () => ({
  useLocation: () => [state.location, vi.fn()],
}));

vi.mock("@/components/DashboardLayout", () => ({
  default: ({ children }: { children: React.ReactNode }) => React.createElement("div", { "data-testid": "dashboard-layout" }, children),
}));

vi.mock("@/lib/trpc", () => ({
  trpc: {
    useUtils: () => ({
      apiKeys: {
        list: { invalidate: vi.fn(async () => undefined) },
        usage: { invalidate: vi.fn(async () => undefined) },
      },
      billing: {
        summary: { invalidate: vi.fn(async () => undefined) },
      },
      telemetry: {
        summary: { invalidate: vi.fn(async () => undefined) },
      },
      logs: {
        summary: { invalidate: vi.fn(async () => undefined) },
      },
      botTexts: {
        summary: { invalidate: vi.fn(async () => undefined) },
      },
      broadcasts: {
        summary: { invalidate: vi.fn(async () => undefined) },
      },
    }),
    jobs: {
      list: {
        useQuery: () => state.queries.jobs,
      },
    },
    proxies: {
      summary: {
        useQuery: () => state.queries.proxy,
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
    revenue: {
      summary: {
        useQuery: () => state.queries.revenue,
      },
    },
    logs: {
      summary: {
        useQuery: () => state.queries.logs,
      },
    },
    apiKeys: {
      list: {
        useQuery: () => state.queries.apiKeys,
      },
      create: {
        useMutation: (options?: { onSuccess?: (result: { preview: string; record: { id: number; scope: string } }) => unknown }) => ({
          isPending: false,
          mutateAsync: vi.fn(async () => {
            const result = {
              preview: "cs_vip_mocktoken",
              record: { id: 999, scope: "vip" },
            };
            await options?.onSuccess?.(result);
            return result;
          }),
        }),
      },
      revoke: {
        useMutation: () => ({
          isPending: false,
          mutateAsync: vi.fn(async () => undefined),
        }),
      },
      usage: {
        useQuery: () => ({ data: null, isLoading: false, error: null }),
      },
    },
    telemetry: {
      summary: {
        useQuery: () => state.queries.telemetry,
      },
    },
    platform: {
      system: {
        useQuery: () => state.queries.system,
      },
    },
    botTexts: {
      summary: {
        useQuery: () => state.queries.botTexts,
      },
      update: {
        useMutation: () => ({
          isPending: false,
          mutateAsync: vi.fn(async (payload: { key: string; title: string; description?: string; body: string }) => ({
            key: payload.key,
            title: payload.title,
            description: payload.description ?? "",
            body: payload.body,
          })),
        }),
      },
    },
    broadcasts: {
      summary: {
        useQuery: () => state.queries.broadcasts,
      },
      create: {
        useMutation: () => ({
          isPending: false,
          mutateAsync: vi.fn(async (payload: { dryRun?: boolean }) => ({
            dryRun: Boolean(payload.dryRun),
            deliveredCount: 1,
            requestedRecipients: 1,
            results: [],
          })),
        }),
      },
    },
  },
}));

import Operations from "./Operations";

function resetState() {
  state.location = "/jobs";
  state.queries.jobs = { data: [], isLoading: false, error: null };
  state.queries.proxy = { data: null, isLoading: false, error: null };
  state.queries.workers = { data: null, isLoading: false, error: null };
  state.queries.billing = { data: null, isLoading: false, error: null };
  state.queries.revenue = { data: null, isLoading: false, error: null };
  state.queries.logs = { data: null, isLoading: false, error: null };
  state.queries.apiKeys = { data: [], isLoading: false, error: null };
  state.queries.telemetry = { data: null, isLoading: false, error: null };
  state.queries.system = { data: null, isLoading: false, error: null };
  state.queries.botTexts = { data: null, isLoading: false, error: null };
  state.queries.broadcasts = { data: null, isLoading: false, error: null };
}

function renderPage(pathname: string) {
  state.location = pathname;
  return renderToStaticMarkup(React.createElement(Operations));
}

describe("admin operations sections", () => {
  beforeEach(() => {
    resetState();
  });

  it("shows a shared loading banner while typed queries are refreshing", () => {
    state.queries.jobs = { data: [], isLoading: true, error: null };

    const html = renderPage("/jobs");

    expect(html).toContain("Loading module snapshot");
    expect(html).toContain("Typed queries are refreshing the current admin section");
  });

  it("surfaces module query errors in the shared alert area", () => {
    state.queries.billing = {
      data: null,
      isLoading: false,
      error: { message: "billing summary unavailable" },
    };

    const html = renderPage("/billing");

    expect(html).toContain("Module data error");
    expect(html).toContain("billing summary unavailable");
  });

  it("renders the Jobs empty state when there are no jobs", () => {
    const html = renderPage("/jobs");

    expect(html).toContain("Job list");
    expect(html).toContain("No jobs available");
  });

  it("renders Proxy providers, policies and health rows when data is present", () => {
    state.queries.proxy = {
      data: {
        providers: [
          {
            code: "evomi",
            name: "Evomi",
            protocolSupport: "http/https",
            status: "healthy",
            priority: 1,
            costPerGbUsd: 2.5,
          },
        ],
        policies: [
          {
            code: "default-sticky",
            name: "Default sticky",
            protocol: "http",
            sessionMode: "sticky",
            maxTransportRetries: 2,
            isDefault: "yes",
          },
        ],
        providerHealth: [
          {
            code: "evomi",
            name: "Evomi",
            status: "healthy",
            healthScore: 0.98,
            lastCheckedAt: "2026-04-03T10:00:00.000Z",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/proxy");

    expect(html).toContain("Providers");
    expect(html).toContain("Default sticky");
    expect(html).toContain("Evomi");
    expect(html).toContain("Policies and health");
  });

  it("renders Workers data-present state with worker nodes and recommendations", () => {
    state.queries.workers = {
      data: {
        workers: [
          {
            code: "worker-a",
            name: "Worker A",
            hostLabel: "host-a",
            status: "healthy",
            role: "default",
            activeJobs: 2,
            concurrencyLimit: 6,
          },
        ],
        recommendations: ["Increase retry visibility for bulk queue"],
        queueHealth: {
          default: { depth: 5, lagSeconds: 12 },
        },
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/workers");

    expect(html).toContain("Worker nodes");
    expect(html).toContain("Worker A");
    expect(html).toContain("Increase retry visibility for bulk queue");
    expect(html).toContain("Depth 5");
  });

  it("renders Billing data-present state with plans, payments, usage and api keys", () => {
    state.queries.billing = {
      data: {
        plans: [
          {
            code: "pro",
            name: "Pro",
            tier: "pro",
            currency: "USD",
            priceUsd: 49,
            monthlyApiQuota: 15000,
            monthlyBrowserRuns: 80,
            maxRpm: 120,
            maxConcurrentJobs: 4,
            vipApiAccess: true,
            features: ["priority-support"],
          },
        ],
        subscriptions: [
          {
            id: 7,
            provider: "crypto-bot",
            status: "active",
            planCode: "pro",
            requestCount: 120,
            browserRunsUsed: 18,
            vipApiAccess: true,
          },
        ],
        payments: [
          {
            id: 15,
            invoiceRef: "INV-015",
            status: "confirmed",
            currency: "USD",
            amount: 49,
            amountUsd: 49,
            provider: "stripe",
          },
        ],
        usageSummary: {
          requests: 120,
          browserRuns: 18,
          revenueUsd: 49,
          marginUsd: 31,
        },
      },
      isLoading: false,
      error: null,
    };
    state.queries.apiKeys = {
      data: [
        {
          id: 2,
          label: "VIP ingestion key",
          keyPrefix: "vip_abc",
          scope: "vip",
          status: "active",
          rpmLimit: 300,
          dailyLimit: 25000,
          lastUsedAt: "2026-04-03T10:00:00.000Z",
          expiresAt: null,
        },
      ],
      isLoading: false,
      error: null,
    };

    const html = renderPage("/billing");

    expect(html).toContain("Plans and subscriptions");
    expect(html).toContain("Pro");
    expect(html).toContain("Subscription #7");
    expect(html).toContain("Payment #15");
    expect(html).toContain("VIP ingestion key");
    expect(html).toContain("Browser runs");
    expect(html).toContain("API key issuance");
    expect(html).toContain("Create API key");
  });

  it("renders Revenue analytics with KPI slices, filters and recent payments", () => {
    state.queries.revenue = {
      data: {
        overview: {
          totalCollectedUsd: 148,
          estimatedMrrUsd: 79,
          refundedUsd: 12,
          activeSubscriptions: 3,
          usageRevenueUsd: 148,
          usageCogsUsd: 52,
          usageMarginUsd: 96,
          currentPeriod: "2026-04",
        },
        usageSummary: {
          revenueUsd: 148,
          cogsUsd: 52,
          marginUsd: 96,
          currentPeriod: "2026-04",
        },
        revenueByMonth: [
          {
            periodKey: "2026-04",
            collectedUsd: 148,
            refundedUsd: 12,
            pendingUsd: 19,
            paymentCount: 4,
          },
        ],
        providerBreakdown: [
          {
            provider: "stripe",
            collectedUsd: 148,
            refundedUsd: 12,
            pendingUsd: 19,
            paymentCount: 4,
          },
        ],
        planBreakdown: [
          {
            planCode: "pro",
            planName: "Pro",
            tier: "pro",
            collectedUsd: 148,
            paymentCount: 4,
            activeSubscriptions: 3,
          },
        ],
        recentPayments: [
          {
            id: 31,
            invoiceRef: "INV-031",
            status: "confirmed",
            provider: "stripe",
            amountUsd: 79,
            planName: "Pro",
            paidAt: "2026-04-03T10:00:00.000Z",
          },
          {
            id: 32,
            invoiceRef: "INV-032",
            status: "refunded",
            provider: "cryptomus",
            amountUsd: 12,
            planName: "Pro",
            paidAt: "2026-04-03T11:00:00.000Z",
          },
          {
            id: 33,
            invoiceRef: "INV-033",
            status: "pending",
            provider: "stripe",
            amountUsd: 19,
            planName: "Starter",
            createdAt: "2026-04-03T12:00:00.000Z",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/revenue");

    expect(html).toContain("Monthly revenue timeline");
    expect(html).toContain("Collected revenue");
    expect(html).toContain("Provider breakdown");
    expect(html).toContain("Plan breakdown");
    expect(html).toContain("Recent payments");
    expect(html).toContain("Paid / confirmed");
    expect(html).toContain("Refunded payments");
    expect(html).toContain("Pending payments");
    expect(html).toContain("Visible after filters");
    expect(html).toContain("Payment status");
    expect(html).toContain("Provider");
    expect(html).toContain("All payments");
    expect(html).toContain("Confirmed only");
    expect(html).toContain("Refunded only");
    expect(html).toContain("Pending only");
    expect(html).toContain("INV-031");
    expect(html).toContain("INV-032");
  });

  it("renders Logs data-present state with counters, pinned critical events and operator log chat", () => {
    state.queries.logs = {
      data: {
        counters: {
          total: 2,
          sources: { audit: 1, job_event: 1 },
          severity: { info: 0, warn: 1, error: 1 },
        },
        timeline: [
          {
            id: "log-1",
            source: "job_event",
            severity: "error",
            status: "failure",
            title: "provider_timeout",
            message: "Primary provider timed out during lease renewal.",
            createdAt: "2026-04-03T09:00:00.000Z",
            resourceType: "job",
            resourceId: "job_1",
            actorLabel: "worker-a",
            ipAddress: "127.0.0.1",
            details: { provider: "evomi" },
          },
          {
            id: "log-2",
            source: "audit",
            severity: "warn",
            status: "denied",
            title: "api_key.revoked",
            message: "Admin revoked a leaked API key.",
            createdAt: "2026-04-03T09:05:00.000Z",
            resourceType: "api_key",
            resourceId: "key_9",
            actorLabel: "owner",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/logs");

    expect(html).toContain("Operator log chat");
    expect(html).toContain("Log counters");
    expect(html).toContain("Pinned critical events");
    expect(html).toContain("Critical entries");
    expect(html).toContain("Visible now: 2");
    expect(html).toContain("provider_timeout");
    expect(html).toContain("api_key.revoked");
    expect(html).toContain("127.0.0.1");
  });

  it("renders All Logs Chat as a standalone full stream view", () => {
    state.queries.logs = {
      data: {
        counters: {
          total: 2,
          sources: { audit: 1, job_event: 1 },
          severity: { info: 0, warn: 1, error: 1 },
        },
        timeline: [
          {
            id: "log-1",
            source: "job_event",
            severity: "error",
            status: "failure",
            title: "provider_timeout",
            message: "Primary provider timed out during lease renewal.",
            createdAt: "2026-04-03T09:00:00.000Z",
            resourceType: "job",
            resourceId: "job_1",
            actorLabel: "worker-a",
            ipAddress: "127.0.0.1",
            details: { provider: "evomi" },
          },
          {
            id: "log-2",
            source: "audit",
            severity: "warn",
            status: "denied",
            title: "api_key.revoked",
            message: "Admin revoked a leaked API key.",
            createdAt: "2026-04-03T09:05:00.000Z",
            resourceType: "api_key",
            resourceId: "key_9",
            actorLabel: "owner",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/log-chat");

    expect(html).toContain("All logs chat");
    expect(html).toContain("Read only");
    expect(html).toContain("Total stream: 2");
    expect(html).toContain("provider_timeout");
    expect(html).toContain("api_key.revoked");
  });

  it("renders Proxy empty state when providers, policies and health rows are absent", () => {
    const html = renderPage("/proxy");

    expect(html).toContain("Proxy module is empty");
    expect(html).toContain("Когда proxy summary вернёт провайдеров и policy");
  });

  it("renders Workers empty state when worker rows and queue posture are absent", () => {
    const html = renderPage("/workers");

    expect(html).toContain("Workers module is empty");
    expect(html).toContain("Когда workers summary вернёт узлы и queue health");
  });

  it("renders Billing empty state when plans, subscriptions, payments and keys are absent", () => {
    const html = renderPage("/billing");

    expect(html).toContain("Billing module is empty");
    expect(html).toContain("Когда billing summary вернёт тарифы, подписки и платежи");
  });

  it("renders Revenue empty state when analytics payload is absent", () => {
    const html = renderPage("/revenue");

    expect(html).toContain("Revenue module is empty");
    expect(html).toContain("Когда revenue summary вернёт collected revenue");
  });

  it("renders Logs empty state when timeline payload is absent", () => {
    const html = renderPage("/logs");

    expect(html).toContain("Logs module is empty");
    expect(html).toContain("Когда logs summary вернёт audit trail и job events");
  });

  it("renders All Logs Chat empty state when standalone stream payload is absent", () => {
    const html = renderPage("/log-chat");

    expect(html).toContain("All logs chat is empty");
    expect(html).toContain("отдельный полноформатный чат со всеми логами");
  });

  it("renders Metrics health counters and telemetry incident overview", () => {
    state.queries.telemetry = {
      data: {
        successRate: 0.984,
        retryRate: 0.021,
        jobStatusCounts: {
          total: 24,
          succeeded: 18,
          failed: 3,
          running: 2,
          canceled: 1,
          waiting_retry: 1,
        },
        health: {
          status: "degraded",
          workers: { healthy: 3 },
          queues: {
            bulk: { depth: 7, lagSeconds: 42 },
            vip: { depth: 0, lagSeconds: 0 },
          },
          providers: {
            lease_proxy: { status: "degraded", successRate: 0.92, leaseP95Ms: 640 },
            reserve_proxy: { status: "healthy", successRate: 0.995, leaseP95Ms: 180 },
          },
        },
        recentAudit: [
          {
            action: "api_key.denied",
            resourceType: "api_key",
            resourceId: "key_7",
            status: "denied",
            createdAt: "2026-04-03T10:00:00.000Z",
          },
          {
            action: "job.retry_failed",
            resourceType: "job",
            resourceId: "job_11",
            status: "failure",
            createdAt: "2026-04-03T10:02:00.000Z",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/metrics");

    expect(html).toContain("Health counters");
    expect(html).toContain("Telemetry incidents");
    expect(html).toContain("Failed jobs");
    expect(html).toContain("Running jobs");
    expect(html).toContain("Canceled jobs");
    expect(html).toContain("Problem queues");
    expect(html).toContain("Problem providers");
    expect(html).toContain("bulk");
    expect(html).toContain("Lag 42s");
    expect(html).toContain("lease_proxy");
    expect(html).toContain("Success 92.0%");
    expect(html).toContain("api_key.denied");
    expect(html).toContain("job.retry_failed");
  });

  it("renders System data-present state with readiness, safe scenarios and runbooks", () => {
    state.queries.system = {
      data: {
        readinessSnapshot: [
          {
            code: "safe-bench-isolation",
            label: "Safe bench isolation",
            status: "ready",
            detail: "External protected flows stay excluded from the operator test bench.",
          },
        ],
        safeTestScenarios: [
          {
            code: "safe-import-preview",
            title: "Safe import preview",
            description: "Preview imported records without touching external systems.",
          },
        ],
        stabilizationChecklist: ["Confirm retry alerts before enabling new queues"],
        rolloutRunbook: ["Promote changes incrementally after automated checks and manual verification."],
        rollbackRunbook: ["Rollback to the latest confirmed checkpoint when health degrades."],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/system");

    expect(html).toContain("Readiness snapshot");
    expect(html).toContain("Safe bench isolation");
    expect(html).toContain("ready");
    expect(html).toContain("Safe test scenarios");
    expect(html).toContain("Safe import preview");
    expect(html).toContain("Stabilization checklist");
    expect(html).toContain("Confirm retry alerts before enabling new queues");
    expect(html).toContain("Rollout runbook");
    expect(html).toContain("Promote changes incrementally after automated checks and manual verification.");
    expect(html).toContain("Rollback runbook");
    expect(html).toContain("Rollback to the latest confirmed checkpoint when health degrades.");
  });

  it("renders Safe Bench data-present state with rollback runbook and quick exits", () => {
    state.queries.system = {
      data: {
        readinessSnapshot: [
          {
            code: "safe-bench-isolation",
            label: "Safe bench isolation",
            status: "ready",
            detail: "External protected flows stay excluded from the operator test bench.",
          },
        ],
        safeTestScenarios: [
          {
            code: "safe-import-preview",
            title: "Safe import preview",
            description: "Preview imported records without touching external systems.",
          },
        ],
        rolloutRunbook: ["Promote changes incrementally after automated checks and manual verification."],
        rollbackRunbook: ["Rollback to the latest confirmed checkpoint when health degrades."],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/safe-bench");

    expect(html).toContain("Bench boundary");
    expect(html).toContain("Rollback runbook");
    expect(html).toContain("Rollback to the latest confirmed checkpoint when health degrades.");
    expect(html).toContain("Quick operator exits");
    expect(html).toContain('href="/system"');
    expect(html).toContain('href="/logs"');
    expect(html).toContain('href="/log-chat"');
    expect(html).toContain("All Logs Chat");
  });

  it("renders Bot Texts data-present state with editable templates and recipients", () => {
    state.queries.botTexts = {
      data: {
        summary: {
          totalTemplates: 2,
          activeRecipients: 2,
          telegramConfigured: true,
        },
        texts: [
          {
            key: "welcome",
            title: "Welcome message",
            description: "Greeting shown to new users",
            body: "Hello and welcome to CSBot",
          },
          {
            key: "maintenance",
            title: "Maintenance notice",
            description: "Shown during downtime",
            body: "The system is under maintenance",
          },
        ],
        recipients: [
          {
            id: 1,
            botLabel: "Primary bot",
            chatId: "123456789",
            status: "active",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/bot-texts");

    expect(html).toContain("Bot text editor");
    expect(html).toContain("Template key");
    expect(html).toContain("Delivery summary");
    expect(html).toContain("Telegram recipients");
    expect(html).toContain("123456789");
    expect(html).toContain("Save template");
    expect(html).toContain("Configured");
  });

  it("renders Broadcasts data-present state with composer, history and manual recipient mode", () => {
    state.queries.broadcasts = {
      data: {
        summary: {
          totalBroadcasts: 3,
          linkedRecipients: 2,
          telegramConfigured: true,
        },
        recipients: [
          {
            id: 1,
            botLabel: "Primary bot",
            chatId: "123456789",
            status: "active",
          },
        ],
        history: [
          {
            id: "broadcast-1",
            publicId: "broadcast-1",
            title: "Maintenance notice",
            status: "success",
            dryRun: false,
            requestedRecipients: 2,
            deliveredCount: 2,
            createdAt: "2026-04-03T10:00:00.000Z",
          },
        ],
      },
      isLoading: false,
      error: null,
    };

    const html = renderPage("/broadcasts");

    expect(html).toContain("Broadcast composer");
    expect(html).toContain("Linked delivery mode");
    expect(html).toContain("Send broadcast");
    expect(html).toContain("Broadcast history");
    expect(html).toContain("Maintenance notice");
    expect(html).toContain("Linked recipients");
    expect(html).toContain("Configured");
  });

  it("renders System empty state when readiness, scenarios and checklist are absent", () => {
    const html = renderPage("/system");

    expect(html).toContain("System module is empty");
    expect(html).toContain("Когда system summary вернёт safe scenarios, readiness и checklist");
  });

  it("renders Bot Texts empty state when no templates are returned", () => {
    const html = renderPage("/bot-texts");

    expect(html).toContain("Bot text editor");
    expect(html).toContain("No templates loaded");
    expect(html).toContain("Шаблоны появятся здесь после ответа botTexts-модуля");
  });

  it("renders Broadcasts empty-history state when no broadcasts are returned", () => {
    const html = renderPage("/broadcasts");

    expect(html).toContain("Broadcast composer");
    expect(html).toContain("Broadcast history");
    expect(html).toContain("No broadcasts yet");
  });
});
