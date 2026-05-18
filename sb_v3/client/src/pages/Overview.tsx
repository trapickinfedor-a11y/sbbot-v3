import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import DashboardLayout from "@/components/DashboardLayout";
import { trpc } from "@/lib/trpc";
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  Clock3,
  DatabaseZap,
  DollarSign,
  Gauge,
  ShieldCheck,
  Waypoints,
} from "lucide-react";
import React, { type ComponentType } from "react";
import { Link } from "wouter";

const statusToneMap: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  healthy: "secondary",
  degraded: "outline",
  disabled: "destructive",
  running: "secondary",
  succeeded: "secondary",
  waiting_retry: "outline",
  failed: "destructive",
  canceled: "outline",
  offline: "destructive",
  maintenance: "outline",
};

type HealthSnapshot = {
  status?: string;
  queues?: Record<string, { depth: number; lagSeconds: number }>;
  providers?: Record<string, { status?: string; successRate?: number; avgLeaseMs?: number }>;
};

export default function Overview() {
  const overviewQuery = trpc.platform.overview.useQuery();
  const telemetryQuery = trpc.telemetry.summary.useQuery();
  const jobsQuery = trpc.jobs.list.useQuery();
  const proxyQuery = trpc.proxies.summary.useQuery();
  const workersQuery = trpc.workers.summary.useQuery();
  const billingQuery = trpc.billing.summary.useQuery();

  const isLoading = [overviewQuery, telemetryQuery, jobsQuery, proxyQuery, workersQuery, billingQuery].some(
    query => query.isLoading,
  );

  const firstError = [overviewQuery, telemetryQuery, jobsQuery, proxyQuery, workersQuery, billingQuery].find(
    query => query.error,
  )?.error;

  const metrics = overviewQuery.data?.metrics ?? [];
  const healthData = (telemetryQuery.data?.health ?? overviewQuery.data?.health ?? null) as HealthSnapshot | null;
  const recentAudit = telemetryQuery.data?.recentAudit ?? overviewQuery.data?.auditTrail ?? [];
  const jobs = jobsQuery.data ?? [];
  const providers = proxyQuery.data?.providers ?? [];
  const workers = workersQuery.data?.workers ?? [];
  const plans = billingQuery.data?.plans ?? [];
  const payments = billingQuery.data?.payments ?? [];
  const subscriptions = billingQuery.data?.subscriptions ?? [];
  const scenarios = overviewQuery.data?.safeTestScenarios ?? [];

  const queueEntries = healthData?.queues ? Object.entries(healthData.queues) : [];
  const providerEntries = healthData?.providers ? Object.entries(healthData.providers) : [];
  const failedJobs = jobs.filter(job => job.status === "failed").length;
  const retryingJobs = jobs.filter(job => job.status === "waiting_retry").length;
  const deniedAudit = recentAudit.filter(entry => entry.status === "denied").length;
  const criticalLogPath = failedJobs > 0 || retryingJobs > 0 ? "/log-chat" : "/logs";
  const incidentStatus = failedJobs > 0 ? "Attention required" : retryingJobs > 0 || deniedAudit > 0 ? "Monitor closely" : "Stable";
  const incidentSummary = [
    { label: "Failed jobs", value: String(failedJobs) },
    { label: "Waiting retry", value: String(retryingJobs) },
    { label: "Denied audit", value: String(deniedAudit) },
  ];
  const quickLinks = [
    {
      title: "Logs",
      description: "Сводка counters, critical entries и быстрый аудит последних событий.",
      path: "/logs",
    },
    {
      title: "All Logs Chat",
      description: "Полный read-only поток всех log events для сквозного просмотра инцидентов.",
      path: "/log-chat",
    },
    {
      title: "Metrics",
      description: "Health counters, queue posture и incident-focused telemetry обзор.",
      path: "/metrics",
    },
    {
      title: "System",
      description: "Readiness snapshot, rollback runbook и safe scenario posture.",
      path: "/system",
    },
    {
      title: "Safe Bench",
      description: "Безопасный тестовый контур и сценарии операционной проверки без внешнего runtime.",
      path: "/safe-bench",
    },
  ];
  const laggingQueues = queueEntries.filter(([, queue]) => queue.lagSeconds > 20);
  const actionQueue = [
    failedJobs > 0
      ? {
          title: "Investigate failed jobs",
          detail: `${failedJobs} job(s) already failed and should be reviewed in the full log stream before any next operator action.`,
          path: "/log-chat",
          cta: "Open All Logs Chat",
          priority: "Critical" as const,
        }
      : null,
    retryingJobs > 0
      ? {
          title: "Review retry backlog",
          detail: `${retryingJobs} job(s) are waiting for retry, so queue posture and recent telemetry should be checked before escalation.`,
          path: "/metrics",
          cta: "Open Metrics",
          priority: "High" as const,
        }
      : null,
    deniedAudit > 0
      ? {
          title: "Confirm denied audit events",
          detail: `${deniedAudit} denied audit event(s) need a quick policy and readiness check in the system module.`,
          path: "/system",
          cta: "Open System",
          priority: "High" as const,
        }
      : null,
    laggingQueues.length > 0
      ? {
          title: "Track queue lag before it grows",
          detail: `${laggingQueues.length} queue(s) already exceed the lag guardrail and should be checked from the telemetry view.`,
          path: "/metrics",
          cta: "Inspect queue lag",
          priority: "Medium" as const,
        }
      : null,
  ].filter(
    (
      item,
    ): item is {
      title: string;
      detail: string;
      path: string;
      cta: string;
      priority: "Critical" | "High" | "Medium";
    } => item !== null,
  );

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-2xl tracking-tight">Platform overview</CardTitle>
                  <CardDescription>
                    Операционный обзор текущего состояния CSBot Admin System по уже реализованным backend-модулям:
                    jobs, proxy, workers, billing, telemetry и safe test bench.
                  </CardDescription>
                </div>
                <Badge variant="secondary" className="gap-1.5 px-3 py-1 text-xs">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Safe operations only
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {firstError ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Overview data error</AlertTitle>
                  <AlertDescription>{firstError.message}</AlertDescription>
                </Alert>
              ) : null}

              <Alert>
                <DatabaseZap className="h-4 w-4" />
                <AlertTitle>Current implementation boundary</AlertTitle>
                <AlertDescription>
                  Эта панель отражает только уже реализованный и безопасный поднабор платформы. Она помогает увидеть,
                  какие контуры действительно доступны сейчас, не подменяя собой ещё не завершённые модули.
                </AlertDescription>
              </Alert>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {(isLoading ? new Array(4).fill(null) : metrics).map((metric, index) => (
                  <div key={metric?.key ?? `metric-skeleton-${index}`} className="rounded-2xl border bg-muted/30 p-4">
                    {metric ? (
                      <>
                        <p className="text-sm text-muted-foreground">{metric.title}</p>
                        <p className="mt-2 text-2xl font-semibold tracking-tight">{metric.value}</p>
                        <p className="mt-2 text-xs text-muted-foreground">{metric.delta ?? "No delta available"}</p>
                      </>
                    ) : (
                      <div className="space-y-3">
                        <div className="h-4 w-24 rounded bg-muted" />
                        <div className="h-8 w-20 rounded bg-muted" />
                        <div className="h-3 w-32 rounded bg-muted" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>System health snapshot</CardTitle>
              <CardDescription>
                Быстрый health-срез по очередям, прокси-провайдерам и worker-контру для безопасной операторской оценки.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <StatusTile
                  icon={Activity}
                  label="Platform status"
                  value={String(healthData?.status ?? (isLoading ? "Loading" : "Unknown"))}
                />
                <StatusTile
                  icon={Gauge}
                  label="Success rate"
                  value={formatPercent(telemetryQuery.data?.successRate)}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Waypoints className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">Queue health</h3>
                </div>
                {queueEntries.length ? (
                  <div className="space-y-3">
                    {queueEntries.map(([queueName, queue]) => (
                      <div key={queueName} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="font-medium capitalize">{queueName}</p>
                            <p className="text-xs text-muted-foreground">
                              Depth {queue.depth} · Lag {queue.lagSeconds}s
                            </p>
                          </div>
                          <Badge variant={queue.lagSeconds > 20 ? "outline" : "secondary"}>{queue.lagSeconds}s</Badge>
                        </div>
                        <Progress value={Math.min((queue.lagSeconds / 40) * 100, 100)} className="mt-3 h-2" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>No queue data</EmptyTitle>
                      <EmptyDescription>Очереди появятся здесь после загрузки telemetry-модуля.</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-medium">Provider health</h3>
                </div>
                {providerEntries.length ? (
                  <div className="space-y-3">
                    {providerEntries.map(([providerCode, provider]) => (
                      <div key={providerCode} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="font-medium">{providerCode}</p>
                            <p className="text-xs text-muted-foreground">
                              Success {formatPercent(provider.successRate)} · Avg lease {provider.avgLeaseMs} ms
                            </p>
                          </div>
                          <Badge variant={statusToneMap[String(provider.status)] ?? "outline"}>{provider.status}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>No provider health</EmptyTitle>
                      <EmptyDescription>Данные health по провайдерам появятся после загрузки proxy-модуля.</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Operator incident snapshot</CardTitle>
              <CardDescription>
                Быстрый срез по сбоям, retry-сигналам и audit-ограничениям, чтобы оператор мог сразу перейти в нужный модуль.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="rounded-2xl border bg-muted/20 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">Current posture</p>
                    <p className="mt-2 text-2xl font-semibold tracking-tight">{incidentStatus}</p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {failedJobs > 0
                        ? "Есть сбойные задания: полный поток уже доступен в отдельном All Logs Chat."
                        : retryingJobs > 0 || deniedAudit > 0
                          ? "Критических failure сейчас нет, но есть сигналы, требующие операторского внимания."
                          : "Сейчас контур выглядит стабильным: можно перейти к деталям через профильные разделы."}
                    </p>
                  </div>
                  <Badge variant={failedJobs > 0 ? "destructive" : retryingJobs > 0 || deniedAudit > 0 ? "outline" : "secondary"}>
                    {failedJobs > 0 ? "Escalate" : retryingJobs > 0 || deniedAudit > 0 ? "Observe" : "Stable"}
                  </Badge>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {incidentSummary.map(item => (
                  <div key={item.label} className="rounded-2xl border bg-background p-4">
                    <p className="text-sm text-muted-foreground">{item.label}</p>
                    <p className="mt-2 text-2xl font-semibold tracking-tight">{item.value}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium">Operator action queue</h3>
                  <Badge
                    variant={
                      actionQueue.length === 0 ? "secondary" : failedJobs > 0 ? "destructive" : "outline"
                    }
                  >
                    {actionQueue.length === 0 ? "Clear" : `${actionQueue.length} active`}
                  </Badge>
                </div>
                {actionQueue.length ? (
                  <div className="space-y-3">
                    {actionQueue.map(action => (
                      <div key={`${action.title}-${action.path}`} className="rounded-2xl border bg-background p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge
                                variant={
                                  action.priority === "Critical"
                                    ? "destructive"
                                    : action.priority === "High"
                                      ? "outline"
                                      : "secondary"
                                }
                              >
                                {action.priority}
                              </Badge>
                              <p className="font-medium">{action.title}</p>
                            </div>
                            <p className="text-sm text-muted-foreground">{action.detail}</p>
                          </div>
                          <Link href={action.path}>
                            <Button variant="outline" size="sm">{action.cta}</Button>
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl border bg-muted/20 p-4">
                    <p className="text-sm font-medium">No immediate actions</p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      В текущем read-only срезе нет сигналов, требующих немедленного перехода. Оператор может перейти к
                      профильным разделам через быстрые переходы ниже.
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-medium">Quick operator jumps</h3>
                  <Link href={criticalLogPath}>
                    <Button variant="outline" size="sm">Open live log focus</Button>
                  </Link>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {quickLinks.map(link => (
                    <Link key={`${link.title}-${link.path}`} href={link.path}>
                      <div className="rounded-2xl border bg-muted/20 p-4 transition-colors hover:bg-muted/40">
                        <p className="font-medium">{link.title}</p>
                        <p className="mt-2 text-sm text-muted-foreground">{link.description}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card className="border-0 shadow-sm">
              <CardHeader>
                <CardTitle>Recent jobs</CardTitle>
                <CardDescription>
                  Последние задания из jobs-модуля с их режимом, источником и текущим состоянием.
                </CardDescription>
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
                          <TableHead>Queue</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {jobs.slice(0, 6).map(job => (
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
                              <Badge variant={statusToneMap[job.status] ?? "outline"}>{job.status}</Badge>
                            </TableCell>
                            <TableCell>
                              {((job.resultJson as {
                                oneCsResult?: {
                                  creditScore?: number | null;
                                  productScore: number;
                                  dataQualityScore: number;
                                  status: string;
                                };
                              } | null)?.oneCsResult) ? (
                                <div className="space-y-1 text-xs">
                                  <div className="flex flex-wrap gap-1.5">
                                    <Badge variant="secondary">
                                      CS {((job.resultJson as {
                                        oneCsResult?: {
                                          creditScore?: number | null;
                                          productScore: number;
                                          dataQualityScore: number;
                                          status: string;
                                        };
                                      } | null)?.oneCsResult?.creditScore ?? "—")}
                                    </Badge>
                                    <Badge variant="outline">
                                      P {((job.resultJson as {
                                        oneCsResult?: {
                                          creditScore?: number | null;
                                          productScore: number;
                                          dataQualityScore: number;
                                          status: string;
                                        };
                                      } | null)?.oneCsResult?.productScore ?? "—")}/20
                                    </Badge>
                                    <Badge variant="outline">
                                      Q {((job.resultJson as {
                                        oneCsResult?: {
                                          creditScore?: number | null;
                                          productScore: number;
                                          dataQualityScore: number;
                                          status: string;
                                        };
                                      } | null)?.oneCsResult?.dataQualityScore ?? "—")}/10
                                    </Badge>
                                  </div>
                                  <p className="capitalize text-muted-foreground">
                                    {String((job.resultJson as {
                                      oneCsResult?: {
                                        creditScore?: number | null;
                                        productScore: number;
                                        dataQualityScore: number;
                                        status: string;
                                      };
                                    } | null)?.oneCsResult?.status ?? "unknown").replace(/_/g, " ")}
                                  </p>
                                </div>
                              ) : (
                                <span className="text-xs text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>{job.queueName}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                ) : (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>No jobs loaded</EmptyTitle>
                      <EmptyDescription>Список заданий появится здесь после ответа jobs-модуля.</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </CardContent>
            </Card>

            <Card className="border-0 shadow-sm">
              <CardHeader>
                <CardTitle>Workers and providers</CardTitle>
                <CardDescription>
                  Сводка по инфраструктурному поднабору, уже доступному в mock-safe и backend-слое.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid gap-3 md:grid-cols-2">
                  <StatusTile icon={Clock3} label="Workers" value={String(workers.length)} />
                  <StatusTile icon={DatabaseZap} label="Providers" value={String(providers.length)} />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {workers.slice(0, 4).map(worker => (
                    <div key={worker.code} className="rounded-xl border bg-muted/20 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{worker.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {worker.role} · {worker.hostLabel}
                          </p>
                        </div>
                        <Badge variant={statusToneMap[worker.status] ?? "outline"}>{worker.status}</Badge>
                      </div>
                      <p className="mt-3 text-xs text-muted-foreground">
                        Active jobs {worker.activeJobs} / {worker.concurrencyLimit}
                      </p>
                      <Progress
                        value={worker.concurrencyLimit ? (worker.activeJobs / worker.concurrencyLimit) * 100 : 0}
                        className="mt-2 h-2"
                      />
                    </div>
                  ))}
                </div>

                <div className="rounded-2xl border bg-muted/20 p-4">
                  <p className="text-sm font-medium">Routing posture</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Провайдеры и worker-узлы уже видимы в админке как операторский read-only слой. Это даёт базу для
                    последующей детализации proxy fallback, policy management и execution orchestration.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Billing summary</CardTitle>
              <CardDescription>
                Текущий read-only обзор тарифов, подписок, платежей и usage economics из billing-модуля.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <StatusTile icon={DollarSign} label="Plans" value={String(plans.length)} />
                <StatusTile icon={ShieldCheck} label="Subscriptions" value={String(subscriptions.length)} />
                <StatusTile icon={Activity} label="Payments" value={String(payments.length)} />
              </div>

              {billingQuery.data?.usageSummary ? (
                <div className="rounded-2xl border bg-muted/20 p-4">
                  <p className="text-sm font-medium">Current usage period</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <KeyValue label="Period" value={billingQuery.data.usageSummary.currentPeriod} />
                    <KeyValue label="Requests" value={String(billingQuery.data.usageSummary.requests)} />
                    <KeyValue label="Browser runs" value={String(billingQuery.data.usageSummary.browserRuns)} />
                    <KeyValue label="Proxy traffic" value={`${billingQuery.data.usageSummary.proxyTrafficGb} GB`} />
                    <KeyValue label="Revenue" value={`$${billingQuery.data.usageSummary.revenueUsd}`} />
                    <KeyValue label="Margin" value={`$${billingQuery.data.usageSummary.marginUsd}`} />
                  </div>
                </div>
              ) : null}

              <ScrollArea className="h-[220px] rounded-xl border bg-muted/10">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Plan</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead>Price</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {plans.map(plan => (
                      <TableRow key={plan.code}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium">{plan.name}</p>
                            <p className="text-xs text-muted-foreground">{plan.code}</p>
                          </div>
                        </TableCell>
                        <TableCell className="capitalize">{plan.tier}</TableCell>
                        <TableCell>{plan.currency} {plan.priceUsd}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Recent audit and safe scenarios</CardTitle>
              <CardDescription>
                История последних системных действий и доступные безопасные тестовые сценарии для операторской проверки.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Recent audit trail</h3>
                {recentAudit.length ? (
                  <div className="space-y-3">
                    {recentAudit.slice(0, 5).map(entry => (
                      <div key={`${entry.action}-${entry.resourceId}-${entry.createdAt}`} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{entry.action}</p>
                            <p className="text-xs text-muted-foreground">
                              {entry.resourceType} · {entry.resourceId}
                            </p>
                          </div>
                          <Badge variant="outline">{entry.status}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty>
                    <EmptyHeader>
                      <EmptyTitle>No audit trail yet</EmptyTitle>
                      <EmptyDescription>Когда telemetry/overview возвращают события, они будут показаны здесь.</EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                )}
              </div>

              <div className="space-y-3">
                <h3 className="text-sm font-medium">Safe test scenarios</h3>
                {scenarios.length ? (
                  <div className="space-y-3">
                    {scenarios.map(scenario => (
                      <div key={scenario.code} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{scenario.title}</p>
                            <p className="text-xs text-muted-foreground">{scenario.code}</p>
                          </div>
                          <Badge variant="secondary">Safe</Badge>
                        </div>
                        <p className="mt-3 text-sm text-muted-foreground">{scenario.description}</p>
                        <p className="mt-2 text-xs text-muted-foreground">Expected outcome: {scenario.expectedOutcome}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </DashboardLayout>
  );
}

type StatusTileProps = {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
};

function StatusTile({ icon: Icon, label, value }: StatusTileProps) {
  return (
    <div className="rounded-2xl border bg-muted/30 p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <p className="text-sm">{label}</p>
      </div>
      <p className="mt-3 text-xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}

function formatPercent(input?: number) {
  if (typeof input !== "number" || Number.isNaN(input)) {
    return "—";
  }

  return `${(input * 100).toFixed(1)}%`;
}
