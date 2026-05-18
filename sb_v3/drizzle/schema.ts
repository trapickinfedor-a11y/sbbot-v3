import {
  bigint,
  decimal,
  index,
  int,
  json,
  mysqlEnum,
  mysqlTable,
  text,
  timestamp,
  uniqueIndex,
  varchar,
} from "drizzle-orm/mysql-core";

const createdAt = timestamp("createdAt").defaultNow().notNull();
const updatedAt = timestamp("updatedAt").defaultNow().onUpdateNow().notNull();

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  telegramChatId: varchar("telegramChatId", { length: 64 }),
  status: mysqlEnum("status", ["active", "suspended", "invited"]).default("active").notNull(),
  createdAt,
  updatedAt,
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export const plans = mysqlTable("plans", {
  id: int("id").autoincrement().primaryKey(),
  code: varchar("code", { length: 64 }).notNull().unique(),
  name: varchar("name", { length: 128 }).notNull(),
  tier: mysqlEnum("tier", ["starter", "pro", "vip", "enterprise"]).notNull(),
  billingInterval: mysqlEnum("billingInterval", ["one_time", "monthly", "quarterly", "yearly"]).notNull(),
  currency: varchar("currency", { length: 12 }).default("USD").notNull(),
  priceUsd: decimal("priceUsd", { precision: 10, scale: 2 }).notNull(),
  includedRequests: int("includedRequests").default(0).notNull(),
  monthlyApiQuota: int("monthlyApiQuota").default(0).notNull(),
  monthlyBrowserRuns: int("monthlyBrowserRuns").default(0).notNull(),
  maxRpm: int("maxRpm").default(60).notNull(),
  maxConcurrentJobs: int("maxConcurrentJobs").default(1).notNull(),
  vipApiAccess: mysqlEnum("vipApiAccess", ["disabled", "enabled"]).default("disabled").notNull(),
  featuresJson: json("featuresJson"),
  isActive: mysqlEnum("isActive", ["yes", "no"]).default("yes").notNull(),
  createdAt,
  updatedAt,
});

export const subscriptions = mysqlTable(
  "subscriptions",
  {
    id: int("id").autoincrement().primaryKey(),
    userId: int("userId").notNull(),
    planId: int("planId").notNull(),
    status: mysqlEnum("status", ["pending", "active", "past_due", "canceled", "expired"]).notNull(),
    provider: mysqlEnum("provider", ["manual", "btcpay", "cryptobot"]).notNull(),
    externalRef: varchar("externalRef", { length: 191 }),
    startedAt: timestamp("startedAt"),
    currentPeriodStart: timestamp("currentPeriodStart"),
    currentPeriodEnd: timestamp("currentPeriodEnd"),
    canceledAt: timestamp("canceledAt"),
    metadataJson: json("metadataJson"),
    createdAt,
    updatedAt,
  },
  table => ({
    subscriptionUserIdx: index("subscriptionUserIdx").on(table.userId),
    subscriptionPlanIdx: index("subscriptionPlanIdx").on(table.planId),
  }),
);

export const apiKeys = mysqlTable(
  "apiKeys",
  {
    id: int("id").autoincrement().primaryKey(),
    userId: int("userId").notNull(),
    label: varchar("label", { length: 128 }).notNull(),
    keyPrefix: varchar("keyPrefix", { length: 24 }).notNull(),
    keyHash: varchar("keyHash", { length: 255 }).notNull(),
    scope: mysqlEnum("scope", ["single", "bulk", "vip", "admin"]).notNull(),
    status: mysqlEnum("status", ["active", "revoked"]).default("active").notNull(),
    rpmLimit: int("rpmLimit").default(60).notNull(),
    dailyLimit: int("dailyLimit").default(1000).notNull(),
    lastUsedAt: timestamp("lastUsedAt"),
    expiresAt: timestamp("expiresAt"),
    createdAt,
    updatedAt,
  },
  table => ({
    apiKeyUserIdx: index("apiKeyUserIdx").on(table.userId),
    apiKeyPrefixUnique: uniqueIndex("apiKeyPrefixUnique").on(table.keyPrefix),
  }),
);

export const proxyProviders = mysqlTable("proxyProviders", {
  id: int("id").autoincrement().primaryKey(),
  code: varchar("code", { length: 64 }).notNull().unique(),
  name: varchar("name", { length: 128 }).notNull(),
  protocolSupport: varchar("protocolSupport", { length: 128 }).notNull(),
  sessionSupport: varchar("sessionSupport", { length: 128 }).notNull(),
  costPerGbUsd: decimal("costPerGbUsd", { precision: 10, scale: 4 }).notNull(),
  priority: int("priority").default(100).notNull(),
  status: mysqlEnum("status", ["healthy", "degraded", "disabled"]).default("healthy").notNull(),
  configJson: json("configJson"),
  notes: text("notes"),
  createdAt,
  updatedAt,
});

