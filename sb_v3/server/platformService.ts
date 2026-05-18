import { createHash, randomBytes } from "crypto";
import type {
  CreateApiKeyInput,
  CreateBulkJobInput,
  CreateJobInput,
  JobStatus,
  RequestMode,
} from "../shared/platform";
import {
  SAFE_TEST_SCENARIOS,
} from "../shared/platform";
import {
  buildSafeLeadImportPayloads,
  parseImportedLeadText,
  toSafeImportedLeadRecord,
} from "../shared/importedLeadFormat";
import { buildOneCsResult } from "../shared/oneCsScoring";
import { ProxyManager, proxyConfigFromEnv } from "./browser/proxyManager";
import { executeCreditScoreJob } from "./browser/browserWorker";
import {
  getDashboardSummary,
  getJobByPublicId,
  listApiKeysForUser,
  listAuditTrailEntries,
  listJobEventsByJobId,
  listJobs,
  listPayments,
  listPlans,
  listProxyPolicies,
  listProxyProviders,
  listSubscriptions,
  listWorkerNodes,
  persistApiKeyRecord,
  revokeApiKeyRecord,
  persistAuditTrailEntry,
  persistJobEvents,
  persistJobRecord,
  persistProxyLease,
  persistUsageRecord,
  persistWorkerRun,
  updateJobRecord,
} from "./db";
import {
  findMockJob,
  listMockJobEvents,
  MOCK_HEALTH_SUMMARY,
  MOCK_USAGE_SUMMARY,
} from "./platformMockData";
import { getCurrentPeriodKey, getRuntimeUsageSummary } from "./runtimeStore";

function createPublicId(prefix: string) {
  return `${prefix}_${randomBytes(6).toString("hex")}`;
}

function hashToken(raw: string) {
  return createHash("sha256").update(raw).digest("hex");
}

function estimateCost(mode: RequestMode, payloadSize: number) {
  const base = mode === "vip" ? 0.15 : mode === "bulk" ? 0.04 : 0.02;
  return Number((base + payloadSize / 10000).toFixed(4));
}

function nowIso() {
  return new Date().toISOString();
}

function toFiniteNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
}

function toStringArray(value: unknown) {
  if (!Array.isArray(value)) {
    return [] as string[];
  }

  return value
    .filter((item): item is string => typeof item === "string")
    .map(item => item.trim())
    .filter(Boolean);
}

function inferOneCsCreditScore(payload: Record<string, unknown>) {
  return toFiniteNumber(payload.creditScore) ?? toFiniteNumber(payload.rawCreditScore) ?? null;
}

function inferOneCsCompletenessScore(payload: Record<string, unknown>) {
  const candidate = toFiniteNumber(payload.completenessScore) ?? toFiniteNumber(payload.dataCompletenessScore);
  if (candidate === null) {
    return undefined;
  }

  return Math.min(1, Math.max(0, candidate));
}

function inferOneCsAdverseReasons(payload: Record<string, unknown>, creditScore: number | null) {
  const explicitReasons = toStringArray(payload.adverseReasons);
  if (explicitReasons.length > 0) {
    return explicitReasons;
  }

  const inferred = new Set<string>();

  if (payload.noCreditProfile === true) {
    inferred.add("Unable to find credit profile at TransUnion");
  }
  if (payload.thinFile === true) {
    inferred.add("Insufficient length of credit history");
  }
  if (payload.highUtilization === true) {
    inferred.add("Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high");
  }
  if (payload.highDebtToIncome === true) {
    inferred.add("High debt in relation to income");
  }
  if (payload.recentInquiries === true) {
    inferred.add("RiskView Consumer Inquiry");
  }

  if (creditScore === null && inferred.size === 0) {
    inferred.add("Insufficient credit history");
  } else if (creditScore !== null) {
    if (creditScore < 480) {
      inferred.add("Serious delinquency, and public record or collection filed");
      inferred.add("High debt in relation to income");
    } else if (creditScore < 560) {
      inferred.add("Serious delinquency");
      inferred.add("Too many accounts with balances");
      inferred.add("Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high");
    } else if (creditScore < 640) {
      inferred.add("Income or credit history insufficient for loan");
      inferred.add("Requested amount unsupported by income");
    } else if (creditScore < 720) {
      inferred.add("RiskView Consumer Inquiry");
    }
  }

  return Array.from(inferred);
}

function inferOneCsPriceUsd(mode: RequestMode, payload: Record<string, unknown>, estimatedCostUsd: number) {
  const explicitPrice =
    toFiniteNumber(payload.priceUsd) ??
    toFiniteNumber(payload.chargedPriceUsd) ??
    toFiniteNumber(payload.requestPriceUsd);

  if (explicitPrice !== null) {
    return explicitPrice;
  }

  const defaults: Record<RequestMode, number> = {
    single: 1.9,
    bulk: 1.7,
    vip: 2.5,
  };

  return Number(Math.max(defaults[mode], estimatedCostUsd * 2.75).toFixed(2));
}

export function buildApiResponse<T>(requestId: string, data: T, meta?: Record<string, unknown>) {
  return {
    ok: true,
    requestId,
    data,
    meta,
  } as const;
}

export function buildApiError(
  requestId: string,
  code: string,
  message: string,
  retryable = false,
  details?: Record<string, unknown>,
) {
  return {
    ok: false,
    requestId,
    error: {
      code,
      message,
      retryable,
      details,
    },
  } as const;
}

export async function getAdminOverview() {
  const summary = await getDashboardSummary();
  const [plans, subscriptions, payments, auditTrail] = await Promise.all([
    listPlans(),
    listSubscriptions(),
    listPayments(),
    listAuditTrailEntries(),
  ]);

  return {
    ...summary,
    plans,
    subscriptions,
    payments,
    auditTrail: auditTrail.slice(0, 50),
    safeTestScenarios: SAFE_TEST_SCENARIOS,
  };
}

export async function getJobsModule() {
  const jobs = await listJobs();

  const enriched = await Promise.all(
    jobs.map(async job => ({
      ...job,
      events: await listJobEventsByJobId(job.id),
    })),
  );

  return enriched;
}

export async function getJobDetails(publicId: string) {
  const job = await getJobByPublicId(publicId);
  if (!job) {
    return null;
  }

  const events = await listJobEventsByJobId(job.id);
  return {
    job,
    events,
  };
}

export async function getProxyModule() {
  const [providers, policies] = await Promise.all([listProxyProviders(), listProxyPolicies()]);

  const providerHealth = providers.map(provider => ({
    code: provider.code,
    name: provider.name,
    status: provider.status,
    priority: provider.priority,
    protocolSupport: provider.protocolSupport,
    sessionSupport: provider.sessionSupport,
    costPerGbUsd: provider.costPerGbUsd,
    healthScore:
      provider.status === "healthy" ? 0.98 : provider.status === "degraded" ? 0.72 : 0.1,
    lastCheckedAt: nowIso(),
  }));

  return {
    providers,
    policies,
    providerHealth,
    routingPrinciples: {
      selectionOrder: providers.sort((a, b) => a.priority - b.priority).map(provider => provider.code),
      fallbackEnabled: true,
      stickySupported: true,
      rotatingSupported: true,
      trafficAccounting: true,
    },
  };
}

