import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import DashboardLayout from "@/components/DashboardLayout";
import { trpc } from "@/lib/trpc";
import { AlertCircle, Copy, KeyRound, ShieldCheck } from "lucide-react";
import { useLocation } from "wouter";

type PageKey =
  | "jobs"
  | "proxy"
  | "workers"
  | "billing"
  | "revenue"
  | "logs"
  | "logchat"
  | "telemetry"
  | "system"
  | "safebench"
  | "bottexts"
  | "broadcasts";

type ApiKeyScope = "single" | "bulk" | "vip" | "admin";

type ApiKeyDraft = {
  label: string;
  scope: ApiKeyScope;
  rpmLimit: string;
  dailyLimit: string;
  expiresAt: string;
};

type BotTextDraft = {
  title: string;
  description: string;
  body: string;
};

type BroadcastAudience = "linked_telegram_users" | "manual_chat_ids";

type BroadcastDraft = {
  title: string;
  message: string;
  audience: BroadcastAudience;
  manualChatIds: string;
};

type HealthSnapshot = {
  status?: string;
  queues?: Record<string, { depth: number; lagSeconds: number }>;
  providers?: Record<string, { status?: string; successRate?: number; avgLeaseMs?: number }>;
  workers?: { total?: number; healthy?: number };
};

export const pageMeta: Record<PageKey, { title: string; description: string }> = {
  jobs: {
    title: "Jobs",
    description: "Операторский обзор очередей, статусов, попыток и событий по заданиям.",
  },
  proxy: {
    title: "Proxy",
    description: "Текущая read-only сводка по провайдерам, policy и health fallback-контуру.",
  },
  workers: {
    title: "Workers",
    description: "Контроль worker-узлов, concurrency, heartbeat и безопасных execution-рекомендаций.",
  },
  billing: {
    title: "Billing",
    description: "Тарифы, подписки, платежи и usage economics по уже реализованному billing-модулю.",
  },
  revenue: {
    title: "Revenue",
    description: "Отдельная аналитика дохода: collected revenue, refunds, MRR и разрезы по провайдерам и тарифам.",
  },
  logs: {
    title: "Logs",
    description: "Единая операторская лента audit и job events со всеми доступными логами по безопасному контуру.",
  },
  logchat: {
    title: "All Logs Chat",
    description: "Отдельный полноформатный чат со всеми логами: audit, job и системные события в одном read-only потоке.",
  },
  telemetry: {
    title: "Metrics",
    description: "Системная телеметрия, queue health, success rate, retry rate и последние audit-события.",
  },
  system: {
    title: "System",
    description: "Системный статус, readiness snapshot, checklist стабилизации и rollout/rollback guidance для операторской проверки.",
  },
  safebench: {
    title: "Safe Bench",
    description: "Отдельный safe-test контур: сценарии регрессии, входные gate и операторские guardrails без live runtime-мутаций.",
  },
  bottexts: {
    title: "Bot Texts",
    description: "Редактирование операторских текстов бота, которые должны обновляться без ручного деплоя и без вмешательства в код.",
  },
  broadcasts: {
    title: "Broadcasts",
    description: "Запуск dry-run и реальных Telegram-рассылок по связанным chatId или вручную заданным получателям.",
  },
};

const toneMap: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  healthy: "secondary",
  active: "secondary",
  succeeded: "secondary",
  running: "secondary",
  confirmed: "secondary",
  paid: "secondary",
  success: "secondary",
  info: "outline",
  degraded: "outline",
  waiting_retry: "outline",
  pending: "outline",
  warned: "outline",
  denied: "outline",
  disabled: "destructive",
  failed: "destructive",
  failure: "destructive",
  error: "destructive",
  offline: "destructive",
  expired: "destructive",
  refunded: "outline",
  maintenance: "outline",
  revoked: "outline",
};

const DEFAULT_API_KEY_DRAFT: ApiKeyDraft = {
  label: "",
  scope: "single",
  rpmLimit: "60",
  dailyLimit: "1000",
  expiresAt: "",
};

const DEFAULT_BROADCAST_DRAFT: BroadcastDraft = {
  title: "",
  message: "",
  audience: "linked_telegram_users",
  manualChatIds: "",
};

const API_KEY_SCOPE_OPTIONS: Array<{ value: ApiKeyScope; label: string; description: string }> = [
  { value: "single", label: "Single", description: "Базовые одиночные запросы." },
  { value: "bulk", label: "Bulk", description: "Пакетные сценарии и bulk endpoints." },
  { value: "vip", label: "VIP", description: "Расширенный контур с VIP endpoints." },
  { value: "admin", label: "Admin", description: "Операторский ключ с максимальными правами." },
];