export const proxyPolicies = mysqlTable(
  "proxyPolicies",
  {
    id: int("id").autoincrement().primaryKey(),
    code: varchar("code", { length: 64 }).notNull().unique(),
    name: varchar("name", { length: 128 }).notNull(),
    protocol: mysqlEnum("protocol", ["http", "socks5"]).notNull(),
    sessionMode: mysqlEnum("sessionMode", ["rotating", "sticky", "hard_sticky"]).notNull(),
    stickyTtlMinutes: int("stickyTtlMinutes"),
    country: varchar("country", { length: 8 }),
    state: varchar("state", { length: 64 }),
    city: varchar("city", { length: 128 }),
    maxTransportRetries: int("maxTransportRetries").default(2).notNull(),
    maxProviderSwitches: int("maxProviderSwitches").default(1).notNull(),
    costCeilingUsd: decimal("costCeilingUsd", { precision: 10, scale: 4 }),
    policyJson: json("policyJson"),
    isDefault: mysqlEnum("isDefault", ["yes", "no"]).default("no").notNull(),
    createdAt,
    updatedAt,
  },
  table => ({
    proxyPolicyCodeIdx: index("proxyPolicyCodeIdx").on(table.code),
  }),
);

export const jobs = mysqlTable(
  "jobs",
  {
    id: int("id").autoincrement().primaryKey(),
    publicId: varchar("publicId", { length: 64 }).notNull().unique(),
    userId: int("userId"),
    apiKeyId: int("apiKeyId"),
    source: mysqlEnum("source", ["dashboard", "api", "telegram", "system", "testbench"]).notNull(),
    requestMode: mysqlEnum("requestMode", ["single", "bulk", "vip"]).notNull(),
    status: mysqlEnum("status", ["queued", "running", "succeeded", "failed", "canceled", "waiting_retry"]).notNull(),
    queueName: varchar("queueName", { length: 64 }).default("default").notNull(),
    priority: int("priority").default(100).notNull(),
    targetLabel: varchar("targetLabel", { length: 191 }),
    payloadJson: json("payloadJson").notNull(),
    resultJson: json("resultJson"),
    errorCode: varchar("errorCode", { length: 64 }),
    errorMessage: text("errorMessage"),
    proxyPolicyId: int("proxyPolicyId"),
    workerNodeId: int("workerNodeId"),
    attemptCount: int("attemptCount").default(0).notNull(),
    maxAttempts: int("maxAttempts").default(3).notNull(),
    costEstimateUsd: decimal("costEstimateUsd", { precision: 10, scale: 4 }).default("0.0000").notNull(),
    cogsUsd: decimal("cogsUsd", { precision: 10, scale: 4 }).default("0.0000").notNull(),
    createdAt,
    updatedAt,
    startedAt: timestamp("startedAt"),
    completedAt: timestamp("completedAt"),
  },
  table => ({
    jobsUserIdx: index("jobsUserIdx").on(table.userId),
    jobsStatusIdx: index("jobsStatusIdx").on(table.status),
    jobsQueueIdx: index("jobsQueueIdx").on(table.queueName, table.status),
  }),
);

export const jobEvents = mysqlTable(
  "jobEvents",
  {
    id: int("id").autoincrement().primaryKey(),
    jobId: int("jobId").notNull(),
    eventType: varchar("eventType", { length: 64 }).notNull(),
    severity: mysqlEnum("severity", ["debug", "info", "warn", "error"]).default("info").notNull(),
    message: text("message").notNull(),
    eventJson: json("eventJson"),
    createdAt,
  },
  table => ({
    jobEventsJobIdx: index("jobEventsJobIdx").on(table.jobId, table.createdAt),
  }),
);

export const workerNodes = mysqlTable("workerNodes", {
  id: int("id").autoincrement().primaryKey(),
  code: varchar("code", { length: 64 }).notNull().unique(),
  name: varchar("name", { length: 128 }).notNull(),
  role: mysqlEnum("role", ["browser", "api", "scheduler", "hybrid"]).default("browser").notNull(),
  status: mysqlEnum("status", ["healthy", "degraded", "offline", "maintenance"]).default("healthy").notNull(),
  concurrencyLimit: int("concurrencyLimit").default(4).notNull(),
  activeJobs: int("activeJobs").default(0).notNull(),
  version: varchar("version", { length: 64 }),
  hostLabel: varchar("hostLabel", { length: 128 }),
  capabilitiesJson: json("capabilitiesJson"),
  lastHeartbeatAt: timestamp("lastHeartbeatAt"),
  createdAt,
  updatedAt,
});

