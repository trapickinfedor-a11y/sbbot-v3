import { z } from "zod";

export const requestModes = ["single", "bulk", "vip"] as const;
export const jobStatuses = ["queued", "running", "succeeded", "failed", "canceled", "waiting_retry"] as const;
export const jobSources = ["dashboard", "api", "telegram", "system", "testbench"] as const;
export const proxyProviderStatuses = ["healthy", "degraded", "disabled"] as const;
export const proxySessionModes = ["rotating", "sticky", "hard_sticky"] as const;
export const workerStatuses = ["healthy", "degraded", "offline", "maintenance"] as const;
export const paymentStatuses = ["pending", "paid", "confirmed", "expired", "failed", "refunded"] as const;
export const planTiers = ["starter", "pro", "vip", "enterprise"] as const;
export const apiKeyScopes = ["single", "bulk", "vip", "admin"] as const;
export const apiKeyStatuses = ["active", "revoked"] as const;
export const botTextKeys = ["welcome", "paymentReminder", "retryNotice", "supportReply", "maintenanceBanner"] as const;
export const broadcastAudienceKinds = ["linked_telegram_users", "manual_chat_ids"] as const;
export const broadcastStatuses = ["draft", "completed", "partial", "failed"] as const;
export const broadcastParseModes = ["plain"] as const;

export type RequestMode = (typeof requestModes)[number];
export type JobStatus = (typeof jobStatuses)[number];
export type JobSource = (typeof jobSources)[number];
export type ProxyProviderStatus = (typeof proxyProviderStatuses)[number];
export type ProxySessionMode = (typeof proxySessionModes)[number];
export type WorkerStatus = (typeof workerStatuses)[number];
export type PaymentStatus = (typeof paymentStatuses)[number];
export type PlanTier = (typeof planTiers)[number];
export type ApiKeyScope = (typeof apiKeyScopes)[number];
export type ApiKeyStatus = (typeof apiKeyStatuses)[number];
export type BotTextKey = (typeof botTextKeys)[number];
export type BroadcastAudienceKind = (typeof broadcastAudienceKinds)[number];
export type BroadcastStatus = (typeof broadcastStatuses)[number];
export type BroadcastParseMode = (typeof broadcastParseModes)[number];

export const jsonRecordSchema = z.record(z.string(), z.unknown());

export const paginationSchema = z.object({
  page: z.number().int().min(1).default(1),
  pageSize: z.number().int().min(1).max(100).default(20),
});

export const dateRangeSchema = z.object({
  from: z.number().int().optional(),
  to: z.number().int().optional(),
});

export const proxyConfigSchema = z.object({
  country: z.string().max(8).optional(),
  state: z.string().max(64).optional(),
  city: z.string().max(128).optional(),
  protocol: z.enum(["http", "socks5"]).default("http"),
  sessionMode: z.enum(proxySessionModes).default("rotating"),
  stickyTtlMinutes: z.number().int().min(1).max(1440).optional(),
  providerHint: z.string().max(64).optional(),
  costCeilingUsd: z.number().min(0).optional(),
  maxTransportRetries: z.number().int().min(0).max(10).default(2),
  maxProviderSwitches: z.number().int().min(0).max(10).default(1),
});

export const createJobSchema = z.object({
  requestMode: z.enum(requestModes),
  targetLabel: z.string().max(191).optional(),
  queueName: z.string().max(64).default("default"),
  priority: z.number().int().min(1).max(1000).default(100),
  payload: jsonRecordSchema,
  proxy: proxyConfigSchema.optional(),
  profilePolicy: z.string().max(128).optional(),
  fingerprintProfile: z.string().max(128).optional(),
  safeTestMode: z.boolean().default(false),
});

export const bulkJobItemSchema = z.object({
  externalId: z.string().max(128).optional(),
  payload: jsonRecordSchema,
});

export const createBulkJobSchema = z.object({
  queueName: z.string().max(64).default("bulk"),
  priority: z.number().int().min(1).max(1000).default(120),
  items: z.array(bulkJobItemSchema).min(1).max(1000),
  proxy: proxyConfigSchema.optional(),
  safeTestMode: z.boolean().default(false),
});

export const createApiKeySchema = z.object({
  label: z.string().min(2).max(128),
  scope: z.enum(apiKeyScopes),
  rpmLimit: z.number().int().min(1).max(10000).default(60),
  dailyLimit: z.number().int().min(1).max(1000000).default(1000),
  expiresAt: z.number().int().optional(),
});

export const listApiKeysSchema = z.object({
  userId: z.number().int().positive().optional(),
}).optional();

export const revokeApiKeySchema = z.object({
  id: z.number().int().positive(),
});