export default function Operations() {
  const [location] = useLocation();
  const pageKey = resolvePageKey(location);
  const meta = pageMeta[pageKey];
  const [isCreateDialogOpen, setIsCreateDialogOpen] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);
  const [createdToken, setCreatedToken] = React.useState<string | null>(null);
  const [copiedToken, setCopiedToken] = React.useState(false);
  const [draft, setDraft] = React.useState<ApiKeyDraft>(DEFAULT_API_KEY_DRAFT);
  const [botTextDrafts, setBotTextDrafts] = React.useState<Record<string, BotTextDraft>>({});
  const [selectedBotTextKey, setSelectedBotTextKey] = React.useState<string>("welcome");
  const [botTextFeedback, setBotTextFeedback] = React.useState<string | null>(null);
  const [broadcastDraft, setBroadcastDraft] = React.useState<BroadcastDraft>(DEFAULT_BROADCAST_DRAFT);
  const [broadcastFeedback, setBroadcastFeedback] = React.useState<string | null>(null);
  const [lastBroadcastResult, setLastBroadcastResult] = React.useState<any | null>(null);

  const utils = trpc.useUtils();
  const jobsQuery = trpc.jobs.list.useQuery();
  const proxyQuery = trpc.proxies.summary.useQuery();
  const workersQuery = trpc.workers.summary.useQuery();
  const billingQuery = trpc.billing.summary.useQuery();
  const revenueQuery = trpc.revenue.summary.useQuery();
  const logsQuery = trpc.logs.summary.useQuery();
  const apiKeysQuery = trpc.apiKeys.list.useQuery();
  const telemetryQuery = trpc.telemetry.summary.useQuery();
  const systemQuery = trpc.platform.system.useQuery();
  const botTextsQuery = trpc.botTexts.summary.useQuery();
  const broadcastsQuery = trpc.broadcasts.summary.useQuery();

  const createApiKeyMutation = trpc.apiKeys.create.useMutation({
    onSuccess: async (result) => {
      setCreatedToken(result.preview);
      setCreateError(null);
      setCopiedToken(false);
      setDraft(DEFAULT_API_KEY_DRAFT);
      await Promise.all([
        utils.apiKeys.list.invalidate(),
        utils.apiKeys.usage.invalidate(),
        utils.billing.summary.invalidate(),
        utils.telemetry.summary.invalidate(),
      ]);
    },
    onError: (error) => {
      setCreateError(error.message);
    },
  });

  const revokeApiKeyMutation = trpc.apiKeys.revoke.useMutation({
    onSuccess: async () => {
      await Promise.all([
        utils.apiKeys.list.invalidate(),
        utils.apiKeys.usage.invalidate(),
        utils.billing.summary.invalidate(),
        utils.telemetry.summary.invalidate(),
      ]);
    },
  });

  const updateBotTextMutation = trpc.botTexts.update.useMutation({
    onSuccess: async (result) => {
      setBotTextFeedback(`Шаблон «${result.title}» сохранён.`);
      setBotTextDrafts(current => ({
        ...current,
        [result.key]: {
          title: result.title,
          description: result.description ?? "",
          body: result.body,
        },
      }));
      await Promise.all([utils.botTexts.summary.invalidate(), utils.logs.summary.invalidate()]);
    },
    onError: error => {
      setBotTextFeedback(error.message);
    },
  });

  const createBroadcastMutation = trpc.broadcasts.create.useMutation({
    onSuccess: async result => {
      setLastBroadcastResult(result);
      setBroadcastFeedback(
        result.dryRun
          ? `Dry run завершён: ${result.deliveredCount}/${result.requestedRecipients} получателей готовы.`
          : `Рассылка завершена: доставлено ${result.deliveredCount} из ${result.requestedRecipients}.`,
      );
      await Promise.all([utils.broadcasts.summary.invalidate(), utils.logs.summary.invalidate()]);
    },
    onError: error => {
      setBroadcastFeedback(error.message);
    },
  });

  React.useEffect(() => {
    const texts = botTextsQuery.data?.texts ?? [];
    if (!texts.length) {
      return;
    }

    setBotTextDrafts(current => {
      const next = { ...current };
      let changed = false;

      texts.forEach((text: any) => {
        if (!next[text.key]) {
          next[text.key] = {
            title: text.title,
            description: text.description ?? "",
            body: text.body,
          };
          changed = true;
        }
      });

      return changed ? next : current;
    });

    setSelectedBotTextKey(current =>
      texts.some((text: any) => text.key === current) ? current : texts[0].key,
    );
  }, [botTextsQuery.data?.texts]);

  const queries = [
    jobsQuery,
    proxyQuery,
    workersQuery,
    billingQuery,
    revenueQuery,
    logsQuery,
    apiKeysQuery,
    telemetryQuery,
    systemQuery,
    botTextsQuery,
    broadcastsQuery,
  ];
  const firstError = queries.find(query => query.error)?.error;
  const isAnyLoading = queries.some(query => query.isLoading);

  const handleDraftChange = (field: keyof ApiKeyDraft, value: string) => {
    setDraft(current => ({ ...current, [field]: value }));
    if (createError) {
      setCreateError(null);
    }
  };

  const handleCreateApiKey = async () => {
    const label = draft.label.trim();
    const rpmLimit = Number(draft.rpmLimit);
    const dailyLimit = Number(draft.dailyLimit);

    if (!label) {
      setCreateError("Введите понятный label для нового ключа.");
      return;
    }

    if (!Number.isInteger(rpmLimit) || rpmLimit < 1 || rpmLimit > 10000) {
      setCreateError("RPM limit должен быть целым числом от 1 до 10000.");
      return;
    }

    if (!Number.isInteger(dailyLimit) || dailyLimit < 1 || dailyLimit > 1000000) {
      setCreateError("Daily limit должен быть целым числом от 1 до 1000000.");
      return;
    }

    const expiresAtTimestamp = draft.expiresAt ? new Date(draft.expiresAt).getTime() : undefined;
    if (draft.expiresAt && Number.isNaN(expiresAtTimestamp)) {
      setCreateError("Expiry должен быть валидной датой и временем.");
      return;
    }

    await createApiKeyMutation.mutateAsync({
      label,
      scope: draft.scope,
      rpmLimit,
      dailyLimit,
      expiresAt: expiresAtTimestamp,
    });
  };

  const handleCopyCreatedToken = async () => {
    if (!createdToken || typeof navigator === "undefined" || !navigator.clipboard) {
      return;
    }

    await navigator.clipboard.writeText(createdToken);
    setCopiedToken(true);
  };

  const handleDialogOpenChange = (open: boolean) => {
    setIsCreateDialogOpen(open);
    setCreateError(null);
    if (!open) {
      setDraft(DEFAULT_API_KEY_DRAFT);
      setCopiedToken(false);
      setCreatedToken(null);
    }
  };

  const handleBotTextDraftChange = (field: keyof BotTextDraft, value: string) => {
    setBotTextFeedback(null);
    setBotTextDrafts(current => ({
      ...current,
      [selectedBotTextKey]: {
        title: current[selectedBotTextKey]?.title ?? "",
        description: current[selectedBotTextKey]?.description ?? "",
        body: current[selectedBotTextKey]?.body ?? "",
        [field]: value,
      },
    }));
  };

  const handleSaveBotText = async () => {
    const currentDraft = botTextDrafts[selectedBotTextKey];
    if (!selectedBotTextKey || !currentDraft) {
      setBotTextFeedback("Выберите шаблон, который нужно отредактировать.");
      return;
    }

    if (!currentDraft.title.trim() || !currentDraft.body.trim()) {
      setBotTextFeedback("У шаблона должны быть заполнены title и body.");
      return;
    }

    await updateBotTextMutation.mutateAsync({
      key: selectedBotTextKey as any,
      title: currentDraft.title.trim(),
      description: currentDraft.description.trim() || undefined,
      body: currentDraft.body,
    });
  };

  const handleBroadcastDraftChange = (field: keyof BroadcastDraft, value: string) => {
    setBroadcastFeedback(null);
    setBroadcastDraft(current => ({ ...current, [field]: value }));
  };

  const handleCreateBroadcast = async (dryRun: boolean) => {
    const title = broadcastDraft.title.trim();
    const message = broadcastDraft.message.trim();
    const manualChatIds = broadcastDraft.manualChatIds
      .split(/[\n,]+/)
      .map(item => item.trim())
      .filter(Boolean);

    if (!title || !message) {
      setBroadcastFeedback("Для рассылки нужно заполнить title и message.");
      return;
    }

    if (broadcastDraft.audience === "manual_chat_ids" && manualChatIds.length === 0) {
      setBroadcastFeedback("Укажите хотя бы один manual chat ID для этого режима доставки.");
      return;
    }

    await createBroadcastMutation.mutateAsync({
      title,
      message,
      audience: broadcastDraft.audience,
      parseMode: "plain",
      manualChatIds,
      dryRun,
    });
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-2xl tracking-tight">{meta.title}</CardTitle>
                  <CardDescription>{meta.description}</CardDescription>
                </div>
                <Badge variant="secondary" className="gap-1.5 px-3 py-1 text-xs">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Operator admin surface
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {firstError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Module data error</AlertTitle>
                  <AlertDescription>{firstError.message}</AlertDescription>
                </Alert>
              ) : null}

              {isAnyLoading ? (
                <Alert>
                  <ShieldCheck className="h-4 w-4" />
                  <AlertTitle>Loading module snapshot</AlertTitle>
                  <AlertDescription>
                    Typed queries are refreshing the current admin section. Summary cards and tables will populate as soon as the
                    module response arrives.
                  </AlertDescription>
                </Alert>
              ) : null}

              <Alert>
                <ShieldCheck className="h-4 w-4" />
                <AlertTitle>Safe operations boundary</AlertTitle>
                  <AlertDescription>
                    Этот раздел показывает уже доступные backend-данные и безопасные состояния. Часть модулей уже поддерживает
                    operator-safe действия: выпуск API key, редактирование Bot Texts и dry-run или live Telegram-рассылки.
                  </AlertDescription>

              </Alert>
            </CardContent>
          </Card>

          <SummaryRail
            pageKey={pageKey}
            jobs={jobsQuery.data ?? []}
            providers={proxyQuery.data?.providers ?? []}
            workers={workersQuery.data?.workers ?? []}
            billing={billingQuery.data ?? null}
            revenue={revenueQuery.data ?? null}
            logs={logsQuery.data ?? null}
            telemetry={telemetryQuery.data ?? null}
            system={systemQuery.data ?? null}
            botTexts={botTextsQuery.data ?? null}
            broadcasts={broadcastsQuery.data ?? null}
          />
        </section>

        {pageKey === "jobs" ? <JobsSection jobs={jobsQuery.data ?? []} /> : null}
        {pageKey === "proxy" ? <ProxySection proxy={proxyQuery.data ?? null} /> : null}
        {pageKey === "workers" ? <WorkersSection workers={workersQuery.data ?? null} /> : null}
        {pageKey === "billing" ? (
          <BillingSection
            billing={billingQuery.data ?? null}
            apiKeys={apiKeysQuery.data ?? []}
            isRevoking={revokeApiKeyMutation.isPending}
            isCreating={createApiKeyMutation.isPending}
            createError={createError}
            createdToken={createdToken}
            copiedToken={copiedToken}
            draft={draft}
            isCreateDialogOpen={isCreateDialogOpen}
            onDialogOpenChange={handleDialogOpenChange}
            onDraftChange={handleDraftChange}
            onCreate={handleCreateApiKey}
            onCopyCreatedToken={handleCopyCreatedToken}
            onRevoke={async (id: number) => {
              await revokeApiKeyMutation.mutateAsync({ id });
            }}
          />
        ) : null}
        {pageKey === "revenue" ? <RevenueSection revenue={revenueQuery.data ?? null} /> : null}
        {pageKey === "logs" ? <LogsSection logs={logsQuery.data ?? null} /> : null}
        {pageKey === "logchat" ? <LogChatSection logs={logsQuery.data ?? null} /> : null}
        {pageKey === "telemetry" ? <TelemetrySection telemetry={telemetryQuery.data ?? null} /> : null}
        {pageKey === "system" ? <SystemSection system={systemQuery.data ?? null} /> : null}
        {pageKey === "safebench" ? <SafeBenchSection system={systemQuery.data ?? null} /> : null}
        {pageKey === "bottexts" ? (
          <BotTextsSection
            module={botTextsQuery.data ?? null}
            selectedKey={selectedBotTextKey}
            drafts={botTextDrafts}
            feedback={botTextFeedback}
            isSaving={updateBotTextMutation.isPending}
            onSelectedKeyChange={setSelectedBotTextKey}
            onDraftChange={handleBotTextDraftChange}
            onSave={handleSaveBotText}
          />
        ) : null}
        {pageKey === "broadcasts" ? (
          <BroadcastsSection
            module={broadcastsQuery.data ?? null}
            draft={broadcastDraft}
            feedback={broadcastFeedback}
            isSubmitting={createBroadcastMutation.isPending}
            lastResult={lastBroadcastResult}
            onDraftChange={handleBroadcastDraftChange}
            onCreate={handleCreateBroadcast}
          />
        ) : null}
      </div>
    </DashboardLayout>
  );
}