export async function getWorkersModule() {
  const workers = await listWorkerNodes();

  return {
    workers,
    queueHealth: MOCK_HEALTH_SUMMARY.queues,
    recommendations: [
      "Keep VIP queue lag under 10 seconds.",
      "Trigger maintenance mode when heartbeat gap exceeds 60 seconds.",
      "Use safe test scenarios before changing routing or retry policies.",
    ],
  };
}

export async function getBillingModule() {
  const [plans, subscriptions, payments, apiKeys] = await Promise.all([
    listPlans(),
    listSubscriptions(),
    listPayments(),
    listApiKeysForUser(),
  ]);

  return {
    plans,
    subscriptions,
    payments,
    apiKeys,
    usageSummary: getRuntimeUsageSummary() ?? MOCK_USAGE_SUMMARY,
  };
}

export async function getRevenueAnalyticsModule() {
  const [plans, subscriptions, payments] = await Promise.all([
    listPlans(),
    listSubscriptions(),
    listPayments(),
  ]);

  const usageSummary = getRuntimeUsageSummary() ?? MOCK_USAGE_SUMMARY;
  const planById = new Map(plans.map(plan => [plan.id, plan]));
  const subscriptionById = new Map(subscriptions.map(subscription => [subscription.id, subscription]));
  const settledStatuses = new Set(["paid", "confirmed"]);
  const refundedStatuses = new Set(["refunded"]);
  const pendingStatuses = new Set(["pending"]);

  const normalizedPayments = payments.map(payment => {
    const normalizedAmountUsd =
      toFiniteNumber(payment.amountUsd) ??
      (payment.currency?.toUpperCase() === "USD" ? toFiniteNumber(payment.amount) : null) ??
      0;
    const effectiveDate = payment.paidAt ?? payment.createdAt ?? new Date();
    const periodKey = getCurrentPeriodKey(effectiveDate);
    const subscription = payment.subscriptionId ? subscriptionById.get(payment.subscriptionId) ?? null : null;
    const plan = subscription ? planById.get(subscription.planId) ?? null : null;

    return {
      ...payment,
      normalizedAmountUsd,
      effectiveDate,
      periodKey,
      subscription,
      plan,
    };
  });

  const totalCollectedUsd = normalizedPayments
    .filter(payment => settledStatuses.has(payment.status))
    .reduce((sum, payment) => sum + payment.normalizedAmountUsd, 0);

  const refundedUsd = normalizedPayments
    .filter(payment => refundedStatuses.has(payment.status))
    .reduce((sum, payment) => sum + payment.normalizedAmountUsd, 0);

  const pendingUsd = normalizedPayments
    .filter(payment => pendingStatuses.has(payment.status))
    .reduce((sum, payment) => sum + payment.normalizedAmountUsd, 0);

  const activeSubscriptions = subscriptions.filter(subscription =>
    ["active", "paid", "confirmed", "trialing"].includes(String(subscription.status)),
  );

  const estimatedMrrUsd = activeSubscriptions.reduce((sum, subscription) => {
    const plan = planById.get(subscription.planId);
    if (!plan) {
      return sum;
    }

    const planPriceUsd = toFiniteNumber(plan.priceUsd) ?? 0;
    const divisor =
      plan.billingInterval === "yearly"
        ? 12
        : plan.billingInterval === "quarterly"
          ? 3
          : plan.billingInterval === "monthly"
            ? 1
            : 0;

    if (!divisor) {
      return sum;
    }

    return sum + planPriceUsd / divisor;
  }, 0);

  const revenueByMonthMap = normalizedPayments.reduce((acc, payment) => {
    const current = acc.get(payment.periodKey) ?? {
      periodKey: payment.periodKey,
      collectedUsd: 0,
      refundedUsd: 0,
      pendingUsd: 0,
      paymentCount: 0,
    };

    if (settledStatuses.has(payment.status)) {
      current.collectedUsd += payment.normalizedAmountUsd;
    }
    if (refundedStatuses.has(payment.status)) {
      current.refundedUsd += payment.normalizedAmountUsd;
    }
    if (pendingStatuses.has(payment.status)) {
      current.pendingUsd += payment.normalizedAmountUsd;
    }
    current.paymentCount += 1;

    acc.set(payment.periodKey, current);
    return acc;
  }, new Map<string, { periodKey: string; collectedUsd: number; refundedUsd: number; pendingUsd: number; paymentCount: number }>());

  const revenueByMonth = Array.from(revenueByMonthMap.values())
    .sort((a, b) => a.periodKey.localeCompare(b.periodKey))
    .slice(-12)
    .map(item => ({
      ...item,
      collectedUsd: Number(item.collectedUsd.toFixed(2)),
      refundedUsd: Number(item.refundedUsd.toFixed(2)),
      pendingUsd: Number(item.pendingUsd.toFixed(2)),
    }));

  const providerBreakdown = Array.from(
    normalizedPayments.reduce((acc, payment) => {
      const key = payment.provider || "unknown";
      const current = acc.get(key) ?? {
        provider: key,
        collectedUsd: 0,
        refundedUsd: 0,
        pendingUsd: 0,
        paymentCount: 0,
      };

      if (settledStatuses.has(payment.status)) {
        current.collectedUsd += payment.normalizedAmountUsd;
      }
      if (refundedStatuses.has(payment.status)) {
        current.refundedUsd += payment.normalizedAmountUsd;
      }
      if (pendingStatuses.has(payment.status)) {
        current.pendingUsd += payment.normalizedAmountUsd;
      }
      current.paymentCount += 1;

      acc.set(key, current);
      return acc;
    }, new Map<string, { provider: string; collectedUsd: number; refundedUsd: number; pendingUsd: number; paymentCount: number }>()).values(),
  )
    .sort((a, b) => b.collectedUsd - a.collectedUsd)
    .map(item => ({
      ...item,
      collectedUsd: Number(item.collectedUsd.toFixed(2)),
      refundedUsd: Number(item.refundedUsd.toFixed(2)),
      pendingUsd: Number(item.pendingUsd.toFixed(2)),
    }));

  const planBreakdown = Array.from(
    normalizedPayments.reduce((acc, payment) => {
      const plan = payment.plan;
      const key = plan?.code ?? "unmapped";
      const current = acc.get(key) ?? {
        planCode: key,
        planName: plan?.name ?? "Unmapped",
        tier: plan?.tier ?? "unknown",
        collectedUsd: 0,
        paymentCount: 0,
        activeSubscriptions: 0,
      };

      if (settledStatuses.has(payment.status)) {
        current.collectedUsd += payment.normalizedAmountUsd;
      }
      current.paymentCount += 1;
      acc.set(key, current);
      return acc;
    }, new Map<string, { planCode: string; planName: string; tier: string; collectedUsd: number; paymentCount: number; activeSubscriptions: number }>())
      .entries(),
  ).reduce((acc, [key, value]) => {
    const activeForPlan = activeSubscriptions.filter(subscription => {
      const plan = planById.get(subscription.planId);
      return (plan?.code ?? "unmapped") === key;
    }).length;

    acc.push({
      ...value,
      activeSubscriptions: activeForPlan,
      collectedUsd: Number(value.collectedUsd.toFixed(2)),
    });
    return acc;
  }, [] as Array<{ planCode: string; planName: string; tier: string; collectedUsd: number; paymentCount: number; activeSubscriptions: number }>)
    .sort((a, b) => b.collectedUsd - a.collectedUsd);

  const recentPayments = normalizedPayments.slice(0, 12).map(payment => ({
    id: payment.id,
    provider: payment.provider,
    status: payment.status,
    currency: payment.currency,
    amount: payment.amount,
    amountUsd: Number(payment.normalizedAmountUsd.toFixed(2)),
    planCode: payment.plan?.code ?? null,
    planName: payment.plan?.name ?? null,
    tier: payment.plan?.tier ?? null,
    paidAt: payment.paidAt,
    createdAt: payment.createdAt ?? payment.effectiveDate,
    invoiceRef: payment.invoiceRef,
    txRef: payment.txRef,
  }));

  return {
    overview: {
      totalCollectedUsd: Number(totalCollectedUsd.toFixed(2)),
      refundedUsd: Number(refundedUsd.toFixed(2)),
      pendingUsd: Number(pendingUsd.toFixed(2)),
      estimatedMrrUsd: Number(estimatedMrrUsd.toFixed(2)),
      activeSubscriptions: activeSubscriptions.length,
      totalPayments: normalizedPayments.length,
      usageRevenueUsd: Number((usageSummary?.revenueUsd ?? 0).toFixed(2)),
      usageMarginUsd: Number((usageSummary?.marginUsd ?? 0).toFixed(2)),
      usageCogsUsd: Number((usageSummary?.cogsUsd ?? 0).toFixed(2)),
      currentPeriod: usageSummary?.currentPeriod ?? getCurrentPeriodKey(),
    },
    usageSummary,
    revenueByMonth,
    providerBreakdown,
    planBreakdown,
    recentPayments,
  };
}

