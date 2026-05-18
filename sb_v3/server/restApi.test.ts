import express from "express";
import type { AddressInfo } from "node:net";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { registerRestApi } from "./restApi";
import { resetRuntimeStore, saveRuntimeApiKey } from "./runtimeStore";

const syntheticImportedText = `LeadFeed Alpha, [3/30/26 9:13 PM]
Alex Example
123 Example St, Exampletown, CA 90001
28 years old (Jan 1, 1998)
(555) 111-2233
alex@example.com
Your credit score: 720
SSN: 123-45-6789
DOB: 1/1/1998

Jordan Sample
456 Another Ave
Demo City, TX 73301
AGE: 31
BORN: FEB 1995
NF
SSN: 987-65-4321
DOB: 2/2/1995`;

const importedDatasetFixture = readFileSync(
  resolve(process.cwd(), "server/fixtures/importedLeadDataset.fixture.txt"),
  "utf8",
);

function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

function seedApiKey(rawToken: string, scope: "single" | "bulk" | "vip" | "admin") {
  const now = new Date();
  saveRuntimeApiKey({
    userId: 1,
    label: `${scope} test key`,
    keyPrefix: rawToken.slice(0, 16),
    keyHash: sha256(rawToken),
    scope,
    status: "active",
    rpmLimit: 120,
    dailyLimit: 10_000,
    lastUsedAt: null,
    expiresAt: new Date(now.getTime() + 60 * 60 * 1000),
    createdAt: now,
    updatedAt: now,
  });
}

describe("restApi imported data routes", () => {
  let server: ReturnType<typeof appListen>;
  let baseUrl = "";

  beforeAll(async () => {
    const app = express();
    app.use(express.json({ limit: "1mb" }));
    registerRestApi(app);

    server = await appListen(app);
    const address = server.address() as AddressInfo;
    baseUrl = `http://127.0.0.1:${address.port}`;
  });

  beforeEach(() => {
    resetRuntimeStore();
    seedApiKey("cs_admin_preview_test_token", "admin");
    seedApiKey("cs_bulk_safe_batch_token", "bulk");
    seedApiKey("cs_single_scope_token", "single");
  });

  afterAll(async () => {
    resetRuntimeStore();
    await new Promise<void>((resolve, reject) => {
      server.close(error => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
  });

  it("returns a redacted structural preview for imported text", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/preview`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_admin_preview_test_token",
      },
      body: JSON.stringify({ inputText: syntheticImportedText }),
    });

    expect(response.status).toBe(200);
    const json = await response.json();

    expect(json.ok).toBe(true);
    expect(json.meta).toMatchObject({ piiRedacted: true, safePreview: true });
    expect(json.data).toMatchObject({
      totalRecords: 2,
      withPhone: 1,
      withEmailDomain: 1,
      withDob: 2,
      withSsnMarker: 2,
    });
    expect(json.data.sampleRecords[0]).toMatchObject({
      piiRedacted: true,
      email: null,
      state: "CA",
    });
    expect(json.data.safePayloads[0]).toMatchObject({
      queueName: "lead-import",
      safeTestMode: true,
      payload: {
        piiRedacted: true,
        target: "mock://lead-import/1",
      },
    });
  });

  it("creates a safe imported batch for bulk-compatible scopes", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/safe-batch`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_bulk_safe_batch_token",
      },
      body: JSON.stringify({ inputText: syntheticImportedText }),
    });

    expect(response.status).toBe(200);
    const json = await response.json();

    expect(json.ok).toBe(true);
    expect(json.meta).toMatchObject({ piiRedacted: true, importedFormat: true, safeTestMode: true });
    expect(json.data.itemCount).toBe(2);
    expect(json.data.jobs).toHaveLength(2);
    expect(json.data.jobs[0]).toMatchObject({
      requestMode: "bulk",
      status: "succeeded",
      queueName: "lead-import",
    });
  });

  it("rejects safe imported batch for single-only scopes", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/safe-batch`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_single_scope_token",
      },
      body: JSON.stringify({ inputText: syntheticImportedText }),
    });

    expect(response.status).toBe(403);
    const json = await response.json();
    expect(json.ok).toBe(false);
    expect(json.error).toMatchObject({ code: "FORBIDDEN" });
  });

  it("returns a redacted preview for the broader anonymized dataset fixture", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/preview`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_admin_preview_test_token",
      },
      body: JSON.stringify({ inputText: importedDatasetFixture }),
    });

    expect(response.status).toBe(200);
    const json = await response.json();

    expect(json.ok).toBe(true);
    expect(json.meta).toMatchObject({ piiRedacted: true, safePreview: true });
    expect(json.data).toMatchObject({
      totalRecords: 9,
      withPhone: 6,
      withEmailDomain: 5,
      withDob: 8,
      withSsnMarker: 8,
    });
    expect(json.data.sourceLabels).toHaveLength(4);
    expect(json.data.safePayloads).toHaveLength(9);
    expect(json.data.sampleRecords.every((record: { piiRedacted: boolean }) => record.piiRedacted)).toBe(true);
  });

  it("creates a safe imported batch from the broader anonymized dataset fixture", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/safe-batch`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_bulk_safe_batch_token",
      },
      body: JSON.stringify({ inputText: importedDatasetFixture }),
    });

    expect(response.status).toBe(200);
    const json = await response.json();

    expect(json.ok).toBe(true);
    expect(json.meta).toMatchObject({ piiRedacted: true, importedFormat: true, safeTestMode: true });
    expect(json.data.itemCount).toBe(9);
    expect(json.data.jobs).toHaveLength(9);
    expect(json.data.jobs.every((job: { requestMode: string; status: string; queueName: string }) => job.requestMode === "bulk")).toBe(true);
    expect(json.data.jobs.every((job: { requestMode: string; status: string; queueName: string }) => job.status === "succeeded")).toBe(true);
    expect(json.data.jobs.every((job: { requestMode: string; status: string; queueName: string }) => job.queueName === "lead-import")).toBe(true);
  });

  it("validates malformed imported payloads", async () => {
    const response = await fetch(`${baseUrl}/api/v1/imported-data/preview`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer cs_admin_preview_test_token",
      },
      body: JSON.stringify({ inputText: "   " }),
    });

    expect(response.status).toBe(400);
    const json = await response.json();
    expect(json.ok).toBe(false);
    expect(json.error).toMatchObject({ code: "VALIDATION_ERROR" });
  });
});

function appListen(app: express.Express) {
  return new Promise<ReturnType<express.Express["listen"]>>((resolve, reject) => {
    const server = app.listen(0, "127.0.0.1", () => resolve(server));
    server.once("error", reject);
  });
}
