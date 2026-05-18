import { and, desc, eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  apiKeys,
  auditTrail,
  InsertUser,
  jobEvents,
  jobs,
  metricSnapshots,
  payments,
  plans,
  proxyLeases,
  proxyPolicies,
  proxyProviders,
  subscriptions,
  systemSettings,
  telegramEndpoints,
  usageRecords,
  users,
  workerNodes,
  workerRuns,
} from "../drizzle/schema";
import type { DashboardMetricCard } from "../shared/platform";
import { ENV } from "./_core/env";
import {
  findMockJob,
  getMockDashboardSummary,
  listMockAuditTrail,
  listMockJobEvents,
  MOCK_API_KEYS,
  MOCK_JOBS,
  MOCK_PAYMENTS,
  MOCK_PLANS,
  MOCK_PROXY_POLICIES,
  MOCK_PROXY_PROVIDERS,
  MOCK_SUBSCRIPTIONS,
  MOCK_WORKER_NODES,
} from "./platformMockData";
import {
  findRuntimeApiKeyByHash,
  findRuntimeJob,
  getRuntimeUsageSummary,
  listRuntimeApiKeys,
  listRuntimeAuditTrailEntries,
  listRuntimeBotTexts,
  listRuntimeJobEventsByJobId,
  listRuntimeJobs,
  listRuntimeTelegramRecipients,
  saveRuntimeApiKey,
  saveRuntimeAuditTrailEntry,
  saveRuntimeBotText,
  saveRuntimeJob,
  saveRuntimeJobEvents,
  saveRuntimeProxyLease,
  saveRuntimeUsageRecord,
  saveRuntimeWorkerRun,
  updateRuntimeApiKey,
  updateRuntimeJob,
} from "./runtimeStore";

let _db: ReturnType<typeof drizzle> | null = null;

type SubscriptionRow = {
  id: number;
  userId: number;
  planId: number;
  status: string;
  provider: string;
  externalRef: string | null;
  startedAt: Date | null;
  currentPeriodStart: Date | null;
  currentPeriodEnd: Date | null;
  canceledAt?: Date | null;
  metadataJson?: unknown;
  createdAt?: Date;
  updatedAt?: Date;
};

type PaymentRow = {
  id: number;
  userId: number;
  subscriptionId: number | null;
  provider: string;
  status: string;
  currency: string;
  amount: string;
  amountUsd: string | null;
  txRef: string | null;
  invoiceRef: string | null;
  paidAt: Date | null;
  createdAt?: Date;
  updatedAt?: Date;
};

type AuditTrailRow = {
  id: number;
  actorUserId: number | null;
  actorType: string;
  action: string;
  resourceType: string;
  resourceId: string;
  status: string;
  ipAddress: string | null;
  detailsJson: unknown;
  createdAt: Date;
};

type BotTextSettingRow = {
  id: number;
  key: string;
  title: string;
  description: string | null;
  body: string;
  updatedByUserId: number | null;
  createdAt: Date;
  updatedAt: Date;
};

type TelegramRecipientRow = {
  id: number;
  userId: number | null;
  botLabel: string;
  chatId: string;
  status: string;
  commandScope: string;
  metadataJson: unknown;
  createdAt: Date;
  updatedAt: Date;
};

type ApiKeyRow = {
  id: number;
  userId: number;
  label: string;
  keyPrefix: string;
  scope: string;
  status: string;
  rpmLimit: number;
  dailyLimit: number;
  lastUsedAt: Date | null;
  expiresAt: Date | null;
  createdAt?: Date;
  updatedAt?: Date;
};

export type ApiKeyAuthRow = ApiKeyRow & {
  keyHash: string;
};

type PlanRow = {
  id: number;
  code: string;
  name: string;
  tier: string;
  billingInterval: string;
  currency: string;
  priceUsd: string;
  includedRequests: number;
  monthlyApiQuota: number;
  monthlyBrowserRuns: number;
  maxRpm: number;
  maxConcurrentJobs: number;
  vipApiAccess: string;
  featuresJson: unknown;
  isActive: string;
  createdAt?: Date;
  updatedAt?: Date;
};

type WorkerNodeRow = {
  id: number;
  code: string;
  name: string;
  role: string;
  status: string;
  concurrencyLimit: number;
  activeJobs: number;
  version: string | null;
  hostLabel: string | null;
  capabilitiesJson: unknown;
  lastHeartbeatAt: Date | null;
  createdAt?: Date;
  updatedAt?: Date;
};

type ProxyProviderRow = {
  id: number;
  code: string;
  name: string;
  protocolSupport: string;
  sessionSupport: string;
  costPerGbUsd: string;
  priority: number;
  status: string;
  notes: string | null;
  configJson: unknown;
  createdAt?: Date;
  updatedAt?: Date;
};

type ProxyPolicyRow = {
  id: number;
  code: string;
  name: string;
  protocol: string;
  sessionMode: string;
  stickyTtlMinutes: number | null;
  country: string | null;
  state: string | null;
  city: string | null;
  maxTransportRetries: number;
  maxProviderSwitches: number;
  costCeilingUsd: string;
  isDefault: string;
  policyJson: unknown;
  createdAt?: Date;
  updatedAt?: Date;
};

type JobEventRow = {
  id: number;
  jobId: number;
  eventType: string;
  severity: string;
  message: string;
  eventJson: unknown;
  createdAt: Date;
};

type JobRow = {
  id: number;
  publicId: string;
  userId: number | null;
  apiKeyId: number | null;
  source: string;
  requestMode: string;
  status: string;
  queueName: string;
  priority: number;
  targetLabel: string | null;
  payloadJson: unknown;
  resultJson: unknown;
  errorCode: string | null;
  errorMessage: string | null;
  proxyPolicyId: number | null;
  workerNodeId: number | null;
  attemptCount: number;
  maxAttempts: number;
  costEstimateUsd: string | null;
  cogsUsd: string | null;
  createdAt: Date;
  startedAt: Date | null;
  completedAt: Date | null;
};

type DashboardSummaryRow = {
  metrics: DashboardMetricCard[];
  jobs: JobRow[];
  providers: ProxyProviderRow[];
  workers: WorkerNodeRow[];
  plans: PlanRow[];
  usage: unknown;
  safeTestScenarios: unknown[];
  health: unknown;
};

export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }

  return _db;
}

