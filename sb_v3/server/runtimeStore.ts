type UsageMetricType = "request" | "bulk_item" | "browser_run" | "proxy_traffic_gb" | "captcha" | "storage";

type AuditStatus = "success" | "failure" | "denied";
type AuditActorType = "user" | "system" | "worker" | "api_key";
type EventSeverity = "debug" | "info" | "warn" | "error";
type JobSource = "dashboard" | "api" | "telegram" | "system" | "testbench";
type RequestMode = "single" | "bulk" | "vip";
type JobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled" | "waiting_retry";
type ProxyLeaseStatus = "active" | "released" | "expired" | "failed";
type WorkerRunStatus = "started" | "completed" | "failed" | "timeout" | "canceled";

export type RuntimeJobRow = {
  id: number;
  publicId: string;
  userId: number | null;
  apiKeyId: number | null;
  source: JobSource;
  requestMode: RequestMode;
  status: JobStatus;
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

export type RuntimeJobEventRow = {
  id: number;
  jobId: number;
  eventType: string;
  severity: EventSeverity;
  message: string;
  eventJson: unknown;
  createdAt: Date;
};

export type RuntimeApiKeyRow = {
  id: number;
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
};

export type RuntimeAuditTrailRow = {
  id: number;
  actorUserId: number | null;
  actorType: AuditActorType;
  action: string;
  resourceType: string;
  resourceId: string;
  status: AuditStatus;
  ipAddress: string | null;
  detailsJson: unknown;
  createdAt: Date;
};

export type RuntimeUsageRecordRow = {
  id: number;
  userId: number | null;
  apiKeyId: number | null;
  jobId: number | null;
  metricType: UsageMetricType;
  quantity: string;
  unitCostUsd: string;
  totalCostUsd: string;
  periodKey: string;
  metadataJson: unknown;
  createdAt: Date;
};

export type RuntimeWorkerRunRow = {
  id: number;
  jobId: number;
  workerNodeId: number;
  runStatus: WorkerRunStatus;
  attemptNumber: number;
  profilePolicy: string | null;
  fingerprintProfile: string | null;
  runtimeMs: number | null;
  detailsJson: unknown;
  createdAt: Date;
  finishedAt: Date | null;
};

export type RuntimeProxyLeaseRow = {
  id: number;
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
  status: ProxyLeaseStatus;
  bytesSent: number;
  bytesReceived: number;
  estimatedCostUsd: string;
  lastErrorCode: string | null;
  metadataJson: unknown;
  createdAt: Date;
  expiresAt: Date | null;
  releasedAt: Date | null;
};

export type RuntimeBotTextRow = {
  id: number;
  key: "welcome" | "paymentReminder" | "retryNotice" | "supportReply" | "maintenanceBanner";
  title: string;
  description: string | null;
  body: string;
  updatedByUserId: number | null;
  createdAt: Date;
  updatedAt: Date;
};

export type RuntimeBroadcastRow = {
  id: number;
  publicId: string;
  title: string;
  message: string;
  audience: "linked_telegram_users" | "manual_chat_ids";
  parseMode: "plain";
  status: "draft" | "completed" | "partial" | "failed";
  dryRun: boolean;
  requestedByUserId: number | null;
  requestedRecipients: number;
  deliveredCount: number;
  failedCount: number;
  recipientsJson: unknown;
  resultsJson: unknown;
  createdAt: Date;
  completedAt: Date | null;
};

export type RuntimeTelegramRecipientRow = {
  id: number;
  userId: number | null;
  botLabel: string;
  chatId: string;
  status: "active" | "disabled";
  commandScope: string;
  metadataJson: unknown;
  createdAt: Date;
  updatedAt: Date;
};

let nextIdCounter = 1;

const runtimeJobs: RuntimeJobRow[] = [];
const runtimeJobEvents: RuntimeJobEventRow[] = [];
const runtimeApiKeys: RuntimeApiKeyRow[] = [];
const runtimeAuditTrail: RuntimeAuditTrailRow[] = [];
const runtimeUsageRecords: RuntimeUsageRecordRow[] = [];
const runtimeWorkerRuns: RuntimeWorkerRunRow[] = [];
const runtimeProxyLeases: RuntimeProxyLeaseRow[] = [];
const runtimeBotTexts: RuntimeBotTextRow[] = [];
const runtimeBroadcasts: RuntimeBroadcastRow[] = [];
const runtimeTelegramRecipients: RuntimeTelegramRecipientRow[] = [];

function nextRuntimeId() {
  return 1_000_000_000 + nextIdCounter++;
}

function cloneDate(value: Date | null) {
  return value ? new Date(value) : null;
}

function toDecimalString(value: number | string, precision = 4) {
  if (typeof value === "string") {
    return value;
  }

  return value.toFixed(precision);
}

function toNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return 0;
}

