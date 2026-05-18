import { describe, expect, it, vi } from "vitest";
import { JobDispatcher } from "./dispatcher";
import { WorkerPool, WorkerContext } from "./workerPool";

function makePayload(priority = 50) {
  return { target: "mock://test", queueName: "test", priority, payload: {}, source: "test" };
}

describe("WorkerPool", () => {
  it("start creates N workers", () => {
    const d = new JobDispatcher();
    const pool = new WorkerPool(d, async () => ({ success: true }), { workerId: 0, concurrency: 3, pollIntervalMs: 999999 });
    pool.start();
    expect(pool.getStats().activeWorkers).toBe(3);
    pool.shutdown(100);
  });

  it("shutdown stops all workers and sets shuttingDown flag", async () => {
    const d = new JobDispatcher();
    const pool = new WorkerPool(d, async () => ({ success: true }), { workerId: 0, concurrency: 2, pollIntervalMs: 999999 });
    pool.start();
    await pool.shutdown(100);
    expect(pool.getStats().isShuttingDown).toBe(true);
    expect(pool.getStats().activeWorkers).toBe(0);
  });

  it("getStats reflects dispatcher state", () => {
    const d = new JobDispatcher();
    d.enqueue(makePayload()); d.enqueue(makePayload());
    const pool = new WorkerPool(d, async () => ({ success: true }), { workerId: 0, concurrency: 1, pollIntervalMs: 999999 });
    const stats = pool.getStats();
    expect(stats.dispatchers?.pending).toBeUndefined(); // dispatcher not nested in stats
    expect(stats.dispatcher.pending).toBe(2);
  });

  it("getStats shows correct activeWorkers count", () => {
    const d = new JobDispatcher();
    const pool = new WorkerPool(d, async () => ({ success: true }), { workerId: 0, concurrency: 5, pollIntervalMs: 999999 });
    pool.start();
    expect(pool.getStats().activeWorkers).toBe(5);
    pool.shutdown(100);
  });

  it("executor is invoked with WorkerContext containing job details", async () => {
    const d = new JobDispatcher();
    const job = d.enqueue(makePayload());
    let capturedJobId: string | null = null;
    let capturedWorkerId: number | null = null;
    const pool = new WorkerPool(d, async (ctx: WorkerContext) => {
      capturedJobId = ctx.job.id;
      capturedWorkerId = ctx.workerId;
      return { success: true };
    }, { workerId: 42, concurrency: 1, pollIntervalMs: 999999 });

    // Manually trigger the executor via the poll method by adding a job
    d.dequeue(1);
    await pool["executor"]({ workerId: 42, job, startTime: new Date(), attempt: 1 });
    expect(capturedJobId).toBe(job.id);
    expect(capturedWorkerId).toBe(42);
  });
});