async function withMockFallback<T>(
  label: string,
  runQuery: (db: NonNullable<Awaited<ReturnType<typeof getDb>>>) => Promise<T>,
  getFallback: () => T | Promise<T>,
): Promise<T> {
  const db = await getDb();
  if (!db) {
    return getFallback();
  }

  try {
    return await runQuery(db);
  } catch (error) {
    console.warn(`[Database] ${label} failed, using mock fallback`, error);
    return await getFallback();
  }
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available, using mock-safe mode");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod", "telegramChatId", "status"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized as never;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }

    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = "admin";
      updateSet.role = "admin";
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  return withMockFallback(
    "getUserByOpenId",
    async db => {
      const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);
      return result.length > 0 ? result[0] : undefined;
    },
    () => ({
      id: 1,
      openId,
      email: "owner@example.com",
      name: process.env.OWNER_NAME ?? "Owner",
      loginMethod: "manus",
      role: openId === ENV.ownerOpenId ? ("admin" as const) : ("user" as const),
      telegramChatId: null,
      status: "active" as const,
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
    }),
  );
}

export async function getDashboardSummary(): Promise<DashboardSummaryRow> {
  const mock = getMockDashboardSummary();
  const runtimeUsage = getRuntimeUsageSummary();

  return {
    metrics: mock.metrics,
    jobs: (await listJobs()).slice(0, 10),
    providers: await listProxyProviders(),
    workers: await listWorkerNodes(),
    plans: await listPlans(),
    usage: runtimeUsage ?? mock.usage,
    safeTestScenarios: mock.safeTestScenarios,
    health: mock.health,
  };
}

export async function listJobs(): Promise<JobRow[]> {
  return withMockFallback<JobRow[]>(
    "listJobs",
    async db => {
      const rows = await db.select().from(jobs).orderBy(desc(jobs.createdAt)).limit(100);
      return rows.map(row => ({
        id: row.id,
        publicId: row.publicId,
        userId: row.userId ?? null,
        apiKeyId: row.apiKeyId ?? null,
        source: String(row.source),
        requestMode: String(row.requestMode),
        status: String(row.status),
        queueName: row.queueName,
        priority: row.priority,
        targetLabel: row.targetLabel,
        payloadJson: row.payloadJson as unknown,
        resultJson: row.resultJson as unknown,
        errorCode: row.errorCode ?? null,
        errorMessage: row.errorMessage ?? null,
        proxyPolicyId: row.proxyPolicyId ?? null,
        workerNodeId: row.workerNodeId ?? null,
        attemptCount: row.attemptCount,
        maxAttempts: row.maxAttempts,
        costEstimateUsd: row.costEstimateUsd ? String(row.costEstimateUsd) : null,
        cogsUsd: row.cogsUsd ? String(row.cogsUsd) : null,
        createdAt: row.createdAt,
        startedAt: row.startedAt ?? null,
        completedAt: row.completedAt ?? null,
      }));
    },
    () => {
      const runtimeJobs = listRuntimeJobs();
      if (runtimeJobs.length > 0) {
        return runtimeJobs;
      }

      return [...MOCK_JOBS]
        .sort((a, b) => b.createdAt - a.createdAt)
        .map(row => ({
          id: row.id,
          publicId: row.publicId,
          userId: row.userId ?? null,
          apiKeyId: row.apiKeyId ?? null,
          source: String(row.source),
          requestMode: String(row.requestMode),
          status: String(row.status),
          queueName: row.queueName,
          priority: row.priority,
          targetLabel: row.targetLabel,
          payloadJson: row.payloadJson,
          resultJson: row.resultJson,
          errorCode: row.errorCode ?? null,
          errorMessage: row.errorMessage ?? null,
          proxyPolicyId: row.proxyPolicyId ?? null,
          workerNodeId: row.workerNodeId ?? null,
          attemptCount: row.attemptCount,
          maxAttempts: row.maxAttempts,
          costEstimateUsd: row.costEstimateUsd ?? null,
          cogsUsd: row.cogsUsd ?? null,
          createdAt: new Date(row.createdAt),
          startedAt: row.startedAt ? new Date(row.startedAt) : null,
          completedAt: row.completedAt ? new Date(row.completedAt) : null,
        }));
    },
  );
}

export async function getJobByPublicId(publicId: string): Promise<JobRow | null> {
  return withMockFallback<JobRow | null>(
    "getJobByPublicId",
    async db => {
      const result = await db.select().from(jobs).where(eq(jobs.publicId, publicId)).limit(1);
      const row = result[0];
      if (!row) return null;
      return {
        id: row.id,
        publicId: row.publicId,
        userId: row.userId ?? null,
        apiKeyId: row.apiKeyId ?? null,
        source: String(row.source),
        requestMode: String(row.requestMode),
        status: String(row.status),
        queueName: row.queueName,
        priority: row.priority,
        targetLabel: row.targetLabel,
        payloadJson: row.payloadJson as unknown,
        resultJson: row.resultJson as unknown,
        errorCode: row.errorCode ?? null,
        errorMessage: row.errorMessage ?? null,
        proxyPolicyId: row.proxyPolicyId ?? null,
        workerNodeId: row.workerNodeId ?? null,
        attemptCount: row.attemptCount,
        maxAttempts: row.maxAttempts,
        costEstimateUsd: row.costEstimateUsd ? String(row.costEstimateUsd) : null,
        cogsUsd: row.cogsUsd ? String(row.cogsUsd) : null,
        createdAt: row.createdAt,
        startedAt: row.startedAt ?? null,
        completedAt: row.completedAt ?? null,
      };
    },
    () => {
      const runtimeJob = findRuntimeJob(publicId);
      if (runtimeJob) {
        return runtimeJob;
      }

      const row = findMockJob(publicId);
      if (!row) return null;
      return {
        id: row.id,
        publicId: row.publicId,
        userId: row.userId ?? null,
        apiKeyId: row.apiKeyId ?? null,
        source: String(row.source),
        requestMode: String(row.requestMode),
        status: String(row.status),
        queueName: row.queueName,
        priority: row.priority,
        targetLabel: row.targetLabel,
        payloadJson: row.payloadJson,
        resultJson: row.resultJson,
        errorCode: row.errorCode ?? null,
        errorMessage: row.errorMessage ?? null,
        proxyPolicyId: row.proxyPolicyId ?? null,
        workerNodeId: row.workerNodeId ?? null,
        attemptCount: row.attemptCount,
        maxAttempts: row.maxAttempts,
        costEstimateUsd: row.costEstimateUsd ?? null,
        cogsUsd: row.cogsUsd ?? null,
        createdAt: new Date(row.createdAt),
        startedAt: row.startedAt ? new Date(row.startedAt) : null,
        completedAt: row.completedAt ? new Date(row.completedAt) : null,
      };
    },
  );
}

