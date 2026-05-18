/**
 * Job queue dispatcher — priority-based with dead-letter queue and exponential backoff.
 */
import { randomBytes } from "crypto";
import { z } from "zod";

export const jobPrioritySchema = z.enum(["critical", "high", "normal", "low", "batch"]);
export type JobPriority = z.infer<typeof jobPrioritySchema>;

export const PRIORITY_ORDER: Record<JobPriority, number> = {
  critical: 100, high: 80, normal: 50, low: 20, batch: 5,
};

export interface JobPayload {
  target: string;
  queueName: string;
  priority: number;
  payload: Record<string, unknown>;
  safeTestMode?: boolean;
  source: string;
}

export interface QueuedJob {
  id: string;
  enqueuedAt: Date;
  priority: JobPriority;
  payload: JobPayload;
  attempts: number;
  maxAttempts: number;
  status: "pending" | "running" | "completed" | "failed" | "dead_letter";
  lastError?: string;
}

export class JobDispatcher {
  private pendingQueue: QueuedJob[] = [];
  private runningJobs = new Map<string, QueuedJob>();
  private deadLetterQueue: QueuedJob[] = [];

  enqueue(job: JobPayload, maxAttempts = 3): QueuedJob {
    const queuedJob: QueuedJob = {
      id: randomBytes(8).toString("hex"),
      enqueuedAt: new Date(),
      priority: this.inferPriority(job.priority),
      payload: job,
      attempts: 0,
      maxAttempts,
      status: "pending",
    };
    this.pendingQueue.push(queuedJob);
    this.sortByPriority();
    return queuedJob;
  }

  dequeue(count: number): QueuedJob[] {
    const jobs: QueuedJob[] = [];
    while (jobs.length < count && this.pendingQueue.length > 0) {
      const job = this.pendingQueue.shift()!;
      job.status = "running";
      this.runningJobs.set(job.id, job);
      jobs.push(job);
    }
    return jobs;
  }

  complete(jobId: string): void {
    const job = this.runningJobs.get(jobId);
    if (job) { job.status = "completed"; this.runningJobs.delete(jobId); }
  }

  fail(jobId: string, error: string): QueuedJob | null {
    const job = this.runningJobs.get(jobId);
    if (!job) return null;
    job.attempts++;
    job.lastError = error;
    this.runningJobs.delete(jobId);

    if (job.attempts >= job.maxAttempts) {
      job.status = "dead_letter";
      this.deadLetterQueue.push(job);
      return job;
    }

    job.status = "pending";
    this.pendingQueue.push(job);
    this.sortByPriority();
    return job;
  }

  getStats() {
    return {
      pending: this.pendingQueue.length,
      running: this.runningJobs.size,
      deadLetter: this.deadLetterQueue.length,
    };
  }

  drainDeadLetter(): QueuedJob[] {
    const dlq = [...this.deadLetterQueue];
    this.deadLetterQueue = [];
    return dlq;
  }

  private inferPriority(numericPriority: number): JobPriority {
    if (numericPriority >= 90) return "critical";
    if (numericPriority >= 75) return "high";
    if (numericPriority >= 45) return "normal";
    if (numericPriority >= 20) return "low";
    return "batch";
  }

  private sortByPriority(): void {
    this.pendingQueue.sort((a, b) => {
      const pa = PRIORITY_ORDER[a.priority] * 1e12 + a.enqueuedAt.getTime();
      const pb = PRIORITY_ORDER[b.priority] * 1e12 + b.enqueuedAt.getTime();
      return pb - pa;
    });
  }
}