export const workerRuns = mysqlTable(
  "workerRuns",
  {
    id: int("id").autoincrement().primaryKey(),
    jobId: int("jobId").notNull(),
    workerNodeId: int("workerNodeId").notNull(),
    runStatus: mysqlEnum("runStatus", ["started", "completed", "failed", "timeout", "canceled"]).notNull(),
    attemptNumber: int("attemptNumber").default(1).notNull(),
    profilePolicy: varchar("profilePolicy", { length: 128 }),
    fingerprintProfile: varchar("fingerprintProfile", { length: 128 }),
    runtimeMs: int("runtimeMs"),
    detailsJson: json("detailsJson"),
    createdAt,
    finishedAt: timestamp("finishedAt"),
  },
  table => ({
    workerRunsJobIdx: index("workerRunsJobIdx").on(table.jobId),
    workerRunsWorkerIdx: index("workerRunsWorkerIdx").on(table.workerNodeId),
  }),
);

export const proxyLeases = mysqlTable(
  "proxyLeases",
  {
    id: int("id").autoincrement().primaryKey(),
    leaseId: varchar("leaseId", { length: 64 }).notNull().unique(),
    jobId: int("jobId"),
    workerNodeId: int("workerNodeId"),
    providerId: int("providerId").notNull(),
    policyId: int("policyId"),
    protocol: mysqlEnum("protocol", ["http", "socks5"]).notNull(),
    sessionMode: mysqlEnum("sessionMode", ["rotating", "sticky", "hard_sticky"]).notNull(),
    sessionKey: varchar("sessionKey", { length: 128 }),
    endpointHost: varchar("endpointHost", { length: 255 }).notNull(),
    endpointPort: int("endpointPort").notNull(),
    country: varchar("country", { length: 8 }),
    status: mysqlEnum("status", ["active", "released", "expired", "failed"]).default("active").notNull(),
    bytesSent: bigint("bytesSent", { mode: "number" }).default(0).notNull(),
    bytesReceived: bigint("bytesReceived", { mode: "number" }).default(0).notNull(),
    estimatedCostUsd: decimal("estimatedCostUsd", { precision: 10, scale: 4 }).default("0.0000").notNull(),
    lastErrorCode: varchar("lastErrorCode", { length: 64 }),
    metadataJson: json("metadataJson"),
    createdAt,
    expiresAt: timestamp("expiresAt"),
    releasedAt: timestamp("releasedAt"),
  },
  table => ({
    proxyLeaseJobIdx: index("proxyLeaseJobIdx").on(table.jobId),
    proxyLeaseProviderIdx: index("proxyLeaseProviderIdx").on(table.providerId, table.status),
  }),
);

export const payments = mysqlTable(
  "payments",
  {
    id: int("id").autoincrement().primaryKey(),
    userId: int("userId").notNull(),
    subscriptionId: int("subscriptionId"),
    provider: mysqlEnum("provider", ["btcpay", "cryptobot", "manual"]).notNull(),
    status: mysqlEnum("status", ["pending", "paid", "confirmed", "expired", "failed", "refunded"]).notNull(),
    currency: varchar("currency", { length: 16 }).notNull(),
    amount: decimal("amount", { precision: 12, scale: 2 }).notNull(),
    amountUsd: decimal("amountUsd", { precision: 12, scale: 2 }),
    txRef: varchar("txRef", { length: 191 }),
    invoiceRef: varchar("invoiceRef", { length: 191 }),
    metadataJson: json("metadataJson"),
    createdAt,
    updatedAt,
    paidAt: timestamp("paidAt"),
  },
  table => ({
    paymentsUserIdx: index("paymentsUserIdx").on(table.userId),
    paymentsStatusIdx: index("paymentsStatusIdx").on(table.status),
  }),
);