export async function listJobEventsByJobId(jobId: number): Promise<JobEventRow[]> {
  return withMockFallback<JobEventRow[]>(
    "listJobEventsByJobId",
    async db => {
      const rows = await db
        .select()
        .from(jobEvents)
        .where(eq(jobEvents.jobId, jobId))
        .orderBy(desc(jobEvents.createdAt))
        .limit(100);

      return rows.map(row => ({
        id: row.id,
        jobId: row.jobId,
        eventType: row.eventType,
        severity: String(row.severity),
        message: row.message,
        eventJson: row.eventJson as unknown,
        createdAt: row.createdAt,
      }));
    },
    () => {
      const runtimeEvents = listRuntimeJobEventsByJobId(jobId);
      if (runtimeEvents.length > 0) {
        return runtimeEvents;
      }

      return listMockJobEvents(jobId).map(row => ({
        id: row.id,
        jobId: row.jobId,
        eventType: row.eventType,
        severity: String(row.severity),
        message: row.message,
        eventJson: row.eventJson as unknown,
        createdAt: row.createdAt,
      }));
    },
  );
}

export async function listProxyProviders(): Promise<ProxyProviderRow[]> {
  return withMockFallback<ProxyProviderRow[]>(
    "listProxyProviders",
    async db => {
      const rows = await db.select().from(proxyProviders).orderBy(proxyProviders.priority);
      return rows.map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        protocolSupport: row.protocolSupport,
        sessionSupport: row.sessionSupport,
        costPerGbUsd: String(row.costPerGbUsd),
        priority: row.priority,
        status: String(row.status),
        notes: row.notes ?? null,
        configJson: row.configJson,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      [...MOCK_PROXY_PROVIDERS]
        .sort((a, b) => a.priority - b.priority)
        .map(row => ({
          id: row.id,
          code: row.code,
          name: row.name,
          protocolSupport: row.protocolSupport,
          sessionSupport: row.sessionSupport,
          costPerGbUsd: row.costPerGbUsd,
          priority: row.priority,
          status: String(row.status),
          notes: row.notes ?? null,
          configJson: row.configJson,
        })),
  );
}

export async function listProxyPolicies(): Promise<ProxyPolicyRow[]> {
  return withMockFallback<ProxyPolicyRow[]>(
    "listProxyPolicies",
    async db => {
      const rows = await db.select().from(proxyPolicies).orderBy(desc(proxyPolicies.isDefault), proxyPolicies.name);
      return rows.map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        protocol: String(row.protocol),
        sessionMode: String(row.sessionMode),
        stickyTtlMinutes: row.stickyTtlMinutes ?? null,
        country: row.country ?? null,
        state: row.state ?? null,
        city: row.city ?? null,
        maxTransportRetries: row.maxTransportRetries,
        maxProviderSwitches: row.maxProviderSwitches,
        costCeilingUsd: String(row.costCeilingUsd),
        isDefault: String(row.isDefault),
        policyJson: row.policyJson,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      [...MOCK_PROXY_POLICIES].map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        protocol: String(row.protocol),
        sessionMode: String(row.sessionMode),
        stickyTtlMinutes: row.stickyTtlMinutes ?? null,
        country: row.country ?? null,
        state: row.state ?? null,
        city: row.city ?? null,
        maxTransportRetries: row.maxTransportRetries,
        maxProviderSwitches: row.maxProviderSwitches,
        costCeilingUsd: row.costCeilingUsd,
        isDefault: String(row.isDefault),
        policyJson: row.policyJson,
      })),
  );
}

export async function listWorkerNodes(): Promise<WorkerNodeRow[]> {
  return withMockFallback<WorkerNodeRow[]>(
    "listWorkerNodes",
    async db => {
      const rows = await db.select().from(workerNodes).orderBy(workerNodes.name);
      return rows.map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        role: String(row.role),
        status: String(row.status),
        concurrencyLimit: row.concurrencyLimit,
        activeJobs: row.activeJobs,
        version: row.version ?? null,
        hostLabel: row.hostLabel ?? null,
        capabilitiesJson: row.capabilitiesJson,
        lastHeartbeatAt: row.lastHeartbeatAt ?? null,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      [...MOCK_WORKER_NODES].map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        role: String(row.role),
        status: String(row.status),
        concurrencyLimit: row.concurrencyLimit,
        activeJobs: row.activeJobs,
        version: row.version ?? null,
        hostLabel: row.hostLabel ?? null,
        capabilitiesJson: row.capabilitiesJson,
        lastHeartbeatAt: new Date(row.lastHeartbeatAt),
      })),
  );
}