export const createPlanSchema = z.object({
  code: z.string().min(2).max(64),
  name: z.string().min(2).max(128),
  tier: z.enum(planTiers),
  billingInterval: z.enum(["one_time", "monthly", "quarterly", "yearly"]),
  currency: z.string().min(3).max(12).default("USD"),
  priceUsd: z.number().min(0),
  includedRequests: z.number().int().min(0).default(0),
  monthlyApiQuota: z.number().int().min(0).default(0),
  monthlyBrowserRuns: z.number().int().min(0).default(0),
  maxRpm: z.number().int().min(1).default(60),
  maxConcurrentJobs: z.number().int().min(1).default(1),
  vipApiAccess: z.boolean().default(false),
  features: z.array(z.string()).default([]),
});

export const providerConfigSchema = z.object({
  code: z.string().min(2).max(64),
  name: z.string().min(2).max(128),
  protocolSupport: z.string().min(2).max(128),
  sessionSupport: z.string().min(2).max(128),
  costPerGbUsd: z.number().min(0),
  priority: z.number().int().min(1).max(1000).default(100),
  status: z.enum(proxyProviderStatuses).default("healthy"),
  notes: z.string().max(5000).optional(),
  config: jsonRecordSchema.optional(),
});

export const metricFilterSchema = paginationSchema.extend({
  snapshotType: z.enum(["system", "provider", "queue", "billing", "job"]).optional(),
  scopeKey: z.string().max(128).optional(),
  range: dateRangeSchema.optional(),
});

export const jobFilterSchema = paginationSchema.extend({
  status: z.enum(jobStatuses).optional(),
  requestMode: z.enum(requestModes).optional(),
  source: z.enum(jobSources).optional(),
  queueName: z.string().max(64).optional(),
  range: dateRangeSchema.optional(),
});

export const updateBotTextSchema = z.object({
  key: z.enum(botTextKeys),
  body: z.string().min(1).max(20000),
  title: z.string().min(2).max(128).optional(),
  description: z.string().max(500).optional(),
});

export const createBroadcastSchema = z.object({
  title: z.string().min(2).max(128),
  message: z.string().min(1).max(4000),
  audience: z.enum(broadcastAudienceKinds),
  parseMode: z.enum(broadcastParseModes).default("plain"),
  manualChatIds: z.array(z.string().min(2).max(64)).default([]),
  dryRun: z.boolean().default(false),
});

export const safeTestScenarioSchema = z.object({
  code: z.string().min(2).max(64),
  title: z.string().min(2).max(128),
  description: z.string().max(1000),
  expectedOutcome: z.string().max(1000),
  mockPayload: jsonRecordSchema,
});

export type CreateJobInput = z.infer<typeof createJobSchema>;
export type CreateBulkJobInput = z.infer<typeof createBulkJobSchema>;
export type CreateApiKeyInput = z.infer<typeof createApiKeySchema>;
export type ListApiKeysInput = z.infer<typeof listApiKeysSchema>;
export type RevokeApiKeyInput = z.infer<typeof revokeApiKeySchema>;
export type CreatePlanInput = z.infer<typeof createPlanSchema>;
export type ProviderConfigInput = z.infer<typeof providerConfigSchema>;
export type MetricFilterInput = z.infer<typeof metricFilterSchema>;
export type JobFilterInput = z.infer<typeof jobFilterSchema>;
export type SafeTestScenario = z.infer<typeof safeTestScenarioSchema>;
export type UpdateBotTextInput = z.infer<typeof updateBotTextSchema>;
export type CreateBroadcastInput = z.infer<typeof createBroadcastSchema>;

export type ApiEnvelope<T> = {
  ok: boolean;
  requestId: string;
  data?: T;
  meta?: Record<string, unknown>;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
};

export type DashboardMetricCard = {
  key: string;
  title: string;
  value: string;
  delta?: string;
  status?: "neutral" | "good" | "warn" | "bad";
};

export const SAFE_TEST_SCENARIOS: SafeTestScenario[] = [
  {
    code: "single_success_mock",
    title: "Single request success",
    description: "Эмуляция одиночного задания с успешным прохождением очереди, lease и worker run.",
    expectedOutcome: "Job переходит в succeeded, usage и audit trail записываются корректно.",
    mockPayload: {
      target: "mock://catalog/item/42",
      action: "extract",
      expectedTransport: "mock-http",
    },
  },
  {
    code: "provider_fallback_mock",
    title: "Provider fallback",
    description: "Эмуляция деградации основного прокси-провайдера и переключения на резервный.",
    expectedOutcome: "Создаётся warning event, lease отмечает fallback, задание завершается без внешнего вызова.",
    mockPayload: {
      target: "mock://provider/fallback",
      action: "extract",
      simulateProviderFailure: true,
    },
  },
  {
    code: "retry_then_success_mock",
    title: "Retry then success",
    description: "Эмуляция транспортной ошибки на первой попытке и успешного завершения на повторной.",
    expectedOutcome: "Job проходит через waiting_retry, workerRuns фиксируют 2 попытки, финальный статус succeeded.",
    mockPayload: {
      target: "mock://retry/case",
      action: "extract",
      simulateRetryableError: true,
    },
  },
];