export async function getOperatorLogsModule() {
  const [jobs, auditTrail] = await Promise.all([
    listJobs(),
    listAuditTrailEntries(),
  ]);

  const recentJobs = jobs.slice(0, 40);
  const jobEventGroups = await Promise.all(
    recentJobs.map(async job => {
      const events = await listJobEventsByJobId(job.id);
      return events.map(event => ({
        id: `job-${job.publicId}-${event.id}`,
        source: "job_event",
        severity: event.severity,
        title: event.eventType,
        message: event.message,
        resourceType: "job",
        resourceId: job.publicId,
        actorLabel: job.source,
        createdAt: event.createdAt,
        details: event.eventJson,
      }));
    }),
  );

  const auditEntries = auditTrail.map(entry => ({
    id: `audit-${entry.id}`,
    source: "audit",
    severity: entry.status === "failure" ? "error" : entry.status === "denied" ? "warn" : "info",
    title: entry.action,
    message: `${entry.actorType} → ${entry.resourceType} · ${entry.resourceId}`,
    resourceType: entry.resourceType,
    resourceId: entry.resourceId,
    actorLabel: entry.actorType,
    createdAt: entry.createdAt,
    status: entry.status,
    ipAddress: entry.ipAddress,
    details: entry.detailsJson,
  }));

  const timeline = [...auditEntries, ...jobEventGroups.flat()]
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .slice(0, 200);

  const counters = timeline.reduce(
    (acc, entry) => {
      acc.total += 1;
      acc.sources[entry.source] = (acc.sources[entry.source] ?? 0) + 1;
      acc.severity[entry.severity] = (acc.severity[entry.severity] ?? 0) + 1;
      return acc;
    },
    {
      total: 0,
      sources: {} as Record<string, number>,
      severity: {} as Record<string, number>,
    },
  );

  return {
    counters,
    timeline,
    jobsInspected: recentJobs.length,
    auditEntries: auditTrail.length,
  };
}

export async function getTelemetryModule() {
  const [jobs, providers, workers, auditTrail] = await Promise.all([
    listJobs(),
    listProxyProviders(),
    listWorkerNodes(),
    listAuditTrailEntries(),
  ]);

  const counts = jobs.reduce(
    (acc, job) => {
      acc.total += 1;
      acc[job.status] = (acc[job.status] ?? 0) + 1;
      return acc;
    },
    {
      total: 0,
      queued: 0,
      running: 0,
      succeeded: 0,
      failed: 0,
      canceled: 0,
      waiting_retry: 0,
    } as Record<string, number>,
  );

  const successRate = counts.total > 0 ? counts.succeeded / counts.total : 0;
  const retryRate = counts.total > 0 ? counts.waiting_retry / counts.total : 0;

  return {
    health: MOCK_HEALTH_SUMMARY,
    jobStatusCounts: counts,
    successRate,
    retryRate,
    providers,
    workers,
    recentAudit: auditTrail.slice(0, 20),
  };
}

