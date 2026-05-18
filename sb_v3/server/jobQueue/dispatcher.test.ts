import { describe, expect, it } from "vitest";
import { JobDispatcher } from "./dispatcher";

function makePayload(priority = 50, source = "test") {
  return { target: "mock://test", queueName: "test", priority, payload: {}, source };
}

describe("JobDispatcher", () => {
  it("enqueue returns a QueuedJob with pending status", () => {
    const d = new JobDispatcher();
    const job = d.enqueue(makePayload());
    expect(job.status).toBe("pending");
    expect(typeof job.id).toBe("string");
    expect(job.id.length).toBeGreaterThan(0);
  });

  it("dequeue returns up to N jobs", () => {
    const d = new JobDispatcher();
    d.enqueue(makePayload()); d.enqueue(makePayload()); d.enqueue(makePayload());
    const jobs = d.dequeue(2);
    expect(jobs).toHaveLength(2);
    expect(jobs.every(j => j.status === "running")).toBe(true);
    expect(d.getStats().pending).toBe(1);
  });

  it("priority ordering: critical > high > normal > low > batch", () => {
    const d = new JobDispatcher();
    d.enqueue(makePayload(5));
    d.enqueue(makePayload(80));
    d.enqueue(makePayload(50));
    d.enqueue(makePayload(100));
    const jobs = d.dequeue(4);
    expect(jobs[0].priority).toBe("critical");
    expect(jobs[1].priority).toBe("high");
    expect(jobs[2].priority).toBe("normal");
    expect(jobs[3].priority).toBe("batch");
  });

  it("complete marks job as completed", () => {
    const d = new JobDispatcher();
    const job = d.enqueue(makePayload());
    d.dequeue(1);
    d.complete(job.id);
    expect(d.getStats().running).toBe(0);
  });

  it("fail retries up to maxAttempts then moves to DLQ", () => {
    const d = new JobDispatcher();
    const job = d.enqueue(makePayload(), 2);
    d.dequeue(1);
    expect(d.fail(job.id, "test error")).not.toBeNull();
    expect(d.getStats().pending).toBe(1);
    d.dequeue(1);
    expect(d.fail(job.id, "test error")).not.toBeNull();
    expect(d.getStats().deadLetter).toBe(1);
    expect(d.getStats().running).toBe(0);
  });

  it("drainDeadLetter returns all DLQ jobs and clears the queue", () => {
    const d = new JobDispatcher();
    const job = d.enqueue(makePayload(), 1);
    d.dequeue(1);
    d.fail(job.id, "fatal");
    const dlq = d.drainDeadLetter();
    expect(dlq).toHaveLength(1);
    expect(d.getStats().deadLetter).toBe(0);
  });

  it("getStats returns accurate counts", () => {
    const d = new JobDispatcher();
    expect(d.getStats()).toEqual({ pending: 0, running: 0, deadLetter: 0 });
    d.enqueue(makePayload()); d.enqueue(makePayload());
    expect(d.getStats().pending).toBe(2);
  });

  it("enqueue respects FIFO within same priority", () => {
    const d = new JobDispatcher();
    const job1 = d.enqueue(makePayload(50, "first"));
    const job2 = d.enqueue(makePayload(50, "second"));
    const [deq1, deq2] = d.dequeue(2);
    expect(deq1.payload.source).toBe("first");
    expect(deq2.payload.source).toBe("second");
  });
});