function cloneJob(job: RuntimeJobRow): RuntimeJobRow {
  return {
    ...job,
    createdAt: new Date(job.createdAt),
    startedAt: cloneDate(job.startedAt),
    completedAt: cloneDate(job.completedAt),
  };
}

function cloneJobEvent(event: RuntimeJobEventRow): RuntimeJobEventRow {
  return {
    ...event,
    createdAt: new Date(event.createdAt),
  };
}

function cloneApiKey(apiKey: RuntimeApiKeyRow): RuntimeApiKeyRow {
  return {
    ...apiKey,
    createdAt: new Date(apiKey.createdAt),
    updatedAt: new Date(apiKey.updatedAt),
    lastUsedAt: cloneDate(apiKey.lastUsedAt),
    expiresAt: cloneDate(apiKey.expiresAt),
  };
}

function cloneAudit(entry: RuntimeAuditTrailRow): RuntimeAuditTrailRow {
  return {
    ...entry,
    createdAt: new Date(entry.createdAt),
  };
}

function cloneUsage(record: RuntimeUsageRecordRow): RuntimeUsageRecordRow {
  return {
    ...record,
    createdAt: new Date(record.createdAt),
  };
}

function cloneWorkerRun(run: RuntimeWorkerRunRow): RuntimeWorkerRunRow {
  return {
    ...run,
    createdAt: new Date(run.createdAt),
    finishedAt: cloneDate(run.finishedAt),
  };
}

function cloneProxyLease(lease: RuntimeProxyLeaseRow): RuntimeProxyLeaseRow {
  return {
    ...lease,
    createdAt: new Date(lease.createdAt),
    expiresAt: cloneDate(lease.expiresAt),
    releasedAt: cloneDate(lease.releasedAt),
  };
}

function cloneBotText(record: RuntimeBotTextRow): RuntimeBotTextRow {
  return {
    ...record,
    createdAt: new Date(record.createdAt),
    updatedAt: new Date(record.updatedAt),
  };
}

function cloneBroadcast(record: RuntimeBroadcastRow): RuntimeBroadcastRow {
  return {
    ...record,
    createdAt: new Date(record.createdAt),
    completedAt: cloneDate(record.completedAt),
  };
}

function cloneTelegramRecipient(record: RuntimeTelegramRecipientRow): RuntimeTelegramRecipientRow {
  return {
    ...record,
    createdAt: new Date(record.createdAt),
    updatedAt: new Date(record.updatedAt),
  };
}

export function getCurrentPeriodKey(date = new Date()) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function resetRuntimeStore() {
  runtimeJobs.length = 0;
  runtimeJobEvents.length = 0;
  runtimeApiKeys.length = 0;
  runtimeAuditTrail.length = 0;
  runtimeUsageRecords.length = 0;
  runtimeWorkerRuns.length = 0;
  runtimeProxyLeases.length = 0;
  runtimeBotTexts.length = 0;
  runtimeBroadcasts.length = 0;
  runtimeTelegramRecipients.length = 0;
  nextIdCounter = 1;
}

export function saveRuntimeJob(input: Omit<RuntimeJobRow, "id"> & { id?: number }) {
  const record: RuntimeJobRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
  };
  runtimeJobs.unshift(record);
  return cloneJob(record);
}

export function listRuntimeJobs() {
  return runtimeJobs
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneJob);
}

export function findRuntimeJob(publicId: string) {
  const record = runtimeJobs.find(job => job.publicId === publicId);
  return record ? cloneJob(record) : null;
}

export function updateRuntimeJob(id: number, patch: Partial<Omit<RuntimeJobRow, "id">>) {
  const index = runtimeJobs.findIndex(job => job.id === id);
  if (index === -1) {
    return null;
  }

  const nextRecord: RuntimeJobRow = {
    ...runtimeJobs[index],
    ...patch,
    id: runtimeJobs[index].id,
    createdAt: patch.createdAt ?? runtimeJobs[index].createdAt,
    startedAt: patch.startedAt === undefined ? runtimeJobs[index].startedAt : patch.startedAt,
    completedAt: patch.completedAt === undefined ? runtimeJobs[index].completedAt : patch.completedAt,
  };

  runtimeJobs[index] = nextRecord;
  return cloneJob(nextRecord);
}

