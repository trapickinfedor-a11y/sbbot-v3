import { z } from "zod";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { adminProcedure, protectedProcedure, publicProcedure, router } from "./_core/trpc";
import {
  createApiKeySchema,
  createBroadcastSchema,
  createBulkJobSchema,
  createJobSchema,
  jobFilterSchema,
  listApiKeysSchema,
  metricFilterSchema,
  revokeApiKeySchema,
  updateBotTextSchema,
} from "../shared/platform";
import {
  createApiKeyRecord,
  createBroadcastCampaign,
  createBulkJob,
  createSafeImportedLeadBatch,
  createSingleJob,
  getAdminOverview,
  getApiUsageSummary,
  getBillingModule,
  getBotTextsModule,
  getBroadcastsModule,
  getJobDetails,
  getJobsModule,
  getOperatorLogsModule,
  getProxyModule,
  getRevenueAnalyticsModule,
  getSafeTestBench,
  getSystemModule,
  getTelemetryModule,
  getWorkersModule,
  listUserApiKeys,
  previewImportedLeadText,
  revokeUserApiKey,
  updateBotTextTemplate,
} from "./platformService";

const jobsRouter = router({
  list: adminProcedure.input(jobFilterSchema.optional()).query(async () => {
    return getJobsModule();
  }),
  get: protectedProcedure
    .input(z.object({ publicId: z.string().min(3).max(64) }))
    .query(async ({ input }) => {
      return getJobDetails(input.publicId);
    }),
  createSafeSingle: adminProcedure.input(createJobSchema).mutation(async ({ ctx, input }) => {
    return createSingleJob(
      {
        ...input,
        safeTestMode: true,
      },
      { userId: ctx.user.id, source: "dashboard" },
    );
  }),
  createSafeBulk: adminProcedure.input(createBulkJobSchema).mutation(async ({ ctx, input }) => {
    return createBulkJob(
      {
        ...input,
        safeTestMode: true,
      },
      { userId: ctx.user.id, source: "dashboard" },
    );
  }),
});

const proxiesRouter = router({
  summary: adminProcedure.query(async () => {
    return getProxyModule();
  }),
});

const workersRouter = router({
  summary: adminProcedure.query(async () => {
    return getWorkersModule();
  }),
});

const billingRouter = router({
  summary: adminProcedure.query(async () => {
    return getBillingModule();
  }),
  usage: protectedProcedure.query(async () => {
    return getApiUsageSummary();
  }),
});

const telemetryRouter = router({
  summary: adminProcedure.input(metricFilterSchema.optional()).query(async () => {
    return getTelemetryModule();
  }),
});

const revenueRouter = router({
  summary: adminProcedure.query(async () => {
    return getRevenueAnalyticsModule();
  }),
});

const logsRouter = router({
  summary: adminProcedure.query(async () => {
    return getOperatorLogsModule();
  }),
});

const platformRouter = router({
  overview: adminProcedure.query(async () => {
    return getAdminOverview();
  }),
  system: adminProcedure.query(async () => {
    return getSystemModule();
  }),
  safeTestBench: adminProcedure.query(async () => {
    return getSafeTestBench();
  }),
});

const apiKeysRouter = router({
  create: protectedProcedure.input(createApiKeySchema).mutation(async ({ ctx, input }) => {
    return createApiKeyRecord(ctx.user.id, input);
  }),
  list: protectedProcedure.input(listApiKeysSchema).query(async ({ ctx, input }) => {
    const requestedUserId = input?.userId;
    const effectiveUserId = ctx.user.role === "admin" ? requestedUserId : ctx.user.id;
    return listUserApiKeys(effectiveUserId);
  }),
  revoke: protectedProcedure.input(revokeApiKeySchema).mutation(async ({ ctx, input }) => {
    return revokeUserApiKey(ctx.user.id, input.id);
  }),
  usage: protectedProcedure.query(async () => {
    return getApiUsageSummary();
  }),
});

const importedDataRouter = router({
  preview: adminProcedure
    .input(z.object({ inputText: z.string().min(1).max(200000) }))
    .mutation(async ({ input }) => {
      return previewImportedLeadText(input.inputText);
    }),
  createSafeBatch: adminProcedure
    .input(z.object({ inputText: z.string().min(1).max(200000) }))
    .mutation(async ({ ctx, input }) => {
      return createSafeImportedLeadBatch(input.inputText, {
        userId: ctx.user.id,
        source: "dashboard",
      });
    }),
});

const botTextsRouter = router({
  summary: adminProcedure.query(async () => {
    return getBotTextsModule();
  }),
  update: adminProcedure.input(updateBotTextSchema).mutation(async ({ ctx, input }) => {
    return updateBotTextTemplate(input, { userId: ctx.user.id });
  }),
});

const broadcastsRouter = router({
  summary: adminProcedure.query(async () => {
    return getBroadcastsModule();
  }),
  create: adminProcedure.input(createBroadcastSchema).mutation(async ({ ctx, input }) => {
    return createBroadcastCampaign(input, { userId: ctx.user.id });
  }),
});

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),
  jobs: jobsRouter,
  proxies: proxiesRouter,
  workers: workersRouter,
  billing: billingRouter,
  telemetry: telemetryRouter,
  revenue: revenueRouter,
  logs: logsRouter,
  platform: platformRouter,
  apiKeys: apiKeysRouter,
  importedData: importedDataRouter,
  botTexts: botTextsRouter,
  broadcasts: broadcastsRouter,
  publicApi: router({
    health: publicProcedure.query(async () => {
      const system = await getSystemModule();
      return system.health;
    }),
  }),
});

export type AppRouter = typeof appRouter;