export async function getSystemModule() {
  const stabilizationChecklist = [
    "Rate limit all public REST endpoints.",
    "Emit audit events for administrative mutations.",
    "Keep proxy fallback paths observable in job events.",
    "Never execute external protected flows from the safe test bench.",
  ];

  return {
    health: MOCK_HEALTH_SUMMARY,
    safeTestScenarios: SAFE_TEST_SCENARIOS,
    stabilizationChecklist,
    readinessSnapshot: [
      {
        code: "safe-bench-isolation",
        label: "Safe bench isolation",
        status: "ready",
        detail: "External protected flows stay excluded from the operator test bench.",
      },
      {
        code: "proxy-fallback-observability",
        label: "Proxy fallback observability",
        status: "ready",
        detail: "Fallback paths are visible through job events and telemetry summaries.",
      },
      {
        code: "admin-audit-mutations",
        label: "Admin mutation audit trail",
        status: "pending",
        detail: "Administrative write actions still need explicit audit coverage before wider rollout.",
      },
      {
        code: "public-rest-rate-limits",
        label: "Public REST rate limits",
        status: "pending",
        detail: "Production-facing public endpoints still require final hardening and verification.",
      },
    ],
    rolloutRunbook: [
      "Confirm the health snapshot and queue/provider counters before any broader rollout.",
      "Run only safe scenarios first and verify expected operator-facing UI text for each path.",
      "Promote changes incrementally after automated checks, manual verification and checkpoint creation.",
    ],
    rollbackRunbook: [
      "Stop at the first degraded signal in health, logs or payment-sensitive operator flows.",
      "Rollback to the latest confirmed checkpoint and re-verify Overview, Metrics and Billing screens.",
      "Keep the previous stable runtime path available until the corrective increment is confirmed visually.",
    ],
  };
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function executeQueuedJobLifecycle(params: {
  job: Awaited<ReturnType<typeof persistJobRecord>>;
  input: CreateJobInput;
  actor: { userId?: number; source: "dashboard" | "api" | "testbench" };
  providerHint: string;
  fallbackProvider: string;
  durationMs: number;
  oneCsResult: ReturnType<typeof buildOneCsResult>;
  summary: {
    creditScore: number | null;
    productScore: number;
    dataQualityScore: number;
    status: string;
    adverseReasonCount: number;
  };
}) {
  const { job, input, actor, providerHint, fallbackProvider, durationMs, summary } = params;
  const startedAt = new Date();

  await updateJobRecord(job.publicId, {
    status: input.payload.simulateRetryableError === true ? "waiting_retry" : "running",
    startedAt,
    attemptCount: 1,
    workerNodeId: 1,
  });

  await persistJobEvents([
    {
      jobId: job.id,
      eventType: input.payload.simulateRetryableError === true ? "job.waiting_retry" : "worker.started",
      severity: input.payload.simulateRetryableError === true ? "warn" : "info",
      message:
        input.payload.simulateRetryableError === true
          ? `Job ${job.publicId} entered retry wait state after first dispatch attempt.`
          : `Worker picked up job ${job.publicId} from queue ${job.queueName}.`,
      eventJson:
        input.payload.simulateRetryableError === true
          ? { retryable: true, nextAttempt: 2, providerHint }
          : { workerNodeId: 1, providerHint, actorSource: actor.source },
      createdAt: startedAt,
    },
  ]);

  const proxyConfig = proxyConfigFromEnv();
  const proxyManager = proxyConfig ? new ProxyManager(proxyConfig) : undefined;

  // Attempt real browser automation when proxy is available
  let browserResult: { creditScore: number | null; source: string; durationMs: number; error?: string } | null = null;

  if (proxyManager) {
    try {
      const payloadRecord = input.payload as Record<string, unknown>;
      const browserPayload = {
        firstName: String(payloadRecord.firstName ?? payloadRecord.first_name ?? "John"),
        lastName: String(payloadRecord.lastName ?? payloadRecord.last_name ?? "Doe"),
        street: String(payloadRecord.street ?? payloadRecord.address ?? "123 Main St"),
        city: String(payloadRecord.city ?? "New York"),
        state: String(payloadRecord.state ?? "NY"),
        zipCode: String(payloadRecord.zipCode ?? payloadRecord.zip_code ?? "10001"),
        dob: String(payloadRecord.dob ?? payloadRecord.dateOfBirth ?? "01/01/1990"),
        annualIncome: String(payloadRecord.annualIncome ?? payloadRecord.annual_income ?? "50000"),
        email: payloadRecord.email ? String(payloadRecord.email) : undefined,
        phone: payloadRecord.phone ? String(payloadRecord.phone) : undefined,
        ssn: payloadRecord.ssn ? String(payloadRecord.ssn) : undefined,
      };

      browserResult = await executeCreditScoreJob(browserPayload, proxyManager, true);

      if (browserResult.creditScore !== null) {
        proxyManager.onSuccess();
      } else {
        proxyManager.onFailure();
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      console.error(`[BrowserWorker] Job ${job.publicId} browser automation failed: ${errMsg}`);
      browserResult = { creditScore: null, source: "browser", durationMs: Date.now() - startedAt.getTime(), error: errMsg };
      proxyManager?.onFailure();
    }
  }

  // Determine credit score and scoring from browser result or fallback
  const creditScore = browserResult?.creditScore ?? inferOneCsCreditScore(input.payload as Record<string, unknown>);
  const completenessScore = inferOneCsCompletenessScore(input.payload as Record<string, unknown>);
  const adverseReasons = inferOneCsAdverseReasons(input.payload as Record<string, unknown>, creditScore);
  const estimatedCostUsd = estimateCost(input.requestMode, JSON.stringify(input.payload).length);
  const realDurationMs = browserResult?.durationMs ?? durationMs;

  const oneCsResult = buildOneCsResult({
    creditScore,
    completenessScore,
    adverseReasons,
    priceUsd: inferOneCsPriceUsd(input.requestMode, input.payload as Record<string, unknown>, estimatedCostUsd),
    durationMs: realDurationMs,
    source: actor.source,
  });

  const computedSummary = {
    creditScore: oneCsResult.creditScore,
    productScore: oneCsResult.productScore,
    dataQualityScore: oneCsResult.dataQualityScore,
    status: oneCsResult.status,
    adverseReasonCount: oneCsResult.adverseReasons.length,
  };

  // Persist proxy lease if proxy was used
  if (proxyManager) {
    await persistProxyLease({
      leaseId: `lease_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
      jobId: job.id,
      workerNodeId: 1,
      providerId: providerHint === "evomi" ? 1 : 2,
      policyId: null,
      protocol: proxyConfig!.protocol,
      sessionMode: "sticky",
      sessionKey: proxyManager.sessionId,
      endpointHost: `${providerHint}.proxy.${proxyConfig!.host}`,
      endpointPort: proxyConfig!.port,
      country: proxyConfig!.country,
      status: "released",
      bytesSent: 1024,
      bytesReceived: 2048,
      estimatedCostUsd: "0.0010",
      lastErrorCode: browserResult?.error ?? null,
      metadataJson: { browserExecuted: browserResult?.creditScore !== null },
      createdAt: startedAt,
      expiresAt: null,
      releasedAt: new Date(),
    });
  }

  await persistWorkerRun({
    jobId: job.id,
    workerNodeId: 1,
    runStatus: "completed",
    attemptNumber: 1,
    profilePolicy: input.profilePolicy ?? "generated",
    fingerprintProfile: input.fingerprintProfile ?? "dynamic",
    runtimeMs: realDurationMs,
    detailsJson: {
      executionMode: browserResult ? "browser_automation" : "simulated",
      providerUsed: providerHint,
      fallbackProvider,
      browserCreditScore: browserResult?.creditScore ?? null,
      browserError: browserResult?.error ?? null,
    },
    createdAt: startedAt,
    finishedAt: new Date(),
  });

  if (input.payload.simulateRetryableError === true) {
    await sleep(350);
    const completedAt = new Date();
    const resultJson = {
      mode: input.requestMode,
      safeTestMode: false,
      providerUsed: providerHint,
      fallbackPrepared: true,
      recoveredAfterRetry: true,
      completedAt: completedAt.toISOString(),
      executionState: "completed_after_retry",
      browserExecuted: !!browserResult,
      oneCsResult,
      summary: computedSummary,
    };

    await updateJobRecord(job.publicId, {
      status: "succeeded",
      resultJson,
      errorCode: null,
      errorMessage: null,
      attemptCount: 2,
      completedAt,
    });

    await persistJobEvents([
      { jobId: job.id, eventType: "worker.retried", severity: "info", message: `Job ${job.publicId} succeeded on retry attempt with provider ${providerHint}.`, eventJson: { attemptNumber: 2, providerHint, fallbackProvider }, createdAt: completedAt },
      { jobId: job.id, eventType: "job.completed", severity: "info", message: `Job ${job.publicId} completed after retry recovery.`, eventJson: { durationMs: realDurationMs, status: oneCsResult.status }, createdAt: completedAt },
    ]);

    await persistWorkerRun({
      jobId: job.id, workerNodeId: 1, runStatus: "completed", attemptNumber: 2,
      profilePolicy: input.profilePolicy ?? null, fingerprintProfile: input.fingerprintProfile ?? null,
      runtimeMs: realDurationMs, detailsJson: { executionMode: "queued_runtime", retried: true, providerUsed: providerHint },
      createdAt: completedAt, finishedAt: completedAt,
    });

    return;
  }

  await sleep(250);
  const completedAt = new Date();
  const resultJson = {
    mode: input.requestMode,
    safeTestMode: false,
    providerUsed: providerHint,
    fallbackPrepared: true,
    completedAt: completedAt.toISOString(),
    executionState: browserResult ? "browser_automation" : "simulated",
    browserExecuted: !!browserResult,
    browserCreditScore: browserResult?.creditScore ?? null,
    oneCsResult,
    summary: computedSummary,
  };

  await updateJobRecord(job.publicId, {
    status: "succeeded",
    resultJson,
    errorCode: browserResult?.error ? "BROWSER_ERROR" : null,
    errorMessage: browserResult?.error ?? null,
    completedAt,
  });

  await persistJobEvents([
    { jobId: job.id, eventType: "worker.completed", severity: "info", message: `Worker completed job ${job.publicId} (${browserResult ? "browser" : "simulated"}).`, eventJson: { durationMs: realDurationMs, providerHint, browserExecuted: !!browserResult }, createdAt: completedAt },
    { jobId: job.id, eventType: "job.completed", severity: "info", message: `Job ${job.publicId} completed in queued runtime mode.`, eventJson: { durationMs: realDurationMs, status: oneCsResult.status }, createdAt: completedAt },
  ]);
}

export async function createSingleJob(input: CreateJobInput, actor: { userId?: number; source: "dashboard" | "api" | "testbench" }) {
  const requestId = createPublicId("req");
  const publicId = createPublicId("job");
  const payloadSize = JSON.stringify(input.payload).length;
  const estimatedCostUsd = estimateCost(input.requestMode, payloadSize);
  const now = new Date();
  const safeTestMode = input.safeTestMode === true;

  const baseStatus: JobStatus = safeTestMode ? "succeeded" : "queued";
  const providerHint = input.proxy?.providerHint ?? "evomi";
  const fallbackProvider = providerHint === "evomi" ? "dataimpulse" : "evomi";
  const payloadRecord = input.payload as Record<string, unknown>;
  const creditScore = inferOneCsCreditScore(payloadRecord);
  const completenessScore = inferOneCsCompletenessScore(payloadRecord);
  const adverseReasons = inferOneCsAdverseReasons(payloadRecord, creditScore);
  const durationMs = Math.round(
    toFiniteNumber(payloadRecord.durationMs) ??
      (input.requestMode === "vip" ? 28_000 : input.requestMode === "bulk" ? 24_000 : 19_000),
  );
  const oneCsResult = buildOneCsResult({
    creditScore,
    completenessScore,
    adverseReasons,
    priceUsd: inferOneCsPriceUsd(input.requestMode, payloadRecord, estimatedCostUsd),
    durationMs,
    source: actor.source,
  });
  const summary = {
    creditScore: oneCsResult.creditScore,
    productScore: oneCsResult.productScore,
    dataQualityScore: oneCsResult.dataQualityScore,
    status: oneCsResult.status,
    adverseReasonCount: oneCsResult.adverseReasons.length,
  };

  const resultJson = safeTestMode
    ? {
        mode: input.requestMode,
        safeTestMode: true,
        providerUsed: providerHint,
        fallbackPrepared: true,
        extractedAt: nowIso(),
        oneCsResult,
        summary,
      }
    : {
        mode: input.requestMode,
        safeTestMode: false,
        providerUsed: providerHint,
        fallbackPrepared: true,
        queuedAt: nowIso(),
        executionState: "queued_for_worker",
        summary,
      };

  const job = await persistJobRecord({
    publicId,
    userId: actor.userId ?? null,
    apiKeyId: null,
    source: actor.source,
    requestMode: input.requestMode,
    status: baseStatus,
    queueName: input.queueName,
    priority: input.priority,
    targetLabel: input.targetLabel ?? null,
    payloadJson: input.payload,
    resultJson,
    errorCode: null,
    errorMessage: null,
    proxyPolicyId: null,
    workerNodeId: 1,
    attemptCount: safeTestMode ? 1 : 0,
    maxAttempts: input.proxy?.maxTransportRetries ? input.proxy.maxTransportRetries + 1 : 3,
    costEstimateUsd: estimatedCostUsd.toFixed(4),
    cogsUsd: (estimatedCostUsd * 0.55).toFixed(4),
    createdAt: now,
    startedAt: safeTestMode ? now : null,
    completedAt: safeTestMode ? now : null,
  });

  const events: Array<{
    type: string;
    severity: "info" | "warn" | "error";
    message: string;
    details: Record<string, unknown>;
  }> = [
    {
      type: "job.created",
      severity: "info",
      message: `Job ${publicId} created in ${safeTestMode ? "safe test" : "queued runtime"} mode.`,
      details: {
        requestMode: input.requestMode,
        queueName: input.queueName,
        providerHint,
      },
    },
    {
      type: "proxy.selection",
      severity: "info",
      message: `Primary provider selected: ${providerHint}.`,
      details: {
        providerHint,
        fallbackProvider,
        sessionMode: input.proxy?.sessionMode ?? "rotating",
      },
    },
  ];

  if (safeTestMode) {
    events.push({
      type: "job.completed",
      severity: "info",
      message: `Job ${publicId} completed inside the safe test bench.`,
      details: {
        durationMs,
        status: oneCsResult.status,
      },
    });
  } else {
    events.push({
      type: "job.queued",
      severity: "info",
      message: `Job ${publicId} accepted into queue ${input.queueName}.`,
      details: {
        queueName: input.queueName,
        maxAttempts: input.proxy?.maxTransportRetries ? input.proxy.maxTransportRetries + 1 : 3,
      },
    });
  }

  if (input.payload.simulateProviderFailure === true) {
    events.push({
      type: "proxy.provider_fallback",
      severity: "warn",
      message: `Primary provider ${providerHint} marked degraded, fallback prepared: ${fallbackProvider}.`,
      details: { from: providerHint, to: fallbackProvider },
    });
  }

  if (input.payload.simulateRetryableError === true) {
    events.push({
      type: "job.waiting_retry",
      severity: "warn",
      message: "Retryable error simulated for stability validation.",
      details: { retryable: true, nextAttempt: 2 },
    });
  }

  await persistJobEvents(
    events.map(event => ({
      jobId: job.id,
      eventType: event.type,
      severity: event.severity,
      message: event.message,
      eventJson: event.details,
      createdAt: now,
    })),
  );
  const savedEvents = await listJobEventsByJobId(job.id);
  const apiEvents = savedEvents.map(event => ({
    id: event.id,
    jobId: event.jobId,
    type: event.eventType,
    severity: event.severity,
    message: event.message,
    details: event.eventJson as Record<string, unknown>,
    createdAt: event.createdAt,
  }));

  await persistProxyLease({
    leaseId: createPublicId("lease"),
    jobId: job.id,
    workerNodeId: 1,
    providerId: providerHint === "dataimpulse" ? 2 : 1,
    policyId: null,
    protocol: input.proxy?.protocol ?? "http",
    sessionMode: input.proxy?.sessionMode ?? "rotating",
    sessionKey: safeTestMode ? `safe_${publicId}` : `queue_${publicId}`,
    endpointHost: `${providerHint}.proxy.internal`,
    endpointPort: input.proxy?.protocol === "socks5" ? 1080 : 9000,
    country: input.proxy?.country ?? null,
    status: safeTestMode ? "released" : "active",
    bytesSent: Math.max(256, payloadSize),
    bytesReceived: Math.max(512, Math.round(payloadSize * 1.5)),
    estimatedCostUsd: estimatedCostUsd.toFixed(4),
    lastErrorCode: input.payload.simulateProviderFailure === true ? "PROVIDER_DEGRADED" : null,
    metadataJson: {
      providerHint,
      fallbackProvider,
      targetLabel: input.targetLabel ?? null,
    },
    createdAt: now,
    expiresAt: safeTestMode ? now : new Date(now.getTime() + 15 * 60 * 1000),
    releasedAt: safeTestMode ? now : null,
  });

  if (safeTestMode) {
    await persistWorkerRun({
      jobId: job.id,
      workerNodeId: 1,
      runStatus: "completed",
      attemptNumber: 1,
      profilePolicy: input.profilePolicy ?? null,
      fingerprintProfile: input.fingerprintProfile ?? null,
      runtimeMs: durationMs,
      detailsJson: {
        safeTestMode: true,
        providerUsed: providerHint,
      },
      createdAt: now,
      finishedAt: now,
    });
  }

  const unitCostUsd = estimatedCostUsd;
  const revenueUsd = inferOneCsPriceUsd(input.requestMode, payloadRecord, estimatedCostUsd);
  await persistUsageRecord({
    userId: actor.userId ?? null,
    apiKeyId: null,
    jobId: job.id,
    metricType: input.requestMode === "bulk" ? "bulk_item" : "request",
    quantity: "1.0000",
    unitCostUsd: unitCostUsd.toFixed(4),
    totalCostUsd: unitCostUsd.toFixed(4),
    periodKey: getCurrentPeriodKey(now),
    metadataJson: {
      requestMode: input.requestMode,
      revenueUsd,
      safeTestMode,
    },
    createdAt: now,
  });

  if (input.requestMode === "vip") {
    await persistUsageRecord({
      userId: actor.userId ?? null,
      apiKeyId: null,
      jobId: job.id,
      metricType: "browser_run",
      quantity: "1.0000",
      unitCostUsd: "0.0000",
      totalCostUsd: "0.0000",
      periodKey: getCurrentPeriodKey(now),
      metadataJson: {
        source: actor.source,
        safeTestMode,
      },
      createdAt: now,
    });
  }

  await persistAuditTrailEntry({
    actorUserId: actor.userId ?? null,
    actorType: actor.source === "api" ? "api_key" : "user",
    action: "job.create",
    resourceType: "job",
    resourceId: publicId,
    status: "success",
    ipAddress: null,
    detailsJson: {
      requestMode: input.requestMode,
      queueName: input.queueName,
      safeTestMode,
      providerHint,
    },
    createdAt: now,
  });

  if (!safeTestMode) {
    void executeQueuedJobLifecycle({
      job,
      input,
      actor,
      providerHint,
      fallbackProvider,
      durationMs,
      oneCsResult,
      summary,
    }).catch(error => {
      console.error(`[ONE CS] queued job lifecycle failed for ${job.publicId}`, error);
    });
  }

  return buildApiResponse(requestId, { job, events: apiEvents }, {
    safeTestMode,
    persisted: true,
    executionMode: safeTestMode ? "safe_test" : "queued_runtime",
  });
}

export async function createBulkJob(input: CreateBulkJobInput, actor: { userId?: number; source: "api" | "dashboard" | "testbench" }) {
  const requestId = createPublicId("req");

  const items = input.items.map((item, index) => {
    const syntheticInput: CreateJobInput = {
      requestMode: "bulk",
      queueName: input.queueName,
      priority: input.priority,
      payload: item.payload,
      proxy: input.proxy,
      safeTestMode: input.safeTestMode,
      targetLabel: item.externalId ?? `bulk-item-${index + 1}`,
    };

    return createSingleJob(syntheticInput, actor);
  });

  const resolved = await Promise.all(items);

  return buildApiResponse(
    requestId,
    {
      batchId: createPublicId("batch"),
      itemCount: resolved.length,
      jobs: resolved.map(result => result.data.job),
    },
    {
      safeTestMode: input.safeTestMode,
      queueName: input.queueName,
    },
  );
}

export async function createApiKeyRecord(userId: number, input: CreateApiKeyInput) {
  const rawToken = `cs_${input.scope}_${randomBytes(18).toString("hex")}`;
  const keyPrefix = rawToken.slice(0, 16);
  const now = new Date();
  const record = await persistApiKeyRecord({
    userId,
    label: input.label,
    keyPrefix,
    keyHash: hashToken(rawToken),
    scope: input.scope,
    status: "active",
    rpmLimit: input.rpmLimit,
    dailyLimit: input.dailyLimit,
    createdAt: now,
    updatedAt: now,
    expiresAt: input.expiresAt ? new Date(input.expiresAt) : null,
    lastUsedAt: null,
  });

  await persistAuditTrailEntry({
    actorUserId: userId,
    actorType: "user",
    action: "apikey.create",
    resourceType: "api_key",
    resourceId: keyPrefix,
    status: "success",
    ipAddress: null,
    detailsJson: {
      scope: input.scope,
      rpmLimit: input.rpmLimit,
      dailyLimit: input.dailyLimit,
    },
    createdAt: now,
  });

  return {
    preview: rawToken,
    record,
  };
}

export async function listUserApiKeys(userId?: number) {
  return listApiKeysForUser(userId);
}

export async function revokeUserApiKey(userId: number, id: number) {
  const existing = (await listApiKeysForUser(userId)).find(apiKey => apiKey.id === id);
  if (!existing) {
    throw new Error("API key not found");
  }

  if (existing.status === "revoked") {
    return existing;
  }

  const revoked = await revokeApiKeyRecord(id);
  if (!revoked) {
    throw new Error("Failed to revoke API key");
  }

  await persistAuditTrailEntry({
    actorUserId: userId,
    actorType: "user",
    action: "apikey.revoke",
    resourceType: "api_key",
    resourceId: revoked.keyPrefix,
    status: "success",
    ipAddress: null,
    detailsJson: {
      scope: revoked.scope,
      previousStatus: existing.status,
      nextStatus: revoked.status,
    },
    createdAt: new Date(),
  });

  return revoked;
}

export async function getSafeTestBench() {
  return {
    scenarios: SAFE_TEST_SCENARIOS,
    mockHealth: MOCK_HEALTH_SUMMARY,
    sampleJob: findMockJob("job_mock_success_001"),
    sampleEvents: listMockJobEvents(1),
    guidance: [
      "Use safe test mode for all manual validation before enabling real integrations.",
      "Validate queue transitions, proxy fallback, rate limiting and audit events independently.",
      "Treat all simulated transport failures as opportunities to inspect observability paths.",
      "Redact sensitive imported records before converting them into queue payloads.",
    ],
  };
}

export async function previewImportedLeadText(inputText: string) {
  const parsed = parseImportedLeadText(inputText);
  const safeRecords = parsed.map(toSafeImportedLeadRecord);
  const stateBreakdown = safeRecords.reduce<Record<string, number>>((acc, record) => {
    const key = record.state ?? "unknown";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  return {
    totalRecords: safeRecords.length,
    sourceLabels: Array.from(new Set(safeRecords.map(record => record.sourceLabel).filter(Boolean))),
    stateBreakdown,
    withPhone: safeRecords.filter(record => record.phoneNumbers.length > 0).length,
    withEmailDomain: safeRecords.filter(record => Boolean(record.emailDomain)).length,
    withDob: safeRecords.filter(record => Boolean(record.dobText)).length,
    withSsnMarker: safeRecords.filter(record => record.hasSsn).length,
    averageCompletenessScore:
      safeRecords.length > 0
        ? Number(
            (
              safeRecords.reduce((sum, record) => sum + record.completenessScore, 0) /
              safeRecords.length
            ).toFixed(2),
          )
        : 0,
    sampleRecords: safeRecords.slice(0, 10),
    safePayloads: buildSafeLeadImportPayloads(inputText).slice(0, 25),
  };
}

export async function createSafeImportedLeadBatch(
  inputText: string,
  actor: { userId?: number; source: "api" | "dashboard" | "testbench" },
) {
  const safePayloads = buildSafeLeadImportPayloads(inputText);

  return createBulkJob(
    {
      queueName: "lead-import",
      priority: 110,
      safeTestMode: true,
      items: safePayloads.map((payload, index) => ({
        externalId: payload.targetLabel ?? `lead-import-${index + 1}`,
        payload: payload.payload,
      })),
    },
    actor,
  );
}

export async function getApiUsageSummary() {
  const apiKeys = await listApiKeysForUser();
  return {
    apiKeys,
    usageSummary: getRuntimeUsageSummary() ?? MOCK_USAGE_SUMMARY,
  };
}

export function assertVipScope(scope: string) {
  return scope === "vip" || scope === "admin";
}

export function deriveRateLimit(scope: string) {
  switch (scope) {
    case "admin":
      return { rpm: 600, daily: 100000 };
    case "vip":
      return { rpm: 300, daily: 25000 };
    case "bulk":
      return { rpm: 120, daily: 5000 };
    default:
      return { rpm: 60, daily: 1000 };
  }
}

const DEFAULT_BOT_TEXT_LIBRARY = [
  {
    key: "maintenanceBanner",
    title: "Maintenance banner",
    description: "Короткое сервисное сообщение для аварийного или планового баннера.",
    body: "Сервис временно работает в ограниченном режиме. Пожалуйста, повторите попытку немного позже.",
  },
  {
    key: "paymentReminder",
    title: "Payment reminder",
    description: "Текст напоминания об оплате или продлении доступа.",
    body: "Напоминаем, что срок оплаты подходит к концу. Если платёж уже отправлен, просто дождитесь подтверждения.",
  },
  {
    key: "retryNotice",
    title: "Retry notice",
    description: "Сообщение для временной ошибки, когда операция будет повторена автоматически.",
    body: "Мы получили временную ошибку и уже поставили запрос на повторную обработку. Дополнительных действий пока не требуется.",
  },
  {
    key: "supportReply",
    title: "Support reply",
    description: "Базовый ответ поддержки для ручных операторских сообщений.",
    body: "Спасибо за обращение. Мы уже проверяем ситуацию и вернёмся с обновлением, как только получим подтверждение по вашему кейсу.",
  },
  {
    key: "welcome",
    title: "Welcome",
    description: "Приветственное сообщение бота для новых пользователей.",
    body: "Добро пожаловать. Бот готов помочь с запросами, статусами и сервисными уведомлениями.",
  },
] as const;

type BotTextModuleRow = {
  id: number;
  key: string;
  title: string;
  description: string | null;
  body: string;
  updatedByUserId: number | null;
  createdAt: Date;
  updatedAt: Date;
};

type BroadcastRecipientTarget = {
  chatId: string;
  label: string;
  source: "linked_telegram_users" | "manual_chat_ids";
};

function normalizeChatIds(input: string[]) {
  return Array.from(
    new Set(
      input
        .map(item => item.trim())
        .filter(Boolean),
    ),
  );
}

async function ensureDefaultBotTexts() {
  const { listBotTextSettings, upsertBotTextSetting } = await import("./db");
  const existing = await listBotTextSettings();
  if (existing.length > 0) {
    return existing;
  }

  const now = new Date();
  const seeded = await Promise.all(
    DEFAULT_BOT_TEXT_LIBRARY.map(item =>
      upsertBotTextSetting({
        key: item.key,
        title: item.title,
        description: item.description,
        body: item.body,
        updatedByUserId: null,
        updatedAt: now,
      }),
    ),
  );

  return seeded;
}

function sortBotTexts(records: BotTextModuleRow[]) {
  return records.slice().sort((a, b) => a.key.localeCompare(b.key));
}

async function resolveBroadcastRecipients(input: {
  audience: "linked_telegram_users" | "manual_chat_ids";
  manualChatIds?: string[];
}) {
  const { listTelegramRecipients } = await import("./db");

  if (input.audience === "manual_chat_ids") {
    return normalizeChatIds(input.manualChatIds ?? []).map(chatId => ({
      chatId,
      label: `manual:${chatId}`,
      source: "manual_chat_ids" as const,
    }));
  }

  const linked = await listTelegramRecipients({ activeOnly: true });
  return normalizeChatIds(linked.map(item => item.chatId)).map(chatId => {
    const recipient = linked.find(item => item.chatId === chatId);
    return {
      chatId,
      label: recipient ? `${recipient.botLabel} · ${chatId}` : chatId,
      source: "linked_telegram_users" as const,
    };
  });
}

async function sendTelegramMessage(params: { botToken: string; chatId: string; text: string }) {
  const response = await fetch(`https://api.telegram.org/bot${params.botToken}/sendMessage`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      chat_id: params.chatId,
      text: params.text,
      disable_web_page_preview: true,
    }),
  });

  const payload = (await response.json().catch(() => null)) as
    | { ok?: boolean; description?: string; result?: { message_id?: number } }
    | null;

  if (!response.ok || !payload?.ok) {
    throw new Error(payload?.description || `Telegram API responded with ${response.status}`);
  }

  return {
    ok: true,
    messageId: payload.result?.message_id ?? null,
  } as const;
}

export async function getBotTextsModule() {
  const texts = sortBotTexts((await ensureDefaultBotTexts()) as BotTextModuleRow[]);
  const { listTelegramRecipients } = await import("./db");
  const recipients = await listTelegramRecipients();

  return {
    texts,
    recipients,
    summary: {
      totalTemplates: texts.length,
      totalRecipients: recipients.length,
      activeRecipients: recipients.filter(item => item.status === "active").length,
      telegramConfigured: Boolean(process.env.BOT_TOKEN),
    },
  };
}

export async function updateBotTextTemplate(
  input: {
    key: string;
    body: string;
    title?: string;
    description?: string;
  },
  actor: { userId: number | null },
) {
  const { listBotTextSettings, persistAuditTrailEntry, upsertBotTextSetting } = await import("./db");
  const existingRows = await ensureDefaultBotTexts();
  const existing = existingRows.find(item => item.key === input.key) ?? (await listBotTextSettings()).find(item => item.key === input.key) ?? null;
  const now = new Date();

  const saved = await upsertBotTextSetting({
    key: input.key,
    title: input.title?.trim() || existing?.title || input.key,
    description: input.description?.trim() || existing?.description || null,
    body: input.body,
    updatedByUserId: actor.userId,
    updatedAt: now,
  });

  await persistAuditTrailEntry({
    actorUserId: actor.userId,
    actorType: actor.userId ? "user" : "system",
    action: "bot_text.updated",
    resourceType: "bot_text",
    resourceId: input.key,
    status: "success",
    ipAddress: null,
    detailsJson: {
      title: saved.title,
      bodyLength: saved.body.length,
      updatedAt: saved.updatedAt.toISOString(),
    },
    createdAt: now,
  });

  return saved;
}

export async function getBroadcastsModule() {
  const { listRuntimeBroadcasts } = await import("./runtimeStore");
  const recipients = await resolveBroadcastRecipients({ audience: "linked_telegram_users" });
  const history = listRuntimeBroadcasts();

  return {
    recipients,
    history,
    summary: {
      totalBroadcasts: history.length,
      completedBroadcasts: history.filter(item => item.status === "completed").length,
      failedBroadcasts: history.filter(item => item.status === "failed").length,
      linkedRecipients: recipients.length,
      telegramConfigured: Boolean(process.env.BOT_TOKEN),
    },
  };
}

export async function createBroadcastCampaign(
  input: {
    title: string;
    message: string;
    audience: "linked_telegram_users" | "manual_chat_ids";
    parseMode?: "plain";
    manualChatIds?: string[];
    dryRun?: boolean;
  },
  actor: { userId: number | null },
) {
  const { persistAuditTrailEntry } = await import("./db");
  const { saveRuntimeBroadcast } = await import("./runtimeStore");
  const requestedAt = new Date();
  const recipients = await resolveBroadcastRecipients({
    audience: input.audience,
    manualChatIds: input.manualChatIds,
  });

  if (recipients.length === 0) {
    throw new Error(
      input.audience === "linked_telegram_users"
        ? "Нет активных Telegram-получателей. Добавьте chatId в telegramEndpoints или используйте manual chat IDs."
        : "Укажите хотя бы один manual chat ID для рассылки.",
    );
  }

  const botToken = process.env.BOT_TOKEN?.trim() ?? "";
  const dryRun = input.dryRun ?? false;
  if (!dryRun && !botToken) {
    throw new Error("BOT_TOKEN не настроен в серверном окружении, поэтому реальную Telegram-рассылку выполнить нельзя.");
  }

  const results = await Promise.all(
    recipients.map(async recipient => {
      if (dryRun) {
        return {
          chatId: recipient.chatId,
          label: recipient.label,
          source: recipient.source,
          ok: true,
          simulated: true,
          error: null,
          messageId: null,
        };
      }

      try {
        const response = await sendTelegramMessage({
          botToken,
          chatId: recipient.chatId,
          text: input.message,
        });
        return {
          chatId: recipient.chatId,
          label: recipient.label,
          source: recipient.source,
          ok: true,
          simulated: false,
          error: null,
          messageId: response.messageId,
        };
      } catch (error) {
        return {
          chatId: recipient.chatId,
          label: recipient.label,
          source: recipient.source,
          ok: false,
          simulated: false,
          error: error instanceof Error ? error.message : "Unknown Telegram send error",
          messageId: null,
        };
      }
    }),
  );

  const deliveredCount = results.filter(item => item.ok).length;
  const failedCount = results.length - deliveredCount;
  const status =
    failedCount === 0 ? "completed" : deliveredCount === 0 ? "failed" : "partial";

  const saved = saveRuntimeBroadcast({
    publicId: createPublicId("broadcast"),
    title: input.title,
    message: input.message,
    audience: input.audience,
    parseMode: input.parseMode ?? "plain",
    status,
    dryRun,
    requestedByUserId: actor.userId,
    requestedRecipients: recipients.length,
    deliveredCount,
    failedCount,
    recipientsJson: recipients,
    resultsJson: results,
    createdAt: requestedAt,
    completedAt: new Date(),
  });

  await persistAuditTrailEntry({
    actorUserId: actor.userId,
    actorType: actor.userId ? "user" : "system",
    action: dryRun ? "broadcast.dry_run" : "broadcast.sent",
    resourceType: "broadcast",
    resourceId: saved.publicId,
    status: failedCount > 0 ? "failure" : "success",
    ipAddress: null,
    detailsJson: {
      audience: input.audience,
      requestedRecipients: recipients.length,
      deliveredCount,
      failedCount,
      dryRun,
      title: input.title,
    },
    createdAt: requestedAt,
  });

  return {
    ...saved,
    results,
  };
}