export function saveRuntimeJobEvents(inputs: Array<Omit<RuntimeJobEventRow, "id"> & { id?: number }>) {
  const saved = inputs.map(input => {
    const record: RuntimeJobEventRow = {
      ...input,
      id: input.id ?? nextRuntimeId(),
    };
    runtimeJobEvents.unshift(record);
    return record;
  });

  return saved.map(cloneJobEvent);
}

export function listRuntimeJobEventsByJobId(jobId: number) {
  return runtimeJobEvents
    .filter(event => event.jobId === jobId)
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneJobEvent);
}

export function saveRuntimeApiKey(input: Omit<RuntimeApiKeyRow, "id"> & { id?: number }) {
  const record: RuntimeApiKeyRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
  };
  runtimeApiKeys.unshift(record);
  return cloneApiKey(record);
}

export function listRuntimeApiKeys(userId?: number) {
  return runtimeApiKeys
    .filter(apiKey => (userId ? apiKey.userId === userId : true))
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneApiKey);
}

export function findRuntimeApiKeyByHash(keyHash: string) {
  const record = runtimeApiKeys.find(apiKey => apiKey.keyHash === keyHash);
  return record ? cloneApiKey(record) : null;
}

export function updateRuntimeApiKey(
  id: number,
  patch: Partial<Omit<RuntimeApiKeyRow, "id" | "keyHash" | "keyPrefix" | "userId">>,
) {
  const index = runtimeApiKeys.findIndex(apiKey => apiKey.id === id);
  if (index === -1) {
    return null;
  }

  const nextRecord: RuntimeApiKeyRow = {
    ...runtimeApiKeys[index],
    ...patch,
    id: runtimeApiKeys[index].id,
    userId: runtimeApiKeys[index].userId,
    keyPrefix: runtimeApiKeys[index].keyPrefix,
    keyHash: runtimeApiKeys[index].keyHash,
    createdAt: patch.createdAt ?? runtimeApiKeys[index].createdAt,
    updatedAt: patch.updatedAt ?? runtimeApiKeys[index].updatedAt,
    lastUsedAt: patch.lastUsedAt === undefined ? runtimeApiKeys[index].lastUsedAt : patch.lastUsedAt,
    expiresAt: patch.expiresAt === undefined ? runtimeApiKeys[index].expiresAt : patch.expiresAt,
  };

  runtimeApiKeys[index] = nextRecord;
  return cloneApiKey(nextRecord);
}

export function saveRuntimeAuditTrailEntry(input: Omit<RuntimeAuditTrailRow, "id"> & { id?: number }) {
  const record: RuntimeAuditTrailRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
  };
  runtimeAuditTrail.unshift(record);
  return cloneAudit(record);
}

export function listRuntimeAuditTrailEntries() {
  return runtimeAuditTrail
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneAudit);
}

export function saveRuntimeUsageRecord(input: Omit<RuntimeUsageRecordRow, "id"> & { id?: number }) {
  const record: RuntimeUsageRecordRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
    quantity: toDecimalString(input.quantity),
    unitCostUsd: toDecimalString(input.unitCostUsd),
    totalCostUsd: toDecimalString(input.totalCostUsd),
  };
  runtimeUsageRecords.unshift(record);
  return cloneUsage(record);
}

export function listRuntimeUsageRecords() {
  return runtimeUsageRecords
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneUsage);
}

export function saveRuntimeWorkerRun(input: Omit<RuntimeWorkerRunRow, "id"> & { id?: number }) {
  const record: RuntimeWorkerRunRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
  };
  runtimeWorkerRuns.unshift(record);
  return cloneWorkerRun(record);
}

export function listRuntimeWorkerRuns() {
  return runtimeWorkerRuns
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneWorkerRun);
}

export function saveRuntimeProxyLease(input: Omit<RuntimeProxyLeaseRow, "id"> & { id?: number }) {
  const record: RuntimeProxyLeaseRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
    estimatedCostUsd: toDecimalString(input.estimatedCostUsd),
  };
  runtimeProxyLeases.unshift(record);
  return cloneProxyLease(record);
}

export function listRuntimeProxyLeases() {
  return runtimeProxyLeases
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneProxyLease);
}

