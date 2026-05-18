import { beforeEach, describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  assertVipScope,
  createApiKeyRecord,
  createBulkJob,
  createSafeImportedLeadBatch,
  createSingleJob,
  deriveRateLimit,
  getAdminOverview,
  getApiUsageSummary,
  getBillingModule,
  getJobDetails,
  getJobsModule,
  getProxyModule,
  getSafeTestBench,
  getSystemModule,
  getTelemetryModule,
  getWorkersModule,
  previewImportedLeadText,
} from "./platformService";
import {
  listRuntimeApiKeys,
  listRuntimeAuditTrailEntries,
  listRuntimeJobEventsByJobId,
  listRuntimeProxyLeases,
  listRuntimeUsageRecords,
  listRuntimeWorkerRuns,
  resetRuntimeStore,
} from "./runtimeStore";

const importedDatasetFixture = readFileSync(
  resolve(process.cwd(), "server/fixtures/importedLeadDataset.fixture.txt"),
  "utf8",
);

describe("platformService", () => {
  beforeEach(() => {
    resetRuntimeStore();
  });

  it("creates a safe single job with deterministic operational fields", async () => {
    const result = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 100,
        payload: {
          target: "mock://catalog/item/42",
          action: "extract",
        },
        safeTestMode: true,
      },
      { userId: 1, source: "dashboard" },
    );

    expect(result.ok).toBe(true);
    expect(result.data.job.status).toBe("succeeded");
    expect(result.data.job.resultJson).toMatchObject({
      safeTestMode: true,
      providerUsed: "evomi",
      oneCsResult: {
        creditScore: null,
        productScore: 1,
        dataQualityScore: 1.4,
        status: "decline",
      },
    });
    expect(result.data.events.some(event => event.type === "job.created")).toBe(true);
    expect(result.data.events.some(event => event.type === "proxy.selection")).toBe(true);
  });

  it("derives ONE CS scores and adverse reasons from explicit payload signals", async () => {
    const result = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 100,
        payload: {
          target: "mock://one-cs/profile/1",
          creditScore: 651,
          completenessScore: 0.86,
          adverseReasons: [
            "Income or credit history insufficient for loan",
            "Requested amount unsupported by income",
            "RiskView Consumer Inquiry",
          ],
        },
        safeTestMode: true,
      },
      { userId: 1, source: "dashboard" },
    );

    expect(result.ok).toBe(true);
    expect(result.data.job.resultJson.oneCsResult).toMatchObject({
      creditScore: 651,
      productScore: 13,
      status: "success",
      adverseReasons: [
        "Income or credit history insufficient for loan",
        "Requested amount unsupported by income",
        "RiskView Consumer Inquiry",
      ],
      adverseReasonGroups: ["affordability", "inquiry_pressure"],
    });
    expect(result.data.job.resultJson.oneCsResult.dataQualityScore).toBeCloseTo(4.4, 5);
    expect(result.data.job.resultJson.summary).toMatchObject({
      creditScore: 651,
      productScore: 13,
      dataQualityScore: 4.4,
      status: "success",
      adverseReasonCount: 3,
    });
  });

  it("adds fallback and retry events when mock payload requests them", async () => {
    const result = await createSingleJob(
      {
        requestMode: "vip",
        queueName: "vip",
        priority: 10,
        payload: {
          target: "mock://provider/fallback",
          simulateProviderFailure: true,
          simulateRetryableError: true,
        },
        proxy: {
          providerHint: "evomi",
          protocol: "http",
          sessionMode: "sticky",
          maxTransportRetries: 3,
          maxProviderSwitches: 2,
        },
        safeTestMode: true,
      },
      { userId: 1, source: "testbench" },
    );

    expect(result.data.events.some(event => event.type === "proxy.provider_fallback")).toBe(true);
    expect(result.data.events.some(event => event.type === "job.waiting_retry")).toBe(true);
    expect(result.data.job.maxAttempts).toBe(4);
    expect(result.data.job.resultJson.oneCsResult.status).toBe("decline");
    expect(result.data.job.resultJson.oneCsResult.adverseReasonGroups).toContain("thin_file");
  });

  it("creates a bulk batch and preserves item count", async () => {
    const result = await createBulkJob(
      {
        queueName: "bulk",
        priority: 120,
        safeTestMode: true,
        items: [
          { externalId: "item-1", payload: { target: "mock://bulk/1" } },
          { externalId: "item-2", payload: { target: "mock://bulk/2" } },
        ],
      },
      { userId: 1, source: "api" },
    );

    expect(result.ok).toBe(true);
    expect(result.data.itemCount).toBe(2);
    expect(result.data.jobs).toHaveLength(2);
    expect(result.meta).toMatchObject({ safeTestMode: true, queueName: "bulk" });
  });

  it("creates API key records with a preview token and hashed storage representation", async () => {
    const result = await createApiKeyRecord(1, {
      label: "VIP Partner Key",
      scope: "vip",
      rpmLimit: 300,
      dailyLimit: 25000,
    });

    expect(result.preview.startsWith("cs_vip_")).toBe(true);
    expect(result.record.scope).toBe("vip");
    expect(result.record.keyHash).not.toBe(result.preview);
    expect(result.record.keyPrefix.length).toBeGreaterThan(8);
  });

  it("derives rate limits by scope and validates vip scopes", () => {
    expect(deriveRateLimit("single")).toEqual({ rpm: 60, daily: 1000 });
    expect(deriveRateLimit("bulk")).toEqual({ rpm: 120, daily: 5000 });
    expect(deriveRateLimit("vip")).toEqual({ rpm: 300, daily: 25000 });
    expect(deriveRateLimit("admin")).toEqual({ rpm: 600, daily: 100000 });
    expect(assertVipScope("vip")).toBe(true);
    expect(assertVipScope("admin")).toBe(true);
    expect(assertVipScope("bulk")).toBe(false);
  });

  it("returns a consistent admin overview and safe test bench payload", async () => {
    const overview = await getAdminOverview();
    const bench = await getSafeTestBench();

    expect(Array.isArray(overview.safeTestScenarios)).toBe(true);
    expect(overview.safeTestScenarios.length).toBeGreaterThan(0);
    expect(Array.isArray(overview.jobs)).toBe(true);
    expect(bench.mockHealth.status).toBe("healthy");
    expect(bench.scenarios.length).toBeGreaterThan(0);
    expect(bench.sampleEvents.length).toBeGreaterThan(0);
  });

  it("builds a safe imported preview from the broader anonymized dataset fixture", async () => {
    const preview = await previewImportedLeadText(importedDatasetFixture);

    expect(preview).toMatchObject({
      totalRecords: 9,
      withPhone: 6,
      withEmailDomain: 5,
      withDob: 8,
      withSsnMarker: 8,
    });
    expect(preview.sourceLabels).toHaveLength(4);
    expect(preview.safePayloads).toHaveLength(9);
    expect(preview.sampleRecords.every(record => record.piiRedacted === true)).toBe(true);
    expect(preview.sampleRecords.some(record => record.flags.includes("no_phone_or_email_marker"))).toBe(true);
    expect(preview.averageCompletenessScore).toBeGreaterThan(0.5);
  });

  it("creates a safe imported batch from the broader anonymized dataset fixture", async () => {
    const result = await createSafeImportedLeadBatch(importedDatasetFixture, {
      userId: 1,
      source: "dashboard",
    });

    expect(result.ok).toBe(true);
    expect(result.data.itemCount).toBe(9);
    expect(result.data.jobs).toHaveLength(9);
    expect(result.meta).toMatchObject({
      safeTestMode: true,
      queueName: "lead-import",
    });
    expect(result.data.jobs.every(job => job.requestMode === "bulk")).toBe(true);
    expect(result.data.jobs.every(job => job.status === "succeeded")).toBe(true);
  });

  it("queues a non-safe single job for runtime execution", async () => {
    const result = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 90,
        payload: {
          target: "mock://runtime/queued/1",
        },
        safeTestMode: false,
      },
      { userId: 7, source: "api" },
    );

    expect(result.ok).toBe(true);
    expect(result.data.job.status).toBe("queued");
    expect(result.data.job.startedAt).toBeNull();
    expect(result.data.job.completedAt).toBeNull();
    expect(result.data.job.resultJson).toMatchObject({
      safeTestMode: false,
      executionState: "queued_for_worker",
    });
    expect(result.meta).toMatchObject({ executionMode: "queued_runtime", persisted: true });
  });

  it("returns persisted job details including recorded events", async () => {
    const created = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 95,
        payload: {
          target: "mock://runtime/details/1",
        },
        safeTestMode: true,
      },
      { userId: 3, source: "dashboard" },
    );

    const details = await getJobDetails(created.data.job.publicId);

    expect(details).not.toBeNull();
    expect(details?.job.publicId).toBe(created.data.job.publicId);
    expect(details?.events.some(event => event.eventType === "job.created")).toBe(true);
    expect(details?.events.some(event => event.eventType === "job.completed")).toBe(true);
  });

  it("returns null job details for an unknown public id", async () => {
    const details = await getJobDetails("job_missing_123");
    expect(details).toBeNull();
  });

  it("enriches jobs module rows with persisted events", async () => {
    const created = await createSingleJob(
      {
        requestMode: "bulk",
        queueName: "bulk",
        priority: 110,
        payload: {
          target: "mock://runtime/jobs-module/1",
        },
        safeTestMode: true,
      },
      { userId: 5, source: "dashboard" },
    );

    const jobs = await getJobsModule();
    const row = jobs.find(job => job.publicId === created.data.job.publicId);

    expect(row).toBeDefined();
    expect(Array.isArray(row?.events)).toBe(true);
    expect(row?.events.some(event => event.eventType === "job.created")).toBe(true);
  });

  it("persists safe-test vip jobs with completed-state details", async () => {
    const created = await createSingleJob(
      {
        requestMode: "vip",
        queueName: "vip",
        priority: 5,
        payload: {
          target: "mock://runtime/lease/safe",
        },
        safeTestMode: true,
      },
      { userId: 2, source: "testbench" },
    );

    const details = await getJobDetails(created.data.job.publicId);

    expect(created.data.job.status).toBe("succeeded");
    expect(details?.events.some(event => event.eventType === "job.completed")).toBe(true);
    expect(created.data.job.completedAt).not.toBeNull();
  });

  it("keeps queued jobs in queued runtime mode with socks5 proxy metadata", async () => {
    const created = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 80,
        payload: {
          target: "mock://runtime/lease/queued",
        },
        proxy: {
          providerHint: "dataimpulse",
          protocol: "socks5",
          sessionMode: "sticky",
        },
        safeTestMode: false,
      },
      { userId: 11, source: "api" },
    );

    expect(created.data.job.status).toBe("queued");
    expect(created.data.job.resultJson).toMatchObject({
      safeTestMode: false,
      providerUsed: "dataimpulse",
      queuedAt: expect.any(String),
    });
    expect(created.data.events.some(event => event.type === "job.queued")).toBe(true);
  });

  it("records request and browser-run usage for safe vip jobs", async () => {
    const created = await createSingleJob(
      {
        requestMode: "vip",
        queueName: "vip",
        priority: 8,
        payload: {
          target: "mock://runtime/usage/vip",
        },
        safeTestMode: true,
      },
      { userId: 4, source: "dashboard" },
    );

    const summary = await getApiUsageSummary();

    expect(created.data.job.requestMode).toBe("vip");
    expect(created.data.job.status).toBe("succeeded");
    expect(typeof summary.usageSummary.requests).toBe("number");
    expect(typeof summary.usageSummary.browserRuns).toBe("number");
  });

  it("aggregates usage summary across multiple persisted jobs", async () => {
    await createSingleJob(
      {
        requestMode: "vip",
        queueName: "vip",
        priority: 8,
        payload: {
          target: "mock://runtime/usage/1",
        },
        safeTestMode: true,
      },
      { userId: 4, source: "dashboard" },
    );

    await createSingleJob(
      {
        requestMode: "bulk",
        queueName: "bulk",
        priority: 110,
        payload: {
          target: "mock://runtime/usage/2",
        },
        safeTestMode: true,
      },
      { userId: 4, source: "api" },
    );

    const summary = await getApiUsageSummary();

    expect(summary.usageSummary.currentPeriod).toBeTruthy();
    expect(typeof summary.usageSummary.requests).toBe("number");
    expect(typeof summary.usageSummary.browserRuns).toBe("number");
    expect(typeof summary.usageSummary.cogsUsd).toBe("number");
    expect(typeof summary.usageSummary.revenueUsd).toBe("number");
  });

  it("persists API key expiry and emits an audit entry", async () => {
    const expiresAt = "2030-01-01T00:00:00.000Z";
    const before = await getAdminOverview();
    const result = await createApiKeyRecord(9, {
      label: "Future Key",
      scope: "bulk",
      rpmLimit: 120,
      dailyLimit: 5000,
      expiresAt,
    });
    const after = await getAdminOverview();

    expect(result.record.expiresAt?.toISOString()).toBe(expiresAt);
    expect(after.auditTrail.length).toBeGreaterThanOrEqual(before.auditTrail.length);
    expect(after.auditTrail.some(entry => entry.action === "apikey.create" && entry.resourceId === result.record.keyPrefix)).toBe(true);
  });

  it("surfaces persisted api keys and usage inside the billing module", async () => {
    const createdKey = await createApiKeyRecord(6, {
      label: "Billing View Key",
      scope: "single",
      rpmLimit: 60,
      dailyLimit: 1000,
    });

    await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 100,
        payload: {
          target: "mock://runtime/billing/1",
        },
        safeTestMode: true,
      },
      { userId: 6, source: "dashboard" },
    );

    const billing = await getBillingModule();

    expect(billing.apiKeys.some(apiKey => apiKey.keyPrefix === createdKey.record.keyPrefix)).toBe(true);
    expect(typeof billing.usageSummary.requests).toBe("number");
    expect(typeof billing.usageSummary.cogsUsd).toBe("number");
  });

  it("computes telemetry counters and success rate from mixed job states", async () => {
    await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 100,
        payload: {
          target: "mock://runtime/telemetry/1",
        },
        safeTestMode: true,
      },
      { userId: 1, source: "dashboard" },
    );

    await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 100,
        payload: {
          target: "mock://runtime/telemetry/2",
        },
        safeTestMode: false,
      },
      { userId: 1, source: "api" },
    );

    const telemetry = await getTelemetryModule();

    expect(telemetry.jobStatusCounts.total).toBeGreaterThan(0);
    expect(telemetry.jobStatusCounts.succeeded).toBeGreaterThanOrEqual(0);
    expect(telemetry.jobStatusCounts.queued).toBeGreaterThanOrEqual(0);
    expect(telemetry.successRate).toBeGreaterThanOrEqual(0);
    expect(telemetry.successRate).toBeLessThanOrEqual(1);
    expect(Array.isArray(telemetry.recentAudit)).toBe(true);
  });

  it("returns worker module recommendations and queue health", async () => {
    const workers = await getWorkersModule();

    expect(Array.isArray(workers.recommendations)).toBe(true);
    expect(workers.recommendations.length).toBeGreaterThan(0);
    expect(workers.queueHealth).toBeDefined();
  });

  it("returns proxy module provider health and routing principles", async () => {
    const proxy = await getProxyModule();

    expect(Array.isArray(proxy.providers)).toBe(true);
    expect(Array.isArray(proxy.providerHealth)).toBe(true);
    expect(proxy.providerHealth.length).toBe(proxy.providers.length);
    expect(proxy.routingPrinciples.selectionOrder).toHaveLength(proxy.providers.length);
    expect(proxy.routingPrinciples.fallbackEnabled).toBe(true);
    expect(proxy.routingPrinciples.stickySupported).toBe(true);
  });

  it("returns system module scenarios and stabilization checklist", async () => {
    const system = await getSystemModule();

    expect(system.health.status).toBe("healthy");
    expect(system.safeTestScenarios.length).toBeGreaterThan(0);
    expect(system.stabilizationChecklist.length).toBeGreaterThan(0);
    expect(system.stabilizationChecklist.some(item => item.includes("Rate limit all public REST endpoints."))).toBe(true);
  });

  it("persists retry events for direct job-detail inspection", async () => {
    const created = await createSingleJob(
      {
        requestMode: "single",
        queueName: "default",
        priority: 101,
        payload: {
          target: "mock://runtime/events/direct",
          simulateRetryableError: true,
        },
        safeTestMode: true,
      },
      { userId: 8, source: "dashboard" },
    );

    const details = await getJobDetails(created.data.job.publicId);

    expect(details?.events.length ?? 0).toBeGreaterThanOrEqual(3);
    expect(details?.events.some(event => event.eventType === "job.waiting_retry")).toBe(true);
  });

  it("creates queued bulk jobs when safe test mode is disabled", async () => {
    const result = await createBulkJob(
      {
        queueName: "bulk",
        priority: 125,
        safeTestMode: false,
        items: [
          { externalId: "queued-1", payload: { target: "mock://bulk/queued/1" } },
          { externalId: "queued-2", payload: { target: "mock://bulk/queued/2" } },
        ],
      },
      { userId: 10, source: "api" },
    );

    expect(result.ok).toBe(true);
    expect(result.data.itemCount).toBe(2);
    expect(result.data.jobs.every(job => job.status === "queued")).toBe(true);
    expect(result.meta).toMatchObject({ safeTestMode: false, queueName: "bulk" });
  });
});
