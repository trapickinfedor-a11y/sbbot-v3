/**
 * Worker pool orchestrator — concurrent workers pulling from dispatcher.
 */
import { JobDispatcher, QueuedJob } from "./dispatcher";

export interface WorkerConfig {
  workerId: number;
  concurrency: number;
  pollIntervalMs: number;
}

export interface WorkerContext {
  workerId: number;
  job: QueuedJob;
  startTime: Date;
  attempt: number;
}

export type JobExecutor = (ctx: WorkerContext) => Promise<{ success: boolean; result?: unknown; error?: string }>;

export class WorkerPool {
  private timers: Map<number, NodeJS.Timeout> = new Map();
  private _shuttingDown = false;

  constructor(
    private dispatcher: JobDispatcher,
    private executor: JobExecutor,
    private config: WorkerConfig,
  ) {}

  start(): void {
    const { workerId, concurrency, pollIntervalMs } = this.config;
    for (let i = 0; i < concurrency; i++) {
      this.schedulePoll(workerId + i, pollIntervalMs);
    }
    console.log(`[WorkerPool] Started ${concurrency} workers`);
  }

  private schedulePoll(workerId: number, delayMs: number): void {
    const timer = setTimeout(async () => {
      if (this._shuttingDown) return;
      await this.poll(workerId);
      if (!this._shuttingDown) this.schedulePoll(workerId, delayMs);
    }, delayMs);
    this.timers.set(workerId, timer);
  }

  private async poll(workerId: number): Promise<void> {
    const jobs = this.dispatcher.dequeue(1);
    if (jobs.length === 0) return;
    const job = jobs[0];
    const ctx: WorkerContext = { workerId, job, startTime: new Date(), attempt: job.attempts + 1 };
    try {
      const result = await this.executor(ctx);
      if (result.success) this.dispatcher.complete(job.id);
      else this.dispatcher.fail(job.id, result.error ?? "Unknown error");
    } catch (err) {
      this.dispatcher.fail(job.id, String(err));
    }
  }

  async shutdown(timeoutMs = 5000): Promise<void> {
    this._shuttingDown = true;
    Array.from(this.timers.values()).forEach(timer => clearTimeout(timer));
    this.timers.clear();
    await new Promise(resolve => setTimeout(resolve, Math.min(timeoutMs, 2000)));
    console.log("[WorkerPool] Graceful shutdown complete");
  }

  getStats() {
    return { activeWorkers: this.timers.size, isShuttingDown: this._shuttingDown, dispatcher: this.dispatcher.getStats() };
  }
}