export function updateRuntimeProxyLease(leaseId: string, patch: Partial<Omit<RuntimeProxyLeaseRow, "id" | "leaseId">>) {
  const index = runtimeProxyLeases.findIndex(lease => lease.leaseId === leaseId);
  if (index === -1) {
    return null;
  }

  const nextRecord: RuntimeProxyLeaseRow = {
    ...runtimeProxyLeases[index],
    ...patch,
    id: runtimeProxyLeases[index].id,
    leaseId: runtimeProxyLeases[index].leaseId,
    createdAt: patch.createdAt ?? runtimeProxyLeases[index].createdAt,
    expiresAt: patch.expiresAt === undefined ? runtimeProxyLeases[index].expiresAt : patch.expiresAt,
    releasedAt: patch.releasedAt === undefined ? runtimeProxyLeases[index].releasedAt : patch.releasedAt,
  };

  runtimeProxyLeases[index] = nextRecord;
  return cloneProxyLease(nextRecord);
}

export function getRuntimeUsageSummary() {
  if (runtimeUsageRecords.length === 0) {
    return null;
  }

  const newest = runtimeUsageRecords[0];
  const currentPeriod = newest?.periodKey ?? getCurrentPeriodKey();
  const inPeriod = runtimeUsageRecords.filter(record => record.periodKey === currentPeriod);

  const requests = inPeriod
    .filter(record => record.metricType === "request" || record.metricType === "bulk_item")
    .reduce((sum, record) => sum + toNumber(record.quantity), 0);

  const browserRuns = inPeriod
    .filter(record => record.metricType === "browser_run")
    .reduce((sum, record) => sum + toNumber(record.quantity), 0);

  const proxyTrafficGb = inPeriod
    .filter(record => record.metricType === "proxy_traffic_gb")
    .reduce((sum, record) => sum + toNumber(record.quantity), 0);

  const cogsUsd = inPeriod.reduce((sum, record) => sum + toNumber(record.totalCostUsd), 0);
  const revenueUsd = inPeriod.reduce((sum, record) => {
    const metadata = record.metadataJson as { revenueUsd?: unknown } | null;
    return sum + toNumber(metadata?.revenueUsd);
  }, 0);
  const marginUsd = revenueUsd - cogsUsd;

  return {
    currentPeriod,
    requests: Number(requests.toFixed(4)),
    browserRuns: Number(browserRuns.toFixed(4)),
    proxyTrafficGb: Number(proxyTrafficGb.toFixed(4)),
    cogsUsd: Number(cogsUsd.toFixed(4)),
    revenueUsd: Number(revenueUsd.toFixed(4)),
    marginUsd: Number(marginUsd.toFixed(4)),
  };
}

export function listRuntimeBotTexts() {
  return runtimeBotTexts
    .slice()
    .sort((a, b) => a.key.localeCompare(b.key))
    .map(cloneBotText);
}

export function saveRuntimeBotText(input: Omit<RuntimeBotTextRow, "id"> & { id?: number }) {
  const existingIndex = runtimeBotTexts.findIndex(record => record.key === input.key);
  const record: RuntimeBotTextRow = {
    ...input,
    id: existingIndex >= 0 ? runtimeBotTexts[existingIndex].id : (input.id ?? nextRuntimeId()),
    createdAt: existingIndex >= 0 ? runtimeBotTexts[existingIndex].createdAt : input.createdAt,
  };

  if (existingIndex >= 0) {
    runtimeBotTexts[existingIndex] = record;
  } else {
    runtimeBotTexts.unshift(record);
  }

  return cloneBotText(record);
}

export function listRuntimeBroadcasts() {
  return runtimeBroadcasts
    .slice()
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
    .map(cloneBroadcast);
}

export function saveRuntimeBroadcast(input: Omit<RuntimeBroadcastRow, "id"> & { id?: number }) {
  const record: RuntimeBroadcastRow = {
    ...input,
    id: input.id ?? nextRuntimeId(),
  };
  runtimeBroadcasts.unshift(record);
  return cloneBroadcast(record);
}

export function listRuntimeTelegramRecipients() {
  return runtimeTelegramRecipients
    .slice()
    .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
    .map(cloneTelegramRecipient);
}

export function saveRuntimeTelegramRecipient(input: Omit<RuntimeTelegramRecipientRow, "id"> & { id?: number }) {
  const existingIndex = runtimeTelegramRecipients.findIndex(record => record.chatId === input.chatId);
  const record: RuntimeTelegramRecipientRow = {
    ...input,
    id: existingIndex >= 0 ? runtimeTelegramRecipients[existingIndex].id : (input.id ?? nextRuntimeId()),
    createdAt: existingIndex >= 0 ? runtimeTelegramRecipients[existingIndex].createdAt : input.createdAt,
  };

  if (existingIndex >= 0) {
    runtimeTelegramRecipients[existingIndex] = record;
  } else {
    runtimeTelegramRecipients.unshift(record);
  }

  return cloneTelegramRecipient(record);
}