export const usageRecords = mysqlTable(
  "usageRecords",
  {
    id: int("id").autoincrement().primaryKey(),
    userId: int("userId"),
    apiKeyId: int("apiKeyId"),
    jobId: int("jobId"),
    metricType: mysqlEnum("metricType", ["request", "bulk_item", "browser_run", "proxy_traffic_gb", "captcha", "storage"]).notNull(),
    quantity: decimal("quantity", { precision: 14, scale: 4 }).notNull(),
    unitCostUsd: decimal("unitCostUsd", { precision: 10, scale: 4 }).default("0.0000").notNull(),
    totalCostUsd: decimal("totalCostUsd", { precision: 12, scale: 4 }).default("0.0000").notNull(),
    periodKey: varchar("periodKey", { length: 32 }).notNull(),
    metadataJson: json("metadataJson"),
    createdAt,
  },
  table => ({
    usageUserIdx: index("usageUserIdx").on(table.userId, table.periodKey),
    usageApiKeyIdx: index("usageApiKeyIdx").on(table.apiKeyId, table.periodKey),
  }),
);

export const metricSnapshots = mysqlTable(
  "metricSnapshots",
  {
    id: int("id").autoincrement().primaryKey(),
    snapshotType: mysqlEnum("snapshotType", ["system", "provider", "queue", "billing", "job"]).notNull(),
    scopeKey: varchar("scopeKey", { length: 128 }).notNull(),
    successRate: decimal("successRate", { precision: 7, scale: 4 }),
    errorRate: decimal("errorRate", { precision: 7, scale: 4 }),
    queueDepth: int("queueDepth"),
    activeWorkers: int("activeWorkers"),
    cogsUsd: decimal("cogsUsd", { precision: 12, scale: 4 }),
    revenueUsd: decimal("revenueUsd", { precision: 12, scale: 4 }),
    payloadJson: json("payloadJson"),
    createdAt,
  },
  table => ({
    metricTypeScopeIdx: index("metricTypeScopeIdx").on(table.snapshotType, table.scopeKey, table.createdAt),
  }),
);

export const telegramEndpoints = mysqlTable("telegramEndpoints", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  botLabel: varchar("botLabel", { length: 128 }).notNull(),
  chatId: varchar("chatId", { length: 64 }),
  status: mysqlEnum("status", ["active", "disabled"]).default("active").notNull(),
  commandScope: varchar("commandScope", { length: 128 }).default("owner_alerts").notNull(),
  metadataJson: json("metadataJson"),
  createdAt,
  updatedAt,
});

export const auditTrail = mysqlTable(
  "auditTrail",
  {
    id: int("id").autoincrement().primaryKey(),
    actorUserId: int("actorUserId"),
    actorType: mysqlEnum("actorType", ["user", "system", "worker", "api_key"]).notNull(),
    action: varchar("action", { length: 128 }).notNull(),
    resourceType: varchar("resourceType", { length: 64 }).notNull(),
    resourceId: varchar("resourceId", { length: 128 }).notNull(),
    status: mysqlEnum("status", ["success", "failure", "denied"]).notNull(),
    ipAddress: varchar("ipAddress", { length: 64 }),
    detailsJson: json("detailsJson"),
    createdAt,
  },
  table => ({
    auditResourceIdx: index("auditResourceIdx").on(table.resourceType, table.resourceId, table.createdAt),
    auditActorIdx: index("auditActorIdx").on(table.actorUserId, table.createdAt),
  }),
);

export const systemSettings = mysqlTable("systemSettings", {
  id: int("id").autoincrement().primaryKey(),
  category: varchar("category", { length: 64 }).notNull(),
  settingKey: varchar("settingKey", { length: 128 }).notNull(),
  valueJson: json("valueJson"),
  updatedByUserId: int("updatedByUserId"),
  createdAt,
  updatedAt,
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type Plan = typeof plans.$inferSelect;
export type Subscription = typeof subscriptions.$inferSelect;
export type ApiKey = typeof apiKeys.$inferSelect;
export type Job = typeof jobs.$inferSelect;
export type JobEvent = typeof jobEvents.$inferSelect;
export type WorkerNode = typeof workerNodes.$inferSelect;
export type WorkerRun = typeof workerRuns.$inferSelect;
export type ProxyProvider = typeof proxyProviders.$inferSelect;
export type ProxyPolicy = typeof proxyPolicies.$inferSelect;
export type ProxyLease = typeof proxyLeases.$inferSelect;
export type Payment = typeof payments.$inferSelect;
export type UsageRecord = typeof usageRecords.$inferSelect;
export type MetricSnapshot = typeof metricSnapshots.$inferSelect;
export type TelegramEndpoint = typeof telegramEndpoints.$inferSelect;
export type AuditTrailEntry = typeof auditTrail.$inferSelect;
export type SystemSetting = typeof systemSettings.$inferSelect;