export async function listApiKeysForUser(userId?: number): Promise<ApiKeyRow[]> {
  return withMockFallback<ApiKeyRow[]>(
    "listApiKeysForUser",
    async db => {
      const rows = !userId
        ? await db.select().from(apiKeys).orderBy(desc(apiKeys.createdAt)).limit(100)
        : await db.select().from(apiKeys).where(eq(apiKeys.userId, userId)).orderBy(desc(apiKeys.createdAt)).limit(100);

      const databaseKeys = rows.map(row => ({
        id: row.id,
        userId: row.userId,
        label: row.label,
        keyPrefix: row.keyPrefix,
        scope: String(row.scope),
        status: String(row.status),
        rpmLimit: row.rpmLimit,
        dailyLimit: row.dailyLimit,
        lastUsedAt: row.lastUsedAt ?? null,
        expiresAt: row.expiresAt ?? null,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));

      const runtimeKeys = listRuntimeApiKeys(userId).map(row => ({
        id: row.id,
        userId: row.userId,
        label: row.label,
        keyPrefix: row.keyPrefix,
        scope: String(row.scope),
        status: String(row.status),
        rpmLimit: row.rpmLimit,
        dailyLimit: row.dailyLimit,
        lastUsedAt: row.lastUsedAt ?? null,
        expiresAt: row.expiresAt ?? null,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));

      const merged = [...runtimeKeys, ...databaseKeys];
      const seen = new Set<string>();
      return merged.filter(row => {
        if (seen.has(row.keyPrefix)) {
          return false;
        }
        seen.add(row.keyPrefix);
        return true;
      });
    },
    () => {
      const runtimeApiKeys = listRuntimeApiKeys(userId);
      if (runtimeApiKeys.length > 0) {
        return runtimeApiKeys;
      }

      return (userId ? MOCK_API_KEYS.filter(key => key.userId === userId) : [...MOCK_API_KEYS]).map(row => ({
        id: row.id,
        userId: row.userId,
        label: row.label,
        keyPrefix: row.keyPrefix,
        scope: String(row.scope),
        status: String(row.status),
        rpmLimit: row.rpmLimit,
        dailyLimit: row.dailyLimit,
        lastUsedAt: new Date(row.lastUsedAt),
        expiresAt: row.expiresAt ? new Date(row.expiresAt) : null,
      }));
    },
  );
}

export async function findApiKeyAuthRecordByHash(keyHash: string): Promise<ApiKeyAuthRow | null> {
  const db = await getDb();
  if (!db) {
    const runtimeRecord = findRuntimeApiKeyByHash(keyHash);
    return runtimeRecord
      ? {
          ...runtimeRecord,
          scope: String(runtimeRecord.scope),
          status: String(runtimeRecord.status),
        }
      : null;
  }

  try {
    const rows = await db.select().from(apiKeys).where(eq(apiKeys.keyHash, keyHash)).limit(1);
    const row = rows[0];
    if (!row) {
      const runtimeRecord = findRuntimeApiKeyByHash(keyHash);
      return runtimeRecord
        ? {
            ...runtimeRecord,
            scope: String(runtimeRecord.scope),
            status: String(runtimeRecord.status),
          }
        : null;
    }

    return {
      id: row.id,
      userId: row.userId,
      label: row.label,
      keyPrefix: row.keyPrefix,
      keyHash: row.keyHash,
      scope: String(row.scope),
      status: String(row.status),
      rpmLimit: row.rpmLimit,
      dailyLimit: row.dailyLimit,
      lastUsedAt: row.lastUsedAt ?? null,
      expiresAt: row.expiresAt ?? null,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    };
  } catch (error) {
    console.warn("[Database] findApiKeyAuthRecordByHash failed, using runtime fallback", error);
    const runtimeRecord = findRuntimeApiKeyByHash(keyHash);
    return runtimeRecord
      ? {
          ...runtimeRecord,
          scope: String(runtimeRecord.scope),
          status: String(runtimeRecord.status),
        }
      : null;
  }
}

export async function touchApiKeyLastUsed(id: number, lastUsedAt = new Date()) {
  const db = await getDb();
  if (!db) {
    return updateRuntimeApiKey(id, { lastUsedAt, updatedAt: lastUsedAt });
  }

  try {
    await db.update(apiKeys).set({ lastUsedAt, updatedAt: lastUsedAt }).where(eq(apiKeys.id, id));
    const rows = await db.select().from(apiKeys).where(eq(apiKeys.id, id)).limit(1);
    const row = rows[0];
    if (!row) {
      return null;
    }

    return {
      id: row.id,
      userId: row.userId,
      label: row.label,
      keyPrefix: row.keyPrefix,
      scope: String(row.scope),
      status: String(row.status),
      rpmLimit: row.rpmLimit,
      dailyLimit: row.dailyLimit,
      lastUsedAt: row.lastUsedAt ?? null,
      expiresAt: row.expiresAt ?? null,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    };
  } catch (error) {
    console.warn("[Database] touchApiKeyLastUsed failed, using runtime fallback", error);
    return updateRuntimeApiKey(id, { lastUsedAt, updatedAt: lastUsedAt });
  }
}

export async function revokeApiKeyRecord(id: number) {
  const revokedAt = new Date();
  const db = await getDb();
  if (!db) {
    return updateRuntimeApiKey(id, { status: "revoked", updatedAt: revokedAt });
  }

  try {
    await db.update(apiKeys).set({ status: "revoked", updatedAt: revokedAt }).where(eq(apiKeys.id, id));
    const rows = await db.select().from(apiKeys).where(eq(apiKeys.id, id)).limit(1);
    const row = rows[0];
    if (!row) {
      return updateRuntimeApiKey(id, { status: "revoked", updatedAt: revokedAt });
    }

    return {
      id: row.id,
      userId: row.userId,
      label: row.label,
      keyPrefix: row.keyPrefix,
      scope: String(row.scope),
      status: String(row.status),
      rpmLimit: row.rpmLimit,
      dailyLimit: row.dailyLimit,
      lastUsedAt: row.lastUsedAt ?? null,
      expiresAt: row.expiresAt ?? null,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    };
  } catch (error) {
    console.warn("[Database] revokeApiKeyRecord failed, using runtime fallback", error);
    return updateRuntimeApiKey(id, { status: "revoked", updatedAt: revokedAt });
  }
}

export async function listPlans(): Promise<PlanRow[]> {
  return withMockFallback<PlanRow[]>(
    "listPlans",
    async db => {
      const rows = await db.select().from(plans).orderBy(plans.priceUsd);
      return rows.map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        tier: String(row.tier),
        billingInterval: String(row.billingInterval),
        currency: row.currency,
        priceUsd: String(row.priceUsd),
        includedRequests: row.includedRequests,
        monthlyApiQuota: row.monthlyApiQuota,
        monthlyBrowserRuns: row.monthlyBrowserRuns,
        maxRpm: row.maxRpm,
        maxConcurrentJobs: row.maxConcurrentJobs,
        vipApiAccess: String(row.vipApiAccess),
        featuresJson: row.featuresJson as unknown,
        isActive: String(row.isActive),
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      MOCK_PLANS.map(row => ({
        id: row.id,
        code: row.code,
        name: row.name,
        tier: String(row.tier),
        billingInterval: String(row.billingInterval),
        currency: row.currency,
        priceUsd: row.priceUsd,
        includedRequests: row.includedRequests,
        monthlyApiQuota: row.monthlyApiQuota,
        monthlyBrowserRuns: row.monthlyBrowserRuns,
        maxRpm: row.maxRpm,
        maxConcurrentJobs: row.maxConcurrentJobs,
        vipApiAccess: String(row.vipApiAccess),
        featuresJson: row.featuresJson,
        isActive: String(row.isActive),
      })),
  );
}

export async function listSubscriptions(): Promise<SubscriptionRow[]> {
  return withMockFallback<SubscriptionRow[]>(
    "listSubscriptions",
    async db => {
      const rows = await db.select().from(subscriptions).orderBy(desc(subscriptions.createdAt)).limit(100);
      return rows.map(row => ({
        id: row.id,
        userId: row.userId,
        planId: row.planId,
        status: row.status,
        provider: row.provider,
        externalRef: row.externalRef ?? null,
        startedAt: row.startedAt ?? null,
        currentPeriodStart: row.currentPeriodStart ?? null,
        currentPeriodEnd: row.currentPeriodEnd ?? null,
        canceledAt: row.canceledAt ?? null,
        metadataJson: row.metadataJson,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      MOCK_SUBSCRIPTIONS.map(row => ({
        id: row.id,
        userId: row.userId,
        planId: row.planId,
        status: row.status,
        provider: row.provider,
        externalRef: row.externalRef ?? null,
        startedAt: new Date(row.startedAt),
        currentPeriodStart: new Date(row.currentPeriodStart),
        currentPeriodEnd: new Date(row.currentPeriodEnd),
        canceledAt: null,
        metadataJson: null,
      })),
  );
}

export async function listPayments(): Promise<PaymentRow[]> {
  return withMockFallback<PaymentRow[]>(
    "listPayments",
    async db => {
      const rows = await db.select().from(payments).orderBy(desc(payments.createdAt)).limit(100);
      return rows.map(row => ({
        id: row.id,
        userId: row.userId,
        subscriptionId: row.subscriptionId ?? null,
        provider: row.provider,
        status: row.status,
        currency: row.currency,
        amount: String(row.amount),
        amountUsd: row.amountUsd ? String(row.amountUsd) : null,
        txRef: row.txRef ?? null,
        invoiceRef: row.invoiceRef ?? null,
        paidAt: row.paidAt ?? null,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
      }));
    },
    () =>
      MOCK_PAYMENTS.map(row => ({
        id: row.id,
        userId: row.userId,
        subscriptionId: row.subscriptionId ?? null,
        provider: row.provider,
        status: row.status,
        currency: row.currency,
        amount: row.amount,
        amountUsd: row.amountUsd ?? null,
        txRef: row.txRef ?? null,
        invoiceRef: row.invoiceRef ?? null,
        paidAt: new Date(row.paidAt),
      })),
  );
}

export async function listMetricSnapshots() {
  return withMockFallback(
    "listMetricSnapshots",
    async db => db.select().from(metricSnapshots).orderBy(desc(metricSnapshots.createdAt)).limit(100),
    () => [],
  );
}

export async function listAuditTrailEntries(): Promise<AuditTrailRow[]> {
  return withMockFallback<AuditTrailRow[]>(
    "listAuditTrailEntries",
    async db => {
      const rows = await db.select().from(auditTrail).orderBy(desc(auditTrail.createdAt)).limit(200);
      const databaseAudit = rows.map(row => ({
        id: row.id,
        actorUserId: row.actorUserId ?? null,
        actorType: String(row.actorType),
        action: row.action,
        resourceType: row.resourceType,
        resourceId: row.resourceId,
        status: String(row.status),
        ipAddress: row.ipAddress ?? null,
        detailsJson: row.detailsJson as unknown,
        createdAt: row.createdAt,
      }));

      const runtimeAudit = listRuntimeAuditTrailEntries().map(row => ({
        id: row.id,
        actorUserId: row.actorUserId ?? null,
        actorType: String(row.actorType),
        action: row.action,
        resourceType: row.resourceType,
        resourceId: row.resourceId,
        status: String(row.status),
        ipAddress: row.ipAddress ?? null,
        detailsJson: row.detailsJson as unknown,
        createdAt: row.createdAt,
      }));

      const merged = [...runtimeAudit, ...databaseAudit].sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
      const seen = new Set<string>();
      return merged.filter(row => {
        const dedupeKey = `${row.action}:${row.resourceType}:${row.resourceId}:${row.createdAt.toISOString()}`;
        if (seen.has(dedupeKey)) {
          return false;
        }
        seen.add(dedupeKey);
        return true;
      }).slice(0, 200);
    },
    () => {
      const runtimeAudit = listRuntimeAuditTrailEntries();
      const mockAudit = listMockAuditTrail().map(row => ({
        id: row.id,
        actorUserId: row.actorUserId ?? null,
        actorType: String(row.actorType),
        action: row.action,
        resourceType: row.resourceType,
        resourceId: row.resourceId,
        status: String(row.status),
        ipAddress: row.ipAddress ?? null,
        detailsJson: row.detailsJson as unknown,
        createdAt: row.createdAt,
      }));

      if (runtimeAudit.length > 0) {
        const seen = new Set(runtimeAudit.map(r => `${r.action}:${r.resourceId}`));
        const uniqueMock = mockAudit.filter(m => !seen.has(`${m.action}:${m.resourceId}`));
        return [...runtimeAudit, ...uniqueMock].sort(
          (a, b) => b.createdAt.getTime() - a.createdAt.getTime(),
        ).slice(0, 200);
      }

      return mockAudit;
    },
  );
}

export async function persistJobRecord(input: Omit<JobRow, "id">): Promise<JobRow> {
  const db = await getDb();
  if (!db) {
    return saveRuntimeJob({
      ...input,
      source: input.source as "dashboard" | "api" | "telegram" | "system" | "testbench",
      requestMode: input.requestMode as "single" | "bulk" | "vip",
      status: input.status as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry",
    });
  }

  try {
    await db.insert(jobs).values({
      publicId: input.publicId,
      userId: input.userId,
      apiKeyId: input.apiKeyId,
      source: input.source as "dashboard" | "api" | "telegram" | "system" | "testbench",
      requestMode: input.requestMode as "single" | "bulk" | "vip",
      status: input.status as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry",
      queueName: input.queueName,
      priority: input.priority,
      targetLabel: input.targetLabel,
      payloadJson: input.payloadJson as Record<string, unknown>,
      resultJson: (input.resultJson ?? null) as Record<string, unknown> | null,
      errorCode: input.errorCode,
      errorMessage: input.errorMessage,
      proxyPolicyId: input.proxyPolicyId,
      workerNodeId: input.workerNodeId,
      attemptCount: input.attemptCount,
      maxAttempts: input.maxAttempts,
      costEstimateUsd: input.costEstimateUsd ?? "0.0000",
      cogsUsd: input.cogsUsd ?? "0.0000",
      createdAt: input.createdAt,
      updatedAt: input.completedAt ?? input.startedAt ?? input.createdAt,
      startedAt: input.startedAt,
      completedAt: input.completedAt,
    });

    const rows = await db.select().from(jobs).where(eq(jobs.publicId, input.publicId)).limit(1);
    const row = rows[0];
    if (!row) {
      throw new Error(`Inserted job ${input.publicId} was not found`);
    }

    return {
      id: row.id,
      publicId: row.publicId,
      userId: row.userId ?? null,
      apiKeyId: row.apiKeyId ?? null,
      source: String(row.source),
      requestMode: String(row.requestMode),
      status: String(row.status),
      queueName: row.queueName,
      priority: row.priority,
      targetLabel: row.targetLabel,
      payloadJson: row.payloadJson as unknown,
      resultJson: row.resultJson as unknown,
      errorCode: row.errorCode ?? null,
      errorMessage: row.errorMessage ?? null,
      proxyPolicyId: row.proxyPolicyId ?? null,
      workerNodeId: row.workerNodeId ?? null,
      attemptCount: row.attemptCount,
      maxAttempts: row.maxAttempts,
      costEstimateUsd: row.costEstimateUsd ? String(row.costEstimateUsd) : null,
      cogsUsd: row.cogsUsd ? String(row.cogsUsd) : null,
      createdAt: row.createdAt,
      startedAt: row.startedAt ?? null,
      completedAt: row.completedAt ?? null,
    };
  } catch (error) {
    console.warn("[Database] persistJobRecord failed, using runtime fallback", error);
    return saveRuntimeJob({
      ...input,
      source: input.source as "dashboard" | "api" | "telegram" | "system" | "testbench",
      requestMode: input.requestMode as "single" | "bulk" | "vip",
      status: input.status as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry",
    });
  }
}

export async function updateJobRecord(
  publicId: string,
  patch: Partial<
    Pick<
      JobRow,
      "status" | "resultJson" | "errorCode" | "errorMessage" | "workerNodeId" | "attemptCount" | "startedAt" | "completedAt"
    >
  >,
): Promise<JobRow | null> {
  const db = await getDb();
  if (!db) {
    const existing = findRuntimeJob(publicId);
    if (!existing) {
      return null;
    }

    return updateRuntimeJob(existing.id, {
      status: (patch.status ?? existing.status) as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry",
      resultJson: patch.resultJson === undefined ? existing.resultJson : patch.resultJson,
      errorCode: patch.errorCode === undefined ? existing.errorCode : patch.errorCode,
      errorMessage: patch.errorMessage === undefined ? existing.errorMessage : patch.errorMessage,
      workerNodeId: patch.workerNodeId === undefined ? existing.workerNodeId : patch.workerNodeId,
      attemptCount: patch.attemptCount === undefined ? existing.attemptCount : patch.attemptCount,
      startedAt: patch.startedAt === undefined ? existing.startedAt : patch.startedAt,
      completedAt: patch.completedAt === undefined ? existing.completedAt : patch.completedAt,
    });
  }

  try {
    const updateValues = {
      ...(patch.status !== undefined ? { status: patch.status as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry" } : {}),
      ...(patch.resultJson !== undefined ? { resultJson: (patch.resultJson ?? null) as Record<string, unknown> | null } : {}),
      ...(patch.errorCode !== undefined ? { errorCode: patch.errorCode } : {}),
      ...(patch.errorMessage !== undefined ? { errorMessage: patch.errorMessage } : {}),
      ...(patch.workerNodeId !== undefined ? { workerNodeId: patch.workerNodeId } : {}),
      ...(patch.attemptCount !== undefined ? { attemptCount: patch.attemptCount } : {}),
      ...(patch.startedAt !== undefined ? { startedAt: patch.startedAt } : {}),
      ...(patch.completedAt !== undefined ? { completedAt: patch.completedAt } : {}),
      updatedAt: patch.completedAt ?? patch.startedAt ?? new Date(),
    };

    await db.update(jobs).set(updateValues).where(eq(jobs.publicId, publicId));
    const rows = await db.select().from(jobs).where(eq(jobs.publicId, publicId)).limit(1);
    const row = rows[0];
    if (!row) {
      return null;
    }

    return {
      id: row.id,
      publicId: row.publicId,
      userId: row.userId ?? null,
      apiKeyId: row.apiKeyId ?? null,
      source: String(row.source),
      requestMode: String(row.requestMode),
      status: String(row.status),
      queueName: row.queueName,
      priority: row.priority,
      targetLabel: row.targetLabel,
      payloadJson: row.payloadJson as unknown,
      resultJson: row.resultJson as unknown,
      errorCode: row.errorCode ?? null,
      errorMessage: row.errorMessage ?? null,
      proxyPolicyId: row.proxyPolicyId ?? null,
      workerNodeId: row.workerNodeId ?? null,
      attemptCount: row.attemptCount,
      maxAttempts: row.maxAttempts,
      costEstimateUsd: row.costEstimateUsd ? String(row.costEstimateUsd) : null,
      cogsUsd: row.cogsUsd ? String(row.cogsUsd) : null,
      createdAt: row.createdAt,
      startedAt: row.startedAt ?? null,
      completedAt: row.completedAt ?? null,
    };
  } catch (error) {
    console.warn("[Database] updateJobRecord failed, using runtime fallback", error);
    const existing = findRuntimeJob(publicId);
    if (!existing) {
      return null;
    }

    return updateRuntimeJob(existing.id, {
      status: (patch.status ?? existing.status) as "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry",
      resultJson: patch.resultJson === undefined ? existing.resultJson : patch.resultJson,
      errorCode: patch.errorCode === undefined ? existing.errorCode : patch.errorCode,
      errorMessage: patch.errorMessage === undefined ? existing.errorMessage : patch.errorMessage,
      workerNodeId: patch.workerNodeId === undefined ? existing.workerNodeId : patch.workerNodeId,
      attemptCount: patch.attemptCount === undefined ? existing.attemptCount : patch.attemptCount,
      startedAt: patch.startedAt === undefined ? existing.startedAt : patch.startedAt,
      completedAt: patch.completedAt === undefined ? existing.completedAt : patch.completedAt,
    });
  }
}

export async function persistJobEvents(
  entries: Array<{
    jobId: number;
    eventType: string;
    severity: "debug" | "info" | "warn" | "error";
    message: string;
    eventJson: unknown;
    createdAt: Date;
  }>,
): Promise<void> {
  if (entries.length === 0) {
    return;
  }

  const db = await getDb();
  if (!db) {
    saveRuntimeJobEvents(entries);
    return;
  }

  try {
    await db.insert(jobEvents).values(
      entries.map(entry => ({
        jobId: entry.jobId,
        eventType: entry.eventType,
        severity: entry.severity,
        message: entry.message,
        eventJson: (entry.eventJson ?? null) as Record<string, unknown> | null,
        createdAt: entry.createdAt,
      })),
    );
  } catch (error) {
    console.warn("[Database] persistJobEvents failed, using runtime fallback", error);
    saveRuntimeJobEvents(entries);
  }
}

export async function persistApiKeyRecord(input: {
  userId: number;
  label: string;
  keyPrefix: string;
  keyHash: string;
  scope: "single" | "bulk" | "vip" | "admin";
  status: "active" | "revoked";
  rpmLimit: number;
  dailyLimit: number;
  lastUsedAt: Date | null;
  expiresAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}): Promise<ApiKeyRow & { keyHash: string }> {
  const db = await getDb();
  if (!db) {
    const runtimeRecord = saveRuntimeApiKey(input);
    return { ...runtimeRecord, keyHash: input.keyHash };
  }

  try {
    await db.insert(apiKeys).values({
      userId: input.userId,
      label: input.label,
      keyPrefix: input.keyPrefix,
      keyHash: input.keyHash,
      scope: input.scope,
      status: input.status,
      rpmLimit: input.rpmLimit,
      dailyLimit: input.dailyLimit,
      lastUsedAt: input.lastUsedAt,
      expiresAt: input.expiresAt,
      createdAt: input.createdAt,
      updatedAt: input.updatedAt,
    });

    const rows = await db.select().from(apiKeys).where(eq(apiKeys.keyPrefix, input.keyPrefix)).limit(1);
    const row = rows[0];
    if (!row) {
      throw new Error(`Inserted api key ${input.keyPrefix} was not found`);
    }

    return {
      id: row.id,
      userId: row.userId,
      label: row.label,
      keyPrefix: row.keyPrefix,
      keyHash: row.keyHash,
      scope: String(row.scope),
      status: String(row.status),
      rpmLimit: row.rpmLimit,
      dailyLimit: row.dailyLimit,
      lastUsedAt: row.lastUsedAt ?? null,
      expiresAt: row.expiresAt ?? null,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    };
  } catch (error) {
    console.warn("[Database] persistApiKeyRecord failed, using runtime fallback", error);
    const runtimeRecord = saveRuntimeApiKey(input);
    return { ...runtimeRecord, keyHash: input.keyHash };
  }
}

export async function persistUsageRecord(input: {
  userId: number | null;
  apiKeyId: number | null;
  jobId: number | null;
  metricType: "request" | "bulk_item" | "browser_run" | "proxy_traffic_gb" | "captcha" | "storage";
  quantity: string;
  unitCostUsd: string;
  totalCostUsd: string;
  periodKey: string;
  metadataJson: unknown;
  createdAt: Date;
}): Promise<void> {
  const db = await getDb();
  if (!db) {
    saveRuntimeUsageRecord(input);
    return;
  }

  try {
    await db.insert(usageRecords).values({
      userId: input.userId,
      apiKeyId: input.apiKeyId,
      jobId: input.jobId,
      metricType: input.metricType,
      quantity: input.quantity,
      unitCostUsd: input.unitCostUsd,
      totalCostUsd: input.totalCostUsd,
      periodKey: input.periodKey,
      metadataJson: (input.metadataJson ?? null) as Record<string, unknown> | null,
      createdAt: input.createdAt,
    });
  } catch (error) {
    console.warn("[Database] persistUsageRecord failed, using runtime fallback", error);
    saveRuntimeUsageRecord(input);
  }
}

export async function persistWorkerRun(input: {
  jobId: number;
  workerNodeId: number;
  runStatus: "started" | "completed" | "failed" | "timeout" | "canceled";
  attemptNumber: number;
  profilePolicy: string | null;
  fingerprintProfile: string | null;
  runtimeMs: number | null;
  detailsJson: unknown;
  createdAt: Date;
  finishedAt: Date | null;
}): Promise<void> {
  const db = await getDb();
  if (!db) {
    saveRuntimeWorkerRun(input);
    return;
  }

  try {
    await db.insert(workerRuns).values({
      jobId: input.jobId,
      workerNodeId: input.workerNodeId,
      runStatus: input.runStatus,
      attemptNumber: input.attemptNumber,
      profilePolicy: input.profilePolicy,
      fingerprintProfile: input.fingerprintProfile,
      runtimeMs: input.runtimeMs,
      detailsJson: (input.detailsJson ?? null) as Record<string, unknown> | null,
      createdAt: input.createdAt,
      finishedAt: input.finishedAt,
    });
  } catch (error) {
    console.warn("[Database] persistWorkerRun failed, using runtime fallback", error);
    saveRuntimeWorkerRun(input);
  }
}

export async function persistProxyLease(input: {
  leaseId: string;
  jobId: number | null;
  workerNodeId: number | null;
  providerId: number;
  policyId: number | null;
  protocol: "http" | "socks5";
  sessionMode: "rotating" | "sticky" | "hard_sticky";
  sessionKey: string | null;
  endpointHost: string;
  endpointPort: number;
  country: string | null;
  status: "active" | "released" | "expired" | "failed";
  bytesSent: number;
  bytesReceived: number;
  estimatedCostUsd: string;
  lastErrorCode: string | null;
  metadataJson: unknown;
  createdAt: Date;
  expiresAt: Date | null;
  releasedAt: Date | null;
}): Promise<void> {
  const db = await getDb();
  if (!db) {
    saveRuntimeProxyLease(input);
    return;
  }

  try {
    await db.insert(proxyLeases).values({
      leaseId: input.leaseId,
      jobId: input.jobId,
      workerNodeId: input.workerNodeId,
      providerId: input.providerId,
      policyId: input.policyId,
      protocol: input.protocol,
      sessionMode: input.sessionMode,
      sessionKey: input.sessionKey,
      endpointHost: input.endpointHost,
      endpointPort: input.endpointPort,
      country: input.country,
      status: input.status,
      bytesSent: input.bytesSent,
      bytesReceived: input.bytesReceived,
      estimatedCostUsd: input.estimatedCostUsd,
      lastErrorCode: input.lastErrorCode,
      metadataJson: (input.metadataJson ?? null) as Record<string, unknown> | null,
      createdAt: input.createdAt,
      expiresAt: input.expiresAt,
      releasedAt: input.releasedAt,
    });
  } catch (error) {
    console.warn("[Database] persistProxyLease failed, using runtime fallback", error);
    saveRuntimeProxyLease(input);
  }
}

function mapBotTextSettingRow(row: typeof systemSettings.$inferSelect): BotTextSettingRow {
  const value = (row.valueJson ?? null) as { title?: unknown; description?: unknown; body?: unknown } | null;

  return {
    id: row.id,
    key: row.settingKey,
    title: typeof value?.title === "string" && value.title.trim().length > 0 ? value.title : row.settingKey,
    description: typeof value?.description === "string" && value.description.trim().length > 0 ? value.description : null,
    body: typeof value?.body === "string" ? value.body : "",
    updatedByUserId: row.updatedByUserId ?? null,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

function mapTelegramRecipientRow(row: typeof telegramEndpoints.$inferSelect): TelegramRecipientRow {
  return {
    id: row.id,
    userId: row.userId ?? null,
    botLabel: row.botLabel,
    chatId: row.chatId ?? "",
    status: String(row.status),
    commandScope: row.commandScope,
    metadataJson: row.metadataJson as unknown,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function listBotTextSettings(): Promise<BotTextSettingRow[]> {
  const fallbackRows = listRuntimeBotTexts().map(row => ({
    id: row.id,
    key: row.key,
    title: row.title,
    description: row.description,
    body: row.body,
    updatedByUserId: row.updatedByUserId,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  }));

  const db = await getDb();
  if (!db) {
    return fallbackRows;
  }

  try {
    const rows = await db
      .select()
      .from(systemSettings)
      .where(eq(systemSettings.category, "bot_text"))
      .orderBy(desc(systemSettings.updatedAt))
      .limit(100);

    return rows.map(mapBotTextSettingRow);
  } catch (error) {
    console.warn("[Database] listBotTextSettings failed, using runtime fallback", error);
    return fallbackRows;
  }
}

export async function upsertBotTextSetting(input: {
  key: string;
  title: string;
  description: string | null;
  body: string;
  updatedByUserId: number | null;
  updatedAt: Date;
}): Promise<BotTextSettingRow> {
  const db = await getDb();
  if (!db) {
    return saveRuntimeBotText({
      key: input.key as "welcome" | "paymentReminder" | "retryNotice" | "supportReply" | "maintenanceBanner",
      title: input.title,
      description: input.description,
      body: input.body,
      updatedByUserId: input.updatedByUserId,
      createdAt: input.updatedAt,
      updatedAt: input.updatedAt,
    });
  }

  try {
    const existingRows = await db
      .select()
      .from(systemSettings)
      .where(and(eq(systemSettings.category, "bot_text"), eq(systemSettings.settingKey, input.key)))
      .limit(1);

    if (existingRows[0]) {
      await db
        .update(systemSettings)
        .set({
          valueJson: {
            title: input.title,
            description: input.description,
            body: input.body,
          },
          updatedByUserId: input.updatedByUserId,
          updatedAt: input.updatedAt,
        })
        .where(eq(systemSettings.id, existingRows[0].id));
    } else {
      await db.insert(systemSettings).values({
        category: "bot_text",
        settingKey: input.key,
        valueJson: {
          title: input.title,
          description: input.description,
          body: input.body,
        },
        updatedByUserId: input.updatedByUserId,
        createdAt: input.updatedAt,
        updatedAt: input.updatedAt,
      });
    }

    const rows = await db
      .select()
      .from(systemSettings)
      .where(and(eq(systemSettings.category, "bot_text"), eq(systemSettings.settingKey, input.key)))
      .limit(1);

    const row = rows[0];
    if (!row) {
      throw new Error(`Bot text ${input.key} was not found after upsert`);
    }

    return mapBotTextSettingRow(row);
  } catch (error) {
    console.warn("[Database] upsertBotTextSetting failed, using runtime fallback", error);
    return saveRuntimeBotText({
      key: input.key as "welcome" | "paymentReminder" | "retryNotice" | "supportReply" | "maintenanceBanner",
      title: input.title,
      description: input.description,
      body: input.body,
      updatedByUserId: input.updatedByUserId,
      createdAt: input.updatedAt,
      updatedAt: input.updatedAt,
    });
  }
}

export async function listTelegramRecipients(options?: { activeOnly?: boolean }): Promise<TelegramRecipientRow[]> {
  const activeOnly = options?.activeOnly ?? false;
  const fallbackRows = listRuntimeTelegramRecipients()
    .filter(row => (activeOnly ? row.status === "active" : true))
    .map(row => ({
      id: row.id,
      userId: row.userId,
      botLabel: row.botLabel,
      chatId: row.chatId,
      status: row.status,
      commandScope: row.commandScope,
      metadataJson: row.metadataJson,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
    }));

  const db = await getDb();
  if (!db) {
    return fallbackRows;
  }

  try {
    const rows = await db
      .select()
      .from(telegramEndpoints)
      .orderBy(desc(telegramEndpoints.updatedAt))
      .limit(500);

    return rows
      .map(mapTelegramRecipientRow)
      .filter(row => row.chatId.trim().length > 0)
      .filter(row => (activeOnly ? row.status === "active" : true));
  } catch (error) {
    console.warn("[Database] listTelegramRecipients failed, using runtime fallback", error);
    return fallbackRows;
  }
}

export async function persistAuditTrailEntry(input: Omit<AuditTrailRow, "id">): Promise<void> {
  const db = await getDb();
  if (!db) {
    saveRuntimeAuditTrailEntry({
      ...input,
      actorType: input.actorType as "user" | "system" | "worker" | "api_key",
      status: input.status as "success" | "failure" | "denied",
    });
    return;
  }

  try {
    await db.insert(auditTrail).values({
      actorUserId: input.actorUserId,
      actorType: input.actorType as "user" | "system" | "worker" | "api_key",
      action: input.action,
      resourceType: input.resourceType,
      resourceId: input.resourceId,
      status: input.status as "success" | "failure" | "denied",
      ipAddress: input.ipAddress,
      detailsJson: (input.detailsJson ?? null) as Record<string, unknown> | null,
      createdAt: input.createdAt,
    });
  } catch (error) {
    console.warn("[Database] persistAuditTrailEntry failed, using runtime fallback", error);
    saveRuntimeAuditTrailEntry({
      ...input,
      actorType: input.actorType as "user" | "system" | "worker" | "api_key",
      status: input.status as "success" | "failure" | "denied",
    });
  }
}