function SummaryRail({
  pageKey,
  jobs,
  providers,
  workers,
  billing,
  revenue,
  logs,
  telemetry,
  system,
  botTexts,
  broadcasts,
}: {
  pageKey: PageKey;
  jobs: Array<any>;
  providers: Array<any>;
  workers: Array<any>;
  billing: any;
  revenue: any;
  logs: any;
  telemetry: any;
  system: any;
  botTexts: any;
  broadcasts: any;
}) {
  const health = (telemetry?.health ?? system?.health ?? null) as HealthSnapshot | null;

  const cards: Record<PageKey, Array<{ label: string; value: string }>> = {
    jobs: [
      { label: "Jobs loaded", value: String(jobs.length) },
      { label: "Running", value: String(jobs.filter(job => job.status === "running").length) },
      { label: "Waiting retry", value: String(jobs.filter(job => job.status === "waiting_retry").length) },
    ],
    proxy: [
      { label: "Providers", value: String(providers.length) },
      { label: "Policies", value: String(providers.length) },
      { label: "Health status", value: String(health?.status ?? "Unknown") },
    ],
    workers: [
      { label: "Workers", value: String(workers.length) },
      { label: "Healthy", value: String(health?.workers?.healthy ?? workers.filter(worker => worker.status === "healthy").length) },
      { label: "Busy", value: String(workers.filter(worker => worker.activeJobs > 0).length) },
    ],
    billing: [
      { label: "Plans", value: String(billing?.plans?.length ?? 0) },
      { label: "Subscriptions", value: String(billing?.subscriptions?.length ?? 0) },
      { label: "Payments", value: String(billing?.payments?.length ?? 0) },
    ],
    revenue: [
      { label: "Collected", value: formatMoney(revenue?.overview?.totalCollectedUsd) },
      { label: "MRR", value: formatMoney(revenue?.overview?.estimatedMrrUsd) },
      { label: "Refunded", value: formatMoney(revenue?.overview?.refundedUsd) },
    ],
    logs: [
      { label: "Log entries", value: String(logs?.counters?.total ?? 0) },
      { label: "Audit", value: String(logs?.counters?.sources?.audit ?? 0) },
      { label: "Job events", value: String(logs?.counters?.sources?.job_event ?? 0) },
    ],
    logchat: [
      { label: "Visible stream", value: String(logs?.timeline?.length ?? 0) },
      { label: "Audit", value: String(logs?.counters?.sources?.audit ?? 0) },
      { label: "Critical", value: String((logs?.timeline ?? []).filter((entry: any) => isCriticalLogEntry(entry)).length) },
    ],
    telemetry: [
      { label: "Success rate", value: formatPercent(telemetry?.successRate) },
      { label: "Retry rate", value: formatPercent(telemetry?.retryRate) },
      { label: "Audit events", value: String(telemetry?.recentAudit?.length ?? 0) },
    ],
    system: [
      { label: "Platform status", value: String(health?.status ?? "Unknown") },
      { label: "Readiness gates", value: String(system?.readinessSnapshot?.length ?? 0) },
      { label: "Checklist items", value: String(system?.stabilizationChecklist?.length ?? 0) },
    ],
    safebench: [
      { label: "Safe scenarios", value: String(system?.safeTestScenarios?.length ?? 0) },
      { label: "Entry gates", value: String(system?.readinessSnapshot?.length ?? 0) },
      { label: "Runbook steps", value: String(system?.rolloutRunbook?.length ?? 0) },
    ],
    bottexts: [
      { label: "Templates", value: String(botTexts?.summary?.totalTemplates ?? 0) },
      { label: "Recipients", value: String(botTexts?.summary?.activeRecipients ?? 0) },
      { label: "Telegram", value: botTexts?.summary?.telegramConfigured ? "Configured" : "Missing" },
    ],
    broadcasts: [
      { label: "Broadcasts", value: String(broadcasts?.summary?.totalBroadcasts ?? 0) },
      { label: "Linked recipients", value: String(broadcasts?.summary?.linkedRecipients ?? 0) },
      { label: "Telegram", value: broadcasts?.summary?.telegramConfigured ? "Configured" : "Missing" },
    ],
  };

  return (
    <Card className="border-0 shadow-sm">
      <CardHeader>
        <CardTitle>Current module status</CardTitle>
        <CardDescription>Быстрый сводный срез по активному разделу админ-панели.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {cards[pageKey].map(card => (
          <div key={card.label} className="rounded-xl border bg-muted/30 p-4">
            <p className="text-sm text-muted-foreground">{card.label}</p>
            <p className="mt-2 text-lg font-semibold tracking-tight">{card.value}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function JobsSection({ jobs }: { jobs: Array<any> }) {
  return (
    <Card className="border-0 shadow-sm">
      <CardHeader>
        <CardTitle>Job list</CardTitle>
        <CardDescription>Последние задания с режимом, источником, стоимостью и статусом.</CardDescription>
      </CardHeader>
      <CardContent>
        {jobs.length ? (
          <ScrollArea className="w-full">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>ONE CS</TableHead>
                  <TableHead>Attempts</TableHead>
                  <TableHead>Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map(job => (
                  <TableRow key={job.publicId}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">{job.targetLabel ?? job.publicId}</p>
                        <p className="font-mono text-xs text-muted-foreground">{job.publicId}</p>
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{job.requestMode}</TableCell>
                    <TableCell className="capitalize">{job.source}</TableCell>
                    <TableCell>
                      <Badge variant={toneMap[job.status] ?? "outline"}>{job.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {job.resultJson?.oneCsResult ? (
                        <div className="space-y-1 text-xs">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <Badge variant="secondary">CS {job.resultJson.oneCsResult.creditScore ?? "—"}</Badge>
                            <Badge variant="outline">P {job.resultJson.oneCsResult.productScore}/20</Badge>
                            <Badge variant="outline">Q {job.resultJson.oneCsResult.dataQualityScore}/10</Badge>
                          </div>
                          <p className="capitalize text-muted-foreground">{String(job.resultJson.oneCsResult.status ?? "—").replace(/_/g, " ")}</p>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {job.attemptCount}/{job.maxAttempts}
                    </TableCell>
                    <TableCell>{formatMoney(job.costEstimateUsd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        ) : (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>No jobs available</EmptyTitle>
              <EmptyDescription>Когда jobs-модуль вернёт записи, они появятся в этой таблице.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </CardContent>
    </Card>
  );
}

function ProxySection({ proxy }: { proxy: any }) {
  const providers = proxy?.providers ?? [];
  const policies = proxy?.policies ?? [];
  const healthRows = proxy?.providerHealth ?? [];

  if (!providers.length && !policies.length && !healthRows.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Proxy module is empty</CardTitle>
          <CardDescription>Когда proxy summary вернёт провайдеров и policy, они появятся в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Providers</CardTitle>
          <CardDescription>Текущие провайдеры прокси с протоколами, priority и статусом.</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="w-full">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Cost / GB</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {providers.map((provider: any) => (
                  <TableRow key={provider.code}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">{provider.name}</p>
                        <p className="text-xs text-muted-foreground">{provider.protocolSupport}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={toneMap[provider.status] ?? "outline"}>{provider.status}</Badge>
                    </TableCell>
                    <TableCell>{provider.priority}</TableCell>
                    <TableCell>{formatMoney(provider.costPerGbUsd)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Policies and health</CardTitle>
          <CardDescription>Policy-настройки маршрутизации и health summary по провайдерам.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {policies.map((policy: any) => (
              <div key={policy.code} className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{policy.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {policy.protocol} · {policy.sessionMode} · retries {policy.maxTransportRetries}
                    </p>
                  </div>
                  <Badge variant={policy.isDefault === "yes" ? "secondary" : "outline"}>
                    {policy.isDefault === "yes" ? "Default" : "Optional"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            {healthRows.map((row: any) => (
              <div key={row.code} className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{row.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Health score {Math.round((row.healthScore ?? 0) * 100)}% · checked {String(row.lastCheckedAt)}
                    </p>
                  </div>
                  <Badge variant={toneMap[row.status] ?? "outline"}>{row.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function WorkersSection({ workers }: { workers: any }) {
  const workerRows = workers?.workers ?? [];
  const recommendations = workers?.recommendations ?? [];
  const queueHealth = workers?.queueHealth ?? {};

  if (!workerRows.length && !recommendations.length && !Object.keys(queueHealth).length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Workers module is empty</CardTitle>
          <CardDescription>Когда workers summary вернёт узлы и queue health, они появятся в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Worker nodes</CardTitle>
          <CardDescription>Read-only срез по worker-узлам, heartbeat и concurrency.</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="w-full">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Worker</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Active / Limit</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workerRows.map((worker: any) => (
                  <TableRow key={worker.code}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">{worker.name}</p>
                        <p className="text-xs text-muted-foreground">{worker.hostLabel}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={toneMap[worker.status] ?? "outline"}>{worker.status}</Badge>
                    </TableCell>
                    <TableCell>{worker.role}</TableCell>
                    <TableCell>
                      {worker.activeJobs}/{worker.concurrencyLimit}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Queue posture and recommendations</CardTitle>
          <CardDescription>Безопасные операторские подсказки для текущего execution-контура.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            {Object.entries(queueHealth).map(([queueName, queue]: [string, any]) => (
              <div key={queueName} className="rounded-xl border bg-muted/20 p-4">
                <p className="font-medium capitalize">{queueName}</p>
                <p className="mt-2 text-sm text-muted-foreground">Depth {queue.depth}</p>
                <p className="text-sm text-muted-foreground">Lag {queue.lagSeconds}s</p>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            {recommendations.map((item: string) => (
              <div key={item} className="rounded-xl border bg-muted/20 p-4 text-sm text-muted-foreground">
                {item}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function BillingSection({
  billing,
  apiKeys,
  isRevoking,
  isCreating,
  createError,
  createdToken,
  copiedToken,
  draft,
  isCreateDialogOpen,
  onDialogOpenChange,
  onDraftChange,
  onCreate,
  onCopyCreatedToken,
  onRevoke,
}: {
  billing: any;
  apiKeys: any[];
  isRevoking: boolean;
  isCreating: boolean;
  createError: string | null;
  createdToken: string | null;
  copiedToken: boolean;
  draft: ApiKeyDraft;
  isCreateDialogOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
  onDraftChange: (field: keyof ApiKeyDraft, value: string) => void;
  onCreate: () => Promise<void>;
  onCopyCreatedToken: () => Promise<void>;
  onRevoke: (id: number) => Promise<void>;
}) {
  const plans = billing?.plans ?? [];
  const subscriptions = billing?.subscriptions ?? [];
  const payments = billing?.payments ?? [];
  const fallbackApiKeys = billing?.apiKeys ?? [];
  const resolvedApiKeys = apiKeys.length ? apiKeys : fallbackApiKeys;
  const usage = billing?.usageSummary ?? null;

  if (!plans.length && !subscriptions.length && !payments.length && !resolvedApiKeys.length && !usage) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Billing module is empty</CardTitle>
          <CardDescription>Когда billing summary вернёт тарифы, подписки и платежи, они появятся в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Plans and subscriptions</CardTitle>
          <CardDescription>Тарифы и активные подписки, доступные в read-only billing-витрине.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ScrollArea className="h-[320px] rounded-xl border bg-muted/10">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Plan</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Quotas</TableHead>
                  <TableHead>Access</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plans.map((plan: any) => (
                  <TableRow key={plan.code}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">{plan.name}</p>
                        <p className="text-xs text-muted-foreground">{plan.code}</p>
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{plan.tier}</TableCell>
                    <TableCell>
                      <div className="space-y-1 text-sm">
                        <p>{plan.currency} {plan.priceUsd}</p>
                        <p className="text-xs text-muted-foreground capitalize">{plan.billingInterval ?? "custom"}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      <div className="space-y-1">
                        <p>Requests {plan.includedRequests ?? 0}</p>
                        <p>API / month {plan.monthlyApiQuota ?? 0}</p>
                        <p>Browser runs {plan.monthlyBrowserRuns ?? 0}</p>
                        <p>Max RPM {plan.maxRpm ?? 0} · Concurrency {plan.maxConcurrentJobs ?? 0}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant={plan.vipApiAccess ? "secondary" : "outline"}>
                          {plan.vipApiAccess ? "VIP API enabled" : "Standard API only"}
                        </Badge>
                        {(plan.features ?? []).slice(0, 2).map((feature: string) => (
                          <Badge key={feature} variant="outline">{feature}</Badge>
                        ))}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>

          <div className="grid gap-3 sm:grid-cols-2">
            {subscriptions.map((subscription: any) => (
              <div key={subscription.id} className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">Subscription #{subscription.id}</p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Plan {subscription.planCode ?? subscription.planId ?? "—"} · Provider {subscription.provider}
                    </p>
                  </div>
                  <Badge className="mt-0" variant={toneMap[subscription.status] ?? "outline"}>{subscription.status}</Badge>
                </div>
                <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                  <p>Period {subscription.currentPeriodKey ?? subscription.billingInterval ?? "—"}</p>
                  <p>Usage requests {subscription.requestCount ?? subscription.requestsUsed ?? 0}</p>
                  <p>Browser runs {subscription.browserRunsUsed ?? subscription.browserRuns ?? 0}</p>
                  <p>VIP {subscription.vipApiAccess ? "enabled" : "standard"}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Payments and usage</CardTitle>
          <CardDescription>Последние платежи и агрегированная economics summary за текущий период.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricChip label="Requests" value={String(usage?.requests ?? 0)} />
            <MetricChip label="Browser runs" value={String(usage?.browserRuns ?? 0)} />
            <MetricChip label="Revenue" value={formatMoney(usage?.revenueUsd)} />
            <MetricChip label="Margin" value={formatMoney(usage?.marginUsd)} />
          </div>

          <ScrollArea className="h-[200px] rounded-xl border bg-muted/10">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Payment</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment: any) => (
                  <TableRow key={payment.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">Payment #{payment.id}</p>
                        <p className="text-xs text-muted-foreground">{payment.invoiceRef ?? payment.txRef ?? "—"}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={toneMap[payment.status] ?? "outline"}>{payment.status}</Badge>
                    </TableCell>
                    <TableCell>{payment.provider ?? "—"}</TableCell>
                    <TableCell>{payment.currency} {payment.amountUsd ?? payment.amount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-sm xl:col-span-2">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>API key issuance</CardTitle>
              <CardDescription>Безопасный выпуск ключей с выбором scope, лимитов и одноразовым показом токена.</CardDescription>
            </div>
            <Dialog open={isCreateDialogOpen} onOpenChange={onDialogOpenChange}>
              <DialogTrigger asChild>
                <Button>Create API key</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                  <DialogTitle>Create API key</DialogTitle>
                  <DialogDescription>Выберите scope, лимиты и optional expiry. Сырой токен будет показан только один раз.</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-2">
                  <div className="grid gap-2">
                    <Label htmlFor="api-key-label">Label</Label>
                    <Input id="api-key-label" value={draft.label} onChange={event => onDraftChange("label", event.target.value)} placeholder="VIP ingestion key" />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <div className="grid gap-2 sm:col-span-1">
                      <Label>Scope</Label>
                      <Select value={draft.scope} onValueChange={value => onDraftChange("scope", value)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select scope" />
                        </SelectTrigger>
                        <SelectContent>
                          {API_KEY_SCOPE_OPTIONS.map(option => (
                            <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        {API_KEY_SCOPE_OPTIONS.find(option => option.value === draft.scope)?.description}
                      </p>
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="api-key-rpm">RPM limit</Label>
                      <Input id="api-key-rpm" type="number" value={draft.rpmLimit} onChange={event => onDraftChange("rpmLimit", event.target.value)} />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="api-key-daily">Daily limit</Label>
                      <Input id="api-key-daily" type="number" value={draft.dailyLimit} onChange={event => onDraftChange("dailyLimit", event.target.value)} />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="api-key-expiry">Expiry</Label>
                    <Input id="api-key-expiry" type="datetime-local" value={draft.expiresAt} onChange={event => onDraftChange("expiresAt", event.target.value)} />
                  </div>
                  {createError ? (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertTitle>Create failed</AlertTitle>
                      <AlertDescription>{createError}</AlertDescription>
                    </Alert>
                  ) : null}
                  {createdToken ? (
                    <Alert>
                      <KeyRound className="h-4 w-4" />
                      <AlertTitle>Token shown once</AlertTitle>
                      <AlertDescription>
                        Сохраните токен сейчас: после закрытия окна будет доступен только prefix в таблице.
                      </AlertDescription>
                      <div className="mt-3 break-all rounded-lg border bg-background px-3 py-2 font-mono text-xs text-foreground">
                        {createdToken}
                      </div>
                    </Alert>
                  ) : null}
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  {createdToken ? (
                    <Button type="button" variant="outline" onClick={() => void onCopyCreatedToken()}>
                      <Copy className="mr-2 h-4 w-4" />
                      {copiedToken ? "Copied" : "Copy token"}
                    </Button>
                  ) : null}
                  <Button type="button" onClick={() => void onCreate()} disabled={isCreating}>
                    {isCreating ? "Creating..." : "Issue key"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {resolvedApiKeys.length ? (
            <ScrollArea className="w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Label</TableHead>
                    <TableHead>Prefix</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Limits</TableHead>
                    <TableHead>Last used</TableHead>
                    <TableHead>Expiry</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resolvedApiKeys.map((key: any) => {
                    const isRevoked = key.status === "revoked";
                    return (
                      <TableRow key={key.id}>
                        <TableCell className="font-medium">{key.label}</TableCell>
                        <TableCell className="font-mono text-xs">{key.keyPrefix}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{key.scope}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={toneMap[key.status] ?? "outline"}>{key.status}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          RPM {key.rpmLimit} · Daily {key.dailyLimit}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDateTime(key.lastUsedAt)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{formatDateTime(key.expiresAt)}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant={isRevoked ? "outline" : "destructive"}
                            size="sm"
                            disabled={isRevoked || isRevoking}
                            onClick={() => {
                              void onRevoke(key.id);
                            }}
                          >
                            {isRevoked ? "Revoked" : isRevoking ? "Revoking..." : "Revoke"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No API keys yet</EmptyTitle>
                <EmptyDescription>Ключи появятся здесь после создания через dashboard или API.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function RevenueSection({ revenue }: { revenue: any }) {
  const overview = revenue?.overview ?? null;
  const usageSummary = revenue?.usageSummary ?? null;
  const revenueByMonth = revenue?.revenueByMonth ?? [];
  const providerBreakdown = revenue?.providerBreakdown ?? [];
  const planBreakdown = revenue?.planBreakdown ?? [];
  const recentPayments = revenue?.recentPayments ?? [];
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [providerFilter, setProviderFilter] = React.useState<string>("all");

  const providerOptions = React.useMemo<string[]>(() => {
    return Array.from(new Set<string>(recentPayments.map((payment: any) => String(payment.provider ?? "unknown")))).sort((a, b) => a.localeCompare(b));
  }, [recentPayments]);

  const statusOptions = React.useMemo<string[]>(() => {
    return Array.from(new Set<string>(recentPayments.map((payment: any) => String(payment.status ?? "unknown")))).sort((a, b) => a.localeCompare(b));
  }, [recentPayments]);

  const paymentKpis = React.useMemo(() => {
    return recentPayments.reduce(
      (acc: {
        paidCount: number;
        paidAmount: number;
        refundedCount: number;
        refundedAmount: number;
        pendingCount: number;
        pendingAmount: number;
      }, payment: any) => {
        const status = String(payment.status ?? "unknown");
        const amount = Number(payment.amountUsd ?? payment.amount ?? 0);

        if (status === "paid" || status === "confirmed") {
          acc.paidCount += 1;
          acc.paidAmount += amount;
        }

        if (status === "refunded") {
          acc.refundedCount += 1;
          acc.refundedAmount += amount;
        }

        if (status === "pending") {
          acc.pendingCount += 1;
          acc.pendingAmount += amount;
        }

        return acc;
      },
      {
        paidCount: 0,
        paidAmount: 0,
        refundedCount: 0,
        refundedAmount: 0,
        pendingCount: 0,
        pendingAmount: 0,
      },
    );
  }, [recentPayments]);

  const filteredPayments = React.useMemo(() => {
    return recentPayments.filter((payment: any) => {
      const matchesStatus = statusFilter === "all" ? true : String(payment.status ?? "unknown") === statusFilter;
      const matchesProvider = providerFilter === "all" ? true : String(payment.provider ?? "unknown") === providerFilter;
      return matchesStatus && matchesProvider;
    });
  }, [providerFilter, recentPayments, statusFilter]);

  if (!overview && !usageSummary && !revenueByMonth.length && !providerBreakdown.length && !planBreakdown.length && !recentPayments.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Revenue module is empty</CardTitle>
          <CardDescription>Когда revenue summary вернёт collected revenue, breakdowns и recent payments, они появятся в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Collected revenue" value={formatMoney(overview?.totalCollectedUsd)} />
        <MetricChip label="Estimated MRR" value={formatMoney(overview?.estimatedMrrUsd)} />
        <MetricChip label="Refunded" value={formatMoney(overview?.refundedUsd)} />
        <MetricChip label="Active subscriptions" value={String(overview?.activeSubscriptions ?? 0)} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Paid / confirmed" value={`${paymentKpis.paidCount} · ${formatMoney(paymentKpis.paidAmount)}`} />
        <MetricChip label="Refunded payments" value={`${paymentKpis.refundedCount} · ${formatMoney(paymentKpis.refundedAmount)}`} />
        <MetricChip label="Pending payments" value={`${paymentKpis.pendingCount} · ${formatMoney(paymentKpis.pendingAmount)}`} />
        <MetricChip label="Visible after filters" value={String(filteredPayments.length)} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Monthly revenue timeline</CardTitle>
            <CardDescription>Срез по collected, refunded и pending revenue по месяцам.</CardDescription>
          </CardHeader>
          <CardContent>
            {revenueByMonth.length ? (
              <ScrollArea className="w-full">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Period</TableHead>
                      <TableHead>Collected</TableHead>
                      <TableHead>Refunded</TableHead>
                      <TableHead>Pending</TableHead>
                      <TableHead>Payments</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revenueByMonth.map((item: any) => (
                      <TableRow key={item.periodKey}>
                        <TableCell>{item.periodKey}</TableCell>
                        <TableCell>{formatMoney(item.collectedUsd)}</TableCell>
                        <TableCell>{formatMoney(item.refundedUsd)}</TableCell>
                        <TableCell>{formatMoney(item.pendingUsd)}</TableCell>
                        <TableCell>{item.paymentCount}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No monthly revenue yet</EmptyTitle>
                  <EmptyDescription>Помесячная выручка появится здесь, когда billing-данные вернут платежи.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Revenue quality snapshot</CardTitle>
            <CardDescription>Сводка по usage-based economics текущего периода.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricChip label="Usage revenue" value={formatMoney(overview?.usageRevenueUsd ?? usageSummary?.revenueUsd)} />
            <MetricChip label="Usage COGS" value={formatMoney(overview?.usageCogsUsd ?? usageSummary?.cogsUsd)} />
            <MetricChip label="Usage margin" value={formatMoney(overview?.usageMarginUsd ?? usageSummary?.marginUsd)} />
            <MetricChip label="Current period" value={String(overview?.currentPeriod ?? usageSummary?.currentPeriod ?? "—")} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Provider breakdown</CardTitle>
            <CardDescription>Выручка и возвраты в разрезе платёжных провайдеров.</CardDescription>
          </CardHeader>
          <CardContent>
            {providerBreakdown.length ? (
              <div className="space-y-3">
                {providerBreakdown.map((item: any) => (
                  <div key={item.provider} className="rounded-xl border bg-muted/20 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium capitalize">{item.provider}</p>
                        <p className="text-xs text-muted-foreground">Payments {item.paymentCount}</p>
                      </div>
                      <Badge variant="secondary">{formatMoney(item.collectedUsd)}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Refunded {formatMoney(item.refundedUsd)} · Pending {formatMoney(item.pendingUsd)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No provider breakdown yet</EmptyTitle>
                  <EmptyDescription>Разрез по провайдерам появится после первых платежей.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Plan breakdown</CardTitle>
            <CardDescription>Доход и активные подписки в разрезе тарифных планов.</CardDescription>
          </CardHeader>
          <CardContent>
            {planBreakdown.length ? (
              <div className="space-y-3">
                {planBreakdown.map((item: any) => (
                  <div key={item.planCode} className="rounded-xl border bg-muted/20 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{item.planName}</p>
                        <p className="text-xs text-muted-foreground">{item.planCode} · {item.tier}</p>
                      </div>
                      <Badge variant="outline">{formatMoney(item.collectedUsd)}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Payments {item.paymentCount} · Active subscriptions {item.activeSubscriptions}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No plan breakdown yet</EmptyTitle>
                  <EmptyDescription>Плановый revenue breakdown появится после маппинга платежей к подпискам и тарифам.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Recent payments</CardTitle>
              <CardDescription>Последние платежи для ручной сверки revenue analytics с billing-модулем.</CardDescription>
            </div>
            <Badge variant="secondary">Visible now: {filteredPayments.length}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr] xl:grid-cols-[1fr_1fr_auto_auto_auto_auto]">
            <div className="space-y-2">
              <Label htmlFor="revenue-status-filter">Payment status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger id="revenue-status-filter">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {statusOptions.map((status: string) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="revenue-provider-filter">Provider</Label>
              <Select value={providerFilter} onValueChange={setProviderFilter}>
                <SelectTrigger id="revenue-provider-filter">
                  <SelectValue placeholder="All providers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All providers</SelectItem>
                  {providerOptions.map((provider: string) => (
                    <SelectItem key={provider} value={provider}>
                      {provider}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button type="button" variant={statusFilter === "all" ? "default" : "outline"} onClick={() => setStatusFilter("all")}>
                All payments
              </Button>
            </div>
            <div className="flex items-end">
              <Button type="button" variant={statusFilter === "confirmed" ? "default" : "outline"} onClick={() => setStatusFilter("confirmed")}>
                Confirmed only
              </Button>
            </div>
            <div className="flex items-end">
              <Button type="button" variant={statusFilter === "refunded" ? "default" : "outline"} onClick={() => setStatusFilter("refunded")}>
                Refunded only
              </Button>
            </div>
            <div className="flex items-end">
              <Button type="button" variant={statusFilter === "pending" ? "default" : "outline"} onClick={() => setStatusFilter("pending")}>
                Pending only
              </Button>
            </div>
          </div>

          {filteredPayments.length ? (
            <ScrollArea className="w-full">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Payment</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPayments.map((payment: any) => (
                    <TableRow key={payment.id}>
                      <TableCell>
                        <div className="space-y-1">
                          <p className="font-medium">Payment #{payment.id}</p>
                          <p className="text-xs text-muted-foreground">{payment.invoiceRef ?? payment.txRef ?? "—"}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={toneMap[payment.status] ?? "outline"}>{payment.status}</Badge>
                      </TableCell>
                      <TableCell>{payment.planName ?? payment.planCode ?? "Unmapped"}</TableCell>
                      <TableCell>{payment.provider}</TableCell>
                      <TableCell>{formatMoney(payment.amountUsd ?? payment.amount)}</TableCell>
                      <TableCell>{formatDateTime(payment.paidAt ?? payment.createdAt)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No payments match current filters</EmptyTitle>
                <EmptyDescription>Измените payment status или provider, чтобы увидеть релевантные записи для ручной сверки revenue.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function LogsSection({ logs }: { logs: any }) {
  const counters = logs?.counters ?? null;
  const timeline = logs?.timeline ?? [];
  const criticalEntries = React.useMemo(() => {
    return timeline.filter((entry: any) => isCriticalLogEntry(entry));
  }, [timeline]);
  const pinnedEntries = React.useMemo(() => criticalEntries.slice(0, 3), [criticalEntries]);

  if (!counters && !timeline.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Logs module is empty</CardTitle>
          <CardDescription>Когда logs summary вернёт audit trail и job events, единая лента появится в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Log counters</CardTitle>
            <CardDescription>Краткий срез по объёму источников и severity в общей операторской ленте.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <MetricChip label="Total entries" value={String(counters?.total ?? 0)} />
            <MetricChip label="Audit" value={String(counters?.sources?.audit ?? 0)} />
            <MetricChip label="Job events" value={String(counters?.sources?.job_event ?? 0)} />
            <MetricChip label="Errors" value={String(counters?.severity?.error ?? 0)} />
            <MetricChip label="Warnings" value={String(counters?.severity?.warn ?? 0)} />
            <MetricChip label="Critical entries" value={String(criticalEntries.length)} />
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Pinned critical events</CardTitle>
            <CardDescription>Быстрый верхний срез по error и denied/failure событиям, требующим внимания владельца.</CardDescription>
          </CardHeader>
          <CardContent>
            {pinnedEntries.length ? (
              <div className="space-y-3">
                {pinnedEntries.map((entry: any) => (
                  <div key={`pinned-${entry.id}`} className="rounded-xl border border-red-200 bg-red-50/70 p-4 dark:border-red-900/50 dark:bg-red-950/20">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="destructive">critical</Badge>
                          <Badge variant="outline">{entry.source}</Badge>
                          <Badge variant={toneMap[entry.severity] ?? "outline"}>{entry.severity}</Badge>
                        </div>
                        <p className="font-medium">{entry.title}</p>
                        <p className="text-sm text-muted-foreground">{entry.message}</p>
                      </div>
                      <div className="text-right text-xs text-muted-foreground">
                        <p>{formatDateTime(entry.createdAt)}</p>
                        <p>{entry.resourceType} · {entry.resourceId}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No critical events</EmptyTitle>
                  <EmptyDescription>Сейчас в общей ленте нет error/failure/denied событий, требующих отдельного закрепления.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>

      <LogChatPanel
        timeline={timeline}
        title="Operator log chat"
        description="Хронологическая лента audit и job events со всеми доступными логами текущего безопасного контура."
      />
    </section>
  );
}

function LogChatSection({ logs }: { logs: any }) {
  const timeline = logs?.timeline ?? [];

  if (!timeline.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>All logs chat is empty</CardTitle>
          <CardDescription>Когда logs summary вернёт данные, здесь появится отдельный полноформатный чат со всеми логами.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <LogChatPanel
      timeline={timeline}
      title="All logs chat"
      description="Отдельный read-only поток со всеми доступными audit, job и системными логами текущего контура."
      standalone
    />
  );
}

function LogChatPanel({
  timeline,
  title,
  description,
  standalone = false,
}: {
  timeline: any[];
  title: string;
  description: string;
  standalone?: boolean;
}) {
  const [sourceFilter, setSourceFilter] = React.useState<string>("all");
  const [severityFilter, setSeverityFilter] = React.useState<string>("all");
  const [criticalOnly, setCriticalOnly] = React.useState(false);
  const [searchValue, setSearchValue] = React.useState("");

  const sourceOptions = React.useMemo<string[]>(() => {
    return Array.from(new Set<string>(timeline.map((entry: any) => String(entry.source ?? "unknown")))).sort((a, b) => a.localeCompare(b));
  }, [timeline]);

  const filteredTimeline = React.useMemo(() => {
    const normalizedSearch = searchValue.trim().toLowerCase();

    return timeline.filter((entry: any) => {
      const matchesSource = sourceFilter === "all" ? true : String(entry.source ?? "unknown") === sourceFilter;
      const matchesSeverity = severityFilter === "all" ? true : String(entry.severity ?? "info") === severityFilter;
      const matchesCritical = criticalOnly ? isCriticalLogEntry(entry) : true;
      const searchable = [
        entry.title,
        entry.message,
        entry.resourceType,
        entry.resourceId,
        entry.actorLabel,
        entry.source,
        entry.status,
        safeJson(entry.details),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matchesSearch = normalizedSearch ? searchable.includes(normalizedSearch) : true;
      return matchesSource && matchesSeverity && matchesCritical && matchesSearch;
    });
  }, [criticalOnly, searchValue, severityFilter, sourceFilter, timeline]);

  return (
    <Card className="border-0 shadow-sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Visible now: {filteredTimeline.length}</Badge>
            <Badge variant="outline">Total stream: {timeline.length}</Badge>
            {standalone ? <Badge variant="outline">Read only</Badge> : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-[1.1fr_0.8fr_0.8fr_auto]">
          <div className="space-y-2">
            <Label htmlFor={standalone ? "all-logs-search" : "logs-search"}>Search</Label>
            <Input
              id={standalone ? "all-logs-search" : "logs-search"}
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="title, message, resource, actor"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor={standalone ? "all-logs-source-filter" : "logs-source-filter"}>Source</Label>
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger id={standalone ? "all-logs-source-filter" : "logs-source-filter"}>
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                {sourceOptions.map((source: string) => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor={standalone ? "all-logs-severity-filter" : "logs-severity-filter"}>Severity</Label>
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger id={standalone ? "all-logs-severity-filter" : "logs-severity-filter"}>
                <SelectValue placeholder="All severities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All severities</SelectItem>
                <SelectItem value="error">error</SelectItem>
                <SelectItem value="warn">warn</SelectItem>
                <SelectItem value="info">info</SelectItem>
                <SelectItem value="debug">debug</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button type="button" variant={criticalOnly ? "default" : "outline"} onClick={() => setCriticalOnly(current => !current)}>
              Critical only
            </Button>
          </div>
        </div>

        {filteredTimeline.length ? (
          <ScrollArea className={standalone ? "h-[70vh] pr-3" : "max-h-[70vh] pr-3"}>
            <div className="space-y-3">
              {filteredTimeline.map((entry: any) => (
                <div key={entry.id} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{entry.source}</Badge>
                        <Badge variant={toneMap[entry.severity] ?? "outline"}>{entry.severity}</Badge>
                        {entry.status ? <Badge variant={toneMap[entry.status] ?? "outline"}>{entry.status}</Badge> : null}
                        {isCriticalLogEntry(entry) ? <Badge variant="destructive">critical</Badge> : null}
                      </div>
                      <p className="font-medium">{entry.title}</p>
                      <p className="text-sm text-muted-foreground">{entry.message}</p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <p>{formatDateTime(entry.createdAt)}</p>
                      <p>{entry.resourceType} · {entry.resourceId}</p>
                      <p>{entry.actorLabel ?? "system"}</p>
                    </div>
                  </div>
                  {entry.ipAddress ? <p className="mt-3 text-xs text-muted-foreground">IP {entry.ipAddress}</p> : null}
                  {entry.details ? (
                    <pre className="mt-3 overflow-x-auto rounded-lg border bg-background/80 p-3 text-xs text-muted-foreground">{safeJson(entry.details)}</pre>
                  ) : null}
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>No logs match the current filters</EmptyTitle>
              <EmptyDescription>Измените search, source, severity или отключите critical-only режим, чтобы вернуть скрытые записи в поток.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </CardContent>
    </Card>
  );
}

function isCriticalLogEntry(entry: any) {
  return entry?.severity === "error" || entry?.status === "failure" || entry?.status === "denied";
}

function TelemetrySection({ telemetry }: { telemetry: any }) {
  const health = (telemetry?.health ?? null) as HealthSnapshot | null;
  const recentAudit = telemetry?.recentAudit ?? [];
  const counts = telemetry?.jobStatusCounts ?? {};

  const queueEntries = React.useMemo(() => {
    return Object.entries(health?.queues ?? {}).map(([queueName, snapshot]) => ({
      queueName,
      depth: Number((snapshot as any)?.depth ?? 0),
      lagSeconds: Number((snapshot as any)?.lagSeconds ?? 0),
    }));
  }, [health]);

  const providerEntries = React.useMemo(() => {
    const rawProviders = health?.providers;
    if (Array.isArray(rawProviders)) {
      return rawProviders.map((provider: any, index: number) => ({
        key: String(provider?.code ?? provider?.name ?? `provider-${index}`),
        code: String(provider?.code ?? provider?.name ?? `provider-${index}`),
        status: String(provider?.status ?? "unknown"),
        successRate: typeof provider?.successRate === "number" ? provider.successRate : undefined,
        leaseP95Ms: typeof provider?.leaseP95Ms === "number" ? provider.leaseP95Ms : undefined,
      }));
    }

    return Object.entries(rawProviders ?? {}).map(([code, provider]) => ({
      key: code,
      code,
      status: String((provider as any)?.status ?? "unknown"),
      successRate: typeof (provider as any)?.successRate === "number" ? (provider as any).successRate : undefined,
      leaseP95Ms: typeof (provider as any)?.leaseP95Ms === "number" ? (provider as any).leaseP95Ms : undefined,
    }));
  }, [health]);

  const problematicQueues = React.useMemo(() => {
    return queueEntries
      .filter((queue) => queue.depth > 0 || queue.lagSeconds > 0)
      .sort((left, right) => right.lagSeconds - left.lagSeconds || right.depth - left.depth)
      .slice(0, 3);
  }, [queueEntries]);

  const problematicProviders = React.useMemo(() => {
    return providerEntries
      .filter((provider) => provider.status !== "healthy" || (typeof provider.successRate === "number" && provider.successRate < 0.97))
      .sort((left, right) => {
        const leftPenalty = (left.status === "healthy" ? 0 : 1) + (typeof left.successRate === "number" ? 1 - left.successRate : 0);
        const rightPenalty = (right.status === "healthy" ? 0 : 1) + (typeof right.successRate === "number" ? 1 - right.successRate : 0);
        return rightPenalty - leftPenalty;
      })
      .slice(0, 3);
  }, [providerEntries]);

  const incidentAudit = React.useMemo(() => {
    return recentAudit.filter((entry: any) => entry?.status === "failure" || entry?.status === "denied").slice(0, 3);
  }, [recentAudit]);

  return (
    <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Health counters</CardTitle>
            <CardDescription>Queue, provider and worker counters from telemetry summary.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <MetricChip label="Platform status" value={String(health?.status ?? "Unknown")} />
            <MetricChip label="Total jobs" value={String(counts.total ?? 0)} />
            <MetricChip label="Succeeded" value={String(counts.succeeded ?? 0)} />
            <MetricChip label="Failed jobs" value={String(counts.failed ?? 0)} />
            <MetricChip label="Running jobs" value={String(counts.running ?? 0)} />
            <MetricChip label="Canceled jobs" value={String(counts.canceled ?? 0)} />
            <MetricChip label="Waiting retry" value={String(counts.waiting_retry ?? 0)} />
            <MetricChip label="Workers healthy" value={String(health?.workers?.healthy ?? 0)} />
            <MetricChip label="Problem queues" value={String(problematicQueues.length)} />
            <MetricChip label="Problem providers" value={String(problematicProviders.length)} />
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Telemetry incidents</CardTitle>
            <CardDescription>Быстрый incident-focused срез по очередям, провайдерам и недавним failure/denied audit-событиям.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium">Problem queues</p>
                {problematicQueues.length ? (
                  <div className="mt-2 space-y-2">
                    {problematicQueues.map((queue) => (
                      <div key={`queue-${queue.queueName}`} className="rounded-xl border bg-muted/20 p-3 text-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{queue.queueName}</span>
                          <Badge variant="outline">Depth {queue.depth}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">Lag {queue.lagSeconds}s</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">No queue incidents right now.</p>
                )}
              </div>

              <div>
                <p className="text-sm font-medium">Problem providers</p>
                {problematicProviders.length ? (
                  <div className="mt-2 space-y-2">
                    {problematicProviders.map((provider) => (
                      <div key={`provider-${provider.key}`} className="rounded-xl border bg-muted/20 p-3 text-sm">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{provider.code}</span>
                          <Badge variant={toneMap[provider.status] ?? "outline"}>{provider.status}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Success {formatPercent(provider.successRate)} · Lease p95 {typeof provider.leaseP95Ms === "number" ? `${provider.leaseP95Ms}ms` : "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">No provider incidents right now.</p>
                )}
              </div>

              <div>
                <p className="text-sm font-medium">Denied or failed audit</p>
                {incidentAudit.length ? (
                  <div className="mt-2 space-y-2">
                    {incidentAudit.map((entry: any) => (
                      <div key={`incident-${entry.action}-${entry.resourceId}-${entry.createdAt}`} className="rounded-xl border bg-red-50/60 p-3 text-sm dark:bg-red-950/20">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium">{entry.action}</span>
                          <Badge variant="destructive">{entry.status}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{entry.resourceType} · {entry.resourceId}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">No denied or failed audit entries in the latest telemetry slice.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Recent audit trail</CardTitle>
          <CardDescription>Последние audit-события из telemetry summary.</CardDescription>
        </CardHeader>
        <CardContent>
          {recentAudit.length ? (
            <div className="space-y-3">
              {recentAudit.map((entry: any) => (
                <div key={`${entry.action}-${entry.resourceId}-${entry.createdAt}`} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{entry.action}</p>
                      <p className="text-xs text-muted-foreground">{entry.resourceType} · {entry.resourceId}</p>
                    </div>
                    <Badge variant={toneMap[entry.status] ?? "outline"}>{entry.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No telemetry audit yet</EmptyTitle>
                <EmptyDescription>События появятся здесь, когда telemetry-модуль вернёт данные.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function SystemSection({ system }: { system: any }) {
  const scenarios = system?.safeTestScenarios ?? [];
  const checklist = system?.stabilizationChecklist ?? [];
  const readinessSnapshot = system?.readinessSnapshot ?? [];
  const rolloutRunbook = system?.rolloutRunbook ?? [];
  const rollbackRunbook = system?.rollbackRunbook ?? [];

  if (!scenarios.length && !checklist.length && !readinessSnapshot.length && !rolloutRunbook.length && !rollbackRunbook.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>System module is empty</CardTitle>
          <CardDescription>Когда system summary вернёт safe scenarios, readiness и checklist, они появятся в этом разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Readiness snapshot</CardTitle>
            <CardDescription>Краткая операторская оценка того, какие системные контуры уже готовы, а какие ещё требуют закрытия.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {readinessSnapshot.length ? (
              readinessSnapshot.map((item: any) => (
                <div key={item.code} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.code}</p>
                    </div>
                    <Badge variant={toneMap[item.status] ?? "outline"}>{item.status}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{item.detail}</p>
                </div>
              ))
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No readiness snapshot yet</EmptyTitle>
                  <EmptyDescription>Readiness signals появятся здесь, когда system summary вернёт статус по ключевым operational gate.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Stabilization checklist</CardTitle>
            <CardDescription>Оставшиеся системные требования для перехода к production-grade контуру.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {checklist.length ? (
              checklist.map((item: string) => (
                <div key={item} className="rounded-xl border bg-muted/20 p-4 text-sm text-muted-foreground">
                  {item}
                </div>
              ))
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No checklist items yet</EmptyTitle>
                  <EmptyDescription>Checklist появится после публикации system stabilization requirements.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Safe test scenarios</CardTitle>
            <CardDescription>Доступные безопасные сценарии для операторской регрессии.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {scenarios.length ? (
              scenarios.map((scenario: any) => (
                <div key={scenario.code} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{scenario.title}</p>
                      <p className="text-xs text-muted-foreground">{scenario.code}</p>
                    </div>
                    <Badge variant="secondary">Safe</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{scenario.description}</p>
                </div>
              ))
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No safe scenarios yet</EmptyTitle>
                  <EmptyDescription>Safe scenarios появятся после публикации очередного safe test pack.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Rollout runbook</CardTitle>
              <CardDescription>Пошаговый безопасный порядок расширения operator-facing контура.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rolloutRunbook.length ? (
                rolloutRunbook.map((step: string, index: number) => (
                  <div key={`${index}-${step}`} className="rounded-xl border bg-muted/20 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Step {index + 1}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{step}</p>
                  </div>
                ))
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No rollout runbook yet</EmptyTitle>
                    <EmptyDescription>Пошаговый rollout runbook появится здесь после публикации операторских процедур.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Rollback runbook</CardTitle>
              <CardDescription>Минимальный безопасный путь отката при деградации health, логов или критичных operator flows.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rollbackRunbook.length ? (
                rollbackRunbook.map((step: string, index: number) => (
                  <div key={`${index}-${step}`} className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Fallback {index + 1}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{step}</p>
                  </div>
                ))
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No rollback runbook yet</EmptyTitle>
                    <EmptyDescription>Rollback guidance появится, когда system summary начнёт возвращать validated fallback steps.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

function SafeBenchSection({ system }: { system: any }) {
  const scenarios = system?.safeTestScenarios ?? [];
  const readinessSnapshot = system?.readinessSnapshot ?? [];
  const rolloutRunbook = system?.rolloutRunbook ?? [];
  const rollbackRunbook = system?.rollbackRunbook ?? [];

  if (!scenarios.length && !readinessSnapshot.length && !rolloutRunbook.length && !rollbackRunbook.length) {
    return (
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Safe Bench is empty</CardTitle>
          <CardDescription>Когда system summary вернёт safe-test сценарии и gate, они появятся в этом отдельном разделе.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Bench boundary</CardTitle>
            <CardDescription>Safe Bench изолирует безопасные сценарии проверки и не запускает live runtime-мутации.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricChip label="Scenarios" value={String(scenarios.length)} />
            <MetricChip label="Entry gates" value={String(readinessSnapshot.length)} />
            <MetricChip label="Rollout steps" value={String(rolloutRunbook.length)} />
            <MetricChip label="Rollback steps" value={String(rollbackRunbook.length)} />
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Safe test scenarios</CardTitle>
            <CardDescription>Подтверждённые read-only и safe-test сценарии для операторской регрессии.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {scenarios.length ? (
              scenarios.map((scenario: any) => (
                <div key={scenario.code} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{scenario.title}</p>
                      <p className="text-xs text-muted-foreground">{scenario.code}</p>
                    </div>
                    <Badge variant="secondary">Safe</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{scenario.description}</p>
                </div>
              ))
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No safe scenarios yet</EmptyTitle>
                  <EmptyDescription>Safe scenarios появятся после публикации очередного safe test pack.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Bench entry gates</CardTitle>
            <CardDescription>Какие контуры уже допускают безопасную проверку, а какие ещё требуют операторского внимания.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {readinessSnapshot.length ? (
              readinessSnapshot.map((item: any) => (
                <div key={item.code} className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.code}</p>
                    </div>
                    <Badge variant={toneMap[item.status] ?? "outline"}>{item.status}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{item.detail}</p>
                </div>
              ))
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No bench gates yet</EmptyTitle>
                  <EmptyDescription>Gate snapshot появится здесь, когда system summary вернёт validated readiness signals.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Execution guardrails</CardTitle>
              <CardDescription>Порядок безопасного прохода safe-test контура перед любым расширением операторских возможностей.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rolloutRunbook.length ? (
                rolloutRunbook.map((step: string, index: number) => (
                  <div key={`${index}-${step}`} className="rounded-xl border bg-muted/20 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Guardrail {index + 1}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{step}</p>
                  </div>
                ))
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No guardrails yet</EmptyTitle>
                    <EmptyDescription>Guardrails появятся после публикации operator safe-test runbook.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Rollback runbook</CardTitle>
              <CardDescription>Безопасный путь отката и выхода из safe-test контура при первых признаках деградации.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rollbackRunbook.length ? (
                rollbackRunbook.map((step: string, index: number) => (
                  <div key={`${index}-${step}`} className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Fallback {index + 1}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{step}</p>
                  </div>
                ))
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No rollback path yet</EmptyTitle>
                    <EmptyDescription>Rollback guidance появится после публикации validated safe-bench fallback steps.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Quick operator exits</CardTitle>
              <CardDescription>Быстрые read-only переходы в соседние разделы для сверки system, логов и полного журнала событий.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-3">
              <a href="/system" className="rounded-xl border bg-muted/20 p-4 transition-colors hover:bg-muted/40">
                <p className="text-sm font-medium">System</p>
                <p className="mt-2 text-xs text-muted-foreground">Сверить readiness snapshot и stabilization checklist.</p>
              </a>
              <a href="/logs" className="rounded-xl border bg-muted/20 p-4 transition-colors hover:bg-muted/40">
                <p className="text-sm font-medium">Logs</p>
                <p className="mt-2 text-xs text-muted-foreground">Проверить последние audit, job и incident события.</p>
              </a>
              <a href="/log-chat" className="rounded-xl border bg-muted/20 p-4 transition-colors hover:bg-muted/40">
                <p className="text-sm font-medium">All Logs Chat</p>
                <p className="mt-2 text-xs text-muted-foreground">Открыть полный хронологический поток всех операторских логов.</p>
              </a>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-muted/20 p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function BotTextsSection({
  module,
  selectedKey,
  drafts,
  feedback,
  isSaving,
  onSelectedKeyChange,
  onDraftChange,
  onSave,
}: {
  module: any;
  selectedKey: string;
  drafts: Record<string, BotTextDraft>;
  feedback: string | null;
  isSaving: boolean;
  onSelectedKeyChange: (value: string) => void;
  onDraftChange: (field: keyof BotTextDraft, value: string) => void;
  onSave: () => Promise<void>;
}) {
  const texts = module?.texts ?? [];
  const recipients = module?.recipients ?? [];
  const selectedDraft = drafts[selectedKey] ?? { title: "", description: "", body: "" };

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Bot text editor</CardTitle>
          <CardDescription>Выберите шаблон, измените текст и сохраните его без ручного редактирования кода.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!module?.summary?.telegramConfigured ? (
            <Alert>
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Telegram token not configured</AlertTitle>
              <AlertDescription>
                Редактирование шаблонов уже работает, но live-отправка через бота будет недоступна, пока в окружении не настроен BOT_TOKEN.
              </AlertDescription>
            </Alert>
          ) : null}

          {feedback ? (
            <Alert>
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Save status</AlertTitle>
              <AlertDescription>{feedback}</AlertDescription>
            </Alert>
          ) : null}

          {texts.length ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Template key</Label>
                  <Select value={selectedKey} onValueChange={onSelectedKeyChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select bot text" />
                    </SelectTrigger>
                    <SelectContent>
                      {texts.map((text: any) => (
                        <SelectItem key={text.key} value={text.key}>
                          {text.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input value={selectedDraft.title} onChange={event => onDraftChange("title", event.target.value)} />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={selectedDraft.description}
                  onChange={event => onDraftChange("description", event.target.value)}
                  placeholder="Краткое описание, где этот шаблон используется"
                />
              </div>

              <div className="space-y-2">
                <Label>Body</Label>
                <Textarea
                  value={selectedDraft.body}
                  onChange={event => onDraftChange("body", event.target.value)}
                  className="min-h-[260px]"
                  placeholder="Введите текст, который бот должен отправлять пользователю"
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-muted/20 p-4">
                <div>
                  <p className="text-sm font-medium">Template rollout</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    После сохранения шаблон останется доступным в backend и журнале аудита без отдельного деплоя интерфейса.
                  </p>
                </div>
                <Button onClick={() => void onSave()} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save template"}
                </Button>
              </div>
            </>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No templates loaded</EmptyTitle>
                <EmptyDescription>Шаблоны появятся здесь после ответа botTexts-модуля.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Delivery summary</CardTitle>
            <CardDescription>Кому потенциально могут уходить тексты и насколько готов Telegram-контур.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Templates</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">{module?.summary?.totalTemplates ?? 0}</p>
            </div>
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Recipients</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">{module?.summary?.activeRecipients ?? 0}</p>
            </div>
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Telegram</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">
                {module?.summary?.telegramConfigured ? "Configured" : "Missing"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Telegram recipients</CardTitle>
            <CardDescription>Связанные chatId, которые можно использовать для операторских broadcast-сценариев.</CardDescription>
          </CardHeader>
          <CardContent>
            {recipients.length ? (
              <ScrollArea className="h-[360px] rounded-xl border bg-muted/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Bot label</TableHead>
                      <TableHead>Chat ID</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recipients.map((recipient: any) => (
                      <TableRow key={recipient.id ?? recipient.chatId}>
                        <TableCell>{recipient.botLabel}</TableCell>
                        <TableCell className="font-mono text-xs">{recipient.chatId}</TableCell>
                        <TableCell>
                          <Badge variant={toneMap[recipient.status] ?? "outline"}>{recipient.status}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No Telegram recipients</EmptyTitle>
                  <EmptyDescription>
                    Пока нет активных chatId. Для live-рассылок добавьте получателей в telegramEndpoints или используйте manual chat IDs.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function BroadcastsSection({
  module,
  draft,
  feedback,
  isSubmitting,
  lastResult,
  onDraftChange,
  onCreate,
}: {
  module: any;
  draft: BroadcastDraft;
  feedback: string | null;
  isSubmitting: boolean;
  lastResult: any;
  onDraftChange: (field: keyof BroadcastDraft, value: string) => void;
  onCreate: (dryRun: boolean) => Promise<void>;
}) {
  const history = module?.history ?? [];
  const recipients = module?.recipients ?? [];

  return (
    <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Broadcast composer</CardTitle>
          <CardDescription>Подготовьте рассылку, прогоните dry run и затем выполните live-отправку из админки.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!module?.summary?.telegramConfigured ? (
            <Alert>
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Live delivery is blocked</AlertTitle>
              <AlertDescription>
                BOT_TOKEN не настроен. Dry run можно выполнять уже сейчас, но реальная Telegram-рассылка будет заблокирована до настройки секрета.
              </AlertDescription>
            </Alert>
          ) : null}

          {feedback ? (
            <Alert>
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Broadcast status</AlertTitle>
              <AlertDescription>{feedback}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Title</Label>
              <Input value={draft.title} onChange={event => onDraftChange("title", event.target.value)} placeholder="Например, Maintenance notice" />
            </div>
            <div className="space-y-2">
              <Label>Audience</Label>
              <Select value={draft.audience} onValueChange={value => onDraftChange("audience", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select audience" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="linked_telegram_users">Linked Telegram users</SelectItem>
                  <SelectItem value="manual_chat_ids">Manual chat IDs</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Message</Label>
            <Textarea
              value={draft.message}
              onChange={event => onDraftChange("message", event.target.value)}
              className="min-h-[220px]"
              placeholder="Введите текст рассылки, который должен уйти в Telegram"
            />
          </div>

          {draft.audience === "manual_chat_ids" ? (
            <div className="space-y-2">
              <Label>Manual chat IDs</Label>
              <Textarea
                value={draft.manualChatIds}
                onChange={event => onDraftChange("manualChatIds", event.target.value)}
                className="min-h-[120px]"
                placeholder="Один chat ID на строку или через запятую"
              />
            </div>
          ) : (
            <div className="rounded-2xl border bg-muted/20 p-4">
              <p className="text-sm font-medium">Linked delivery mode</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Для live-режима будут использованы активные chatId из telegramEndpoints. Сейчас доступно {recipients.length} получателей.
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={() => void onCreate(true)} disabled={isSubmitting}>
              {isSubmitting ? "Processing..." : "Run dry run"}
            </Button>
            <Button
              onClick={() => void onCreate(false)}
              disabled={
                isSubmitting ||
                !draft.title.trim() ||
                !draft.message.trim() ||
                (!module?.summary?.telegramConfigured && draft.audience === "linked_telegram_users")
              }
            >
              {isSubmitting ? "Sending..." : "Send broadcast"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Broadcast summary</CardTitle>
            <CardDescription>Короткий срез по истории запусков и связанным получателям.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">History</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">{module?.summary?.totalBroadcasts ?? 0}</p>
            </div>
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Linked recipients</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">{module?.summary?.linkedRecipients ?? 0}</p>
            </div>
            <div className="rounded-xl border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">Telegram</p>
              <p className="mt-2 text-xl font-semibold tracking-tight">
                {module?.summary?.telegramConfigured ? "Configured" : "Missing"}
              </p>
            </div>
          </CardContent>
        </Card>

        {lastResult ? (
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Last run result</CardTitle>
              <CardDescription>Последний запуск из текущей сессии с разбивкой по каждому получателю.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[220px] rounded-xl border bg-muted/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Mode</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(lastResult.results ?? []).map((result: any) => (
                      <TableRow key={`${result.chatId}-${result.label}`}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium">{result.label}</p>
                            <p className="font-mono text-xs text-muted-foreground">{result.chatId}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={result.ok ? "secondary" : "destructive"}>
                            {result.ok ? "Delivered" : "Failed"}
                          </Badge>
                        </TableCell>
                        <TableCell>{result.simulated ? "Dry run" : "Live"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        ) : null}

        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle>Broadcast history</CardTitle>
            <CardDescription>История запусков, чтобы быстро понимать, что уже отправлялось и с каким результатом.</CardDescription>
          </CardHeader>
          <CardContent>
            {history.length ? (
              <ScrollArea className="h-[320px] rounded-xl border bg-muted/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Recipients</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((item: any) => (
                      <TableRow key={item.publicId}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium">{item.title}</p>
                            <p className="text-xs text-muted-foreground">{item.dryRun ? "Dry run" : "Live"}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={toneMap[item.status] ?? "outline"}>{item.status}</Badge>
                        </TableCell>
                        <TableCell>
                          {item.deliveredCount}/{item.requestedRecipients}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            ) : (
              <Empty>
                <EmptyHeader>
                  <EmptyTitle>No broadcasts yet</EmptyTitle>
                  <EmptyDescription>История появится после первого dry run или live-отправки.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export function resolvePageKey(pathname: string): PageKey {
  if (pathname.startsWith("/proxy")) return "proxy";
  if (pathname.startsWith("/workers")) return "workers";
  if (pathname.startsWith("/billing")) return "billing";
  if (pathname.startsWith("/revenue")) return "revenue";
  if (pathname.startsWith("/log-chat")) return "logchat";
  if (pathname.startsWith("/logs")) return "logs";
  if (pathname.startsWith("/metrics") || pathname.startsWith("/telemetry")) return "telemetry";
  if (pathname.startsWith("/safe-bench")) return "safebench";
  if (pathname.startsWith("/system")) return "system";
  if (pathname.startsWith("/bot-texts")) return "bottexts";
  if (pathname.startsWith("/broadcasts")) return "broadcasts";
  return "jobs";
}

function formatPercent(input?: number) {
  if (typeof input !== "number" || Number.isNaN(input)) {
    return "—";
  }

  return `${(input * 100).toFixed(1)}%`;
}

function formatMoney(input: unknown) {
  const numeric = typeof input === "number" ? input : typeof input === "string" ? Number(input) : NaN;
  if (Number.isNaN(numeric)) {
    return "—";
  }

  return `$${numeric.toFixed(2)}`;
}

function formatDateTime(value: unknown) {
  if (!value) {
    return "—";
  }

  const date = value instanceof Date ? value : new Date(String(value));
  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleString();
}

function safeJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
