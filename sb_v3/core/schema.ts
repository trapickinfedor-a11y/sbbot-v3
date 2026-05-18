import {
  int,
  json,
  mysqlEnum,
  mysqlTable,
  text,
  timestamp,
  varchar,
} from "drizzle-orm/mysql-core";

export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  subscriptionTier: mysqlEnum("subscriptionTier", ["regular", "vip"]).default("regular").notNull(),
  preferredLanguage: mysqlEnum("preferredLanguage", ["en", "ru", "es", "cn"]).default("en").notNull(),
  balanceCents: int("balanceCents").default(0).notNull(),
  monthlyApiQuota: int("monthlyApiQuota").default(0).notNull(),
  apiCallsUsed: int("apiCallsUsed").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export const subscriptionPlans = mysqlTable("subscriptionPlans", {
  id: int("id").autoincrement().primaryKey(),
  code: varchar("code", { length: 32 }).notNull().unique(),
  name: varchar("name", { length: 120 }).notNull(),
  billingPeriod: mysqlEnum("billingPeriod", ["monthly", "yearly"]).default("monthly").notNull(),
  audience: mysqlEnum("audience", ["regular", "vip"]).notNull(),
  priceCents: int("priceCents").notNull(),
  includedCreditsCents: int("includedCreditsCents").default(0).notNull(),
  includedApiQuota: int("includedApiQuota").default(0).notNull(),
  rateLimitPerMinute: int("rateLimitPerMinute").default(0).notNull(),
  featuresJson: json("featuresJson"),
  isActive: int("isActive").default(1).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const subscriptions = mysqlTable("subscriptions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  planId: int("planId").notNull(),
  status: mysqlEnum("status", ["trial", "active", "past_due", "canceled", "expired"]).default("active").notNull(),
  startedAt: timestamp("startedAt").defaultNow().notNull(),
  renewsAt: timestamp("renewsAt"),
  canceledAt: timestamp("canceledAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const transactions = mysqlTable("transactions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  kind: mysqlEnum("kind", ["top_up", "subscription", "search_charge", "api_charge", "refund", "adjustment"]).notNull(),
  status: mysqlEnum("status", ["pending", "completed", "failed", "canceled"]).default("pending").notNull(),
  paymentMethod: mysqlEnum("paymentMethod", ["card", "crypto", "bank_transfer", "manual", "balance"]).default("card").notNull(),
  provider: varchar("provider", { length: 64 }),
  amountCents: int("amountCents").notNull(),
  balanceBeforeCents: int("balanceBeforeCents").default(0).notNull(),
  balanceAfterCents: int("balanceAfterCents").default(0).notNull(),
  referenceId: varchar("referenceId", { length: 120 }),
  metadataJson: json("metadataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  completedAt: timestamp("completedAt"),
});

export const apiKeys = mysqlTable("apiKeys", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  name: varchar("name", { length: 120 }).notNull(),
  keyHash: varchar("keyHash", { length: 255 }).notNull(),
  keyPreview: varchar("keyPreview", { length: 24 }).notNull(),
  status: mysqlEnum("status", ["active", "revoked"]).default("active").notNull(),
  lastUsedAt: timestamp("lastUsedAt"),
  expiresAt: timestamp("expiresAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const searchRequests = mysqlTable("searchRequests", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  type: mysqlEnum("type", ["phone", "address", "ssn", "driver_license", "credit_report", "background_check"]).notNull(),
  status: mysqlEnum("status", ["queued", "processing", "completed", "failed"]).default("queued").notNull(),
  inputQuery: text("inputQuery").notNull(),
  locale: mysqlEnum("locale", ["en", "ru", "es", "cn"]).default("en").notNull(),
  selectedCandidateId: int("selectedCandidateId"),
  candidateCount: int("candidateCount").default(0).notNull(),
  totalChargeCents: int("totalChargeCents").default(0).notNull(),
  sourceLabel: varchar("sourceLabel", { length: 120 }),
  ipAddress: varchar("ipAddress", { length: 64 }),
  metadataJson: json("metadataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  completedAt: timestamp("completedAt"),
});

export const searchCandidates = mysqlTable("searchCandidates", {
  id: int("id").autoincrement().primaryKey(),
  searchRequestId: int("searchRequestId").notNull(),
  candidateOrder: int("candidateOrder").default(0).notNull(),
  fullName: varchar("fullName", { length: 180 }).notNull(),
  ageBand: varchar("ageBand", { length: 64 }),
  primaryPhone: varchar("primaryPhone", { length: 32 }),
  primaryAddress: varchar("primaryAddress", { length: 255 }),
  summary: text("summary"),
  confidenceScore: int("confidenceScore").default(0).notNull(),
  dataJson: json("dataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const auditLogs = mysqlTable("auditLogs", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  actionType: varchar("actionType", { length: 120 }).notNull(),
  entityType: varchar("entityType", { length: 120 }).notNull(),
  entityId: varchar("entityId", { length: 120 }),
  ipAddress: varchar("ipAddress", { length: 64 }),
  userAgent: text("userAgent"),
  locale: mysqlEnum("locale", ["en", "ru", "es", "cn"]).default("en").notNull(),
  metadataJson: json("metadataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const notifications = mysqlTable("notifications", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  kind: mysqlEnum("kind", ["low_balance", "subscription_renewal", "search_complete", "api_quota_warning", "system"]).notNull(),
  channel: mysqlEnum("channel", ["in_app", "email", "webhook"]).default("in_app").notNull(),
  status: mysqlEnum("status", ["unread", "read", "sent", "failed"]).default("unread").notNull(),
  title: varchar("title", { length: 180 }).notNull(),
  body: text("body").notNull(),
  metadataJson: json("metadataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  readAt: timestamp("readAt"),
});

export const apiUsageMetrics = mysqlTable("apiUsageMetrics", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  apiKeyId: int("apiKeyId"),
  route: varchar("route", { length: 180 }).notNull(),
  method: mysqlEnum("method", ["GET", "POST", "PUT", "DELETE"]).default("GET").notNull(),
  statusCode: int("statusCode").notNull(),
  requestUnits: int("requestUnits").default(1).notNull(),
  latencyMs: int("latencyMs").default(0).notNull(),
  ipAddress: varchar("ipAddress", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const complianceEvents = mysqlTable("complianceEvents", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId"),
  searchRequestId: int("searchRequestId"),
  eventType: mysqlEnum("eventType", ["consent_captured", "terms_accepted", "policy_acknowledged", "access_granted", "access_denied", "review_flagged", "export_requested"]).notNull(),
  severity: mysqlEnum("severity", ["info", "warning", "critical"]).default("info").notNull(),
  notes: text("notes"),
  metadataJson: json("metadataJson"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const systemSettings = mysqlTable("systemSettings", {
  id: int("id").autoincrement().primaryKey(),
  settingKey: varchar("settingKey", { length: 120 }).notNull().unique(),
  scope: mysqlEnum("scope", ["global", "billing", "search", "api", "notifications", "localization"]).default("global").notNull(),
  settingValue: text("settingValue").notNull(),
  updatedByUserId: int("updatedByUserId"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type SubscriptionPlan = typeof subscriptionPlans.$inferSelect;
export type InsertSubscriptionPlan = typeof subscriptionPlans.$inferInsert;
export type Subscription = typeof subscriptions.$inferSelect;
export type InsertSubscription = typeof subscriptions.$inferInsert;
export type Transaction = typeof transactions.$inferSelect;
export type InsertTransaction = typeof transactions.$inferInsert;
export type ApiKey = typeof apiKeys.$inferSelect;
export type InsertApiKey = typeof apiKeys.$inferInsert;
export type SearchRequest = typeof searchRequests.$inferSelect;
export type InsertSearchRequest = typeof searchRequests.$inferInsert;
export type SearchCandidate = typeof searchCandidates.$inferSelect;
export type InsertSearchCandidate = typeof searchCandidates.$inferInsert;
export type AuditLog = typeof auditLogs.$inferSelect;
export type InsertAuditLog = typeof auditLogs.$inferInsert;
export type Notification = typeof notifications.$inferSelect;
export type InsertNotification = typeof notifications.$inferInsert;
export type ApiUsageMetric = typeof apiUsageMetrics.$inferSelect;
export type InsertApiUsageMetric = typeof apiUsageMetrics.$inferInsert;
export type ComplianceEvent = typeof complianceEvents.$inferSelect;
export type InsertComplianceEvent = typeof complianceEvents.$inferInsert;
export type SystemSetting = typeof systemSettings.$inferSelect;
export type InsertSystemSetting = typeof systemSettings.$inferInsert;
