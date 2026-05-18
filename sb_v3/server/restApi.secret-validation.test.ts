import { createHash } from "node:crypto";
import express from "express";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { registerRestApi } from "./restApi";
import { resetRuntimeStore, saveRuntimeApiKey } from "./runtimeStore";

let server: ReturnType<express.Express["listen"]> | null = null;
let baseUrl = "";

function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

describe("REST API secret validation", () => {
  beforeAll(async () => {
    const app = express();
    app.use(express.json());
    registerRestApi(app);

    await new Promise<void>((resolve) => {
      server = app.listen(0, "127.0.0.1", () => {
        const address = server?.address();
        if (!address || typeof address === "string") {
          throw new Error("Failed to bind test server");
        }
        baseUrl = `http://127.0.0.1:${address.port}`;
        resolve();
      });
    });
  });

  beforeEach(() => {
    resetRuntimeStore();
  });

  afterAll(async () => {
    resetRuntimeStore();

    await new Promise<void>((resolve, reject) => {
      if (!server) {
        resolve();
        return;
      }

      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
  });

  it("accepts migrated PRIVATE_API_KEY on protected usage summary endpoint", async () => {
    const migratedApiKey = process.env.PRIVATE_API_KEY;

    expect(typeof migratedApiKey).toBe("string");
    expect(migratedApiKey?.length ?? 0).toBeGreaterThan(16);

    const response = await fetch(`${baseUrl}/api/v1/usage/summary`, {
      headers: {
        Authorization: `Bearer ${migratedApiKey}`,
      },
    });

    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      ok: boolean;
      data?: {
        apiKeys?: Array<{ keyPrefix: string }>;
        usageSummary?: {
          requests?: number;
        };
      };
    };

    expect(payload.ok).toBe(true);
    expect(Array.isArray(payload.data?.apiKeys ?? [])).toBe(true);
    expect(typeof payload.data?.usageSummary?.requests).toBe("number");
  });

  it("accepts runtime API key only when bearer token matches persisted sha256 hash", async () => {
    const rawToken = "cs_bulk_runtime_validation_token_123456789";
    const now = new Date();

    saveRuntimeApiKey({
      userId: 42,
      label: "Runtime bulk key",
      keyPrefix: rawToken.slice(0, 16),
      keyHash: sha256(rawToken),
      scope: "bulk",
      status: "active",
      rpmLimit: 77,
      dailyLimit: 700,
      lastUsedAt: null,
      expiresAt: new Date(now.getTime() + 60_000),
      createdAt: now,
      updatedAt: now,
    });

    const response = await fetch(`${baseUrl}/api/v1/usage/summary`, {
      headers: {
        Authorization: `Bearer ${rawToken}`,
      },
    });

    expect(response.status).toBe(200);

    const payload = (await response.json()) as {
      ok: boolean;
      data?: {
        apiKeys?: Array<{ keyPrefix: string }>;
      };
    };

    expect(payload.ok).toBe(true);
    expect(payload.data?.apiKeys?.some((key) => key.keyPrefix === rawToken.slice(0, 16))).toBe(true);
  });

  it("rejects revoked or expired runtime API keys even if prefix looks valid", async () => {
    const rawToken = "cs_admin_revoked_validation_token_987654321";
    const now = new Date();

    saveRuntimeApiKey({
      userId: 7,
      label: "Revoked key",
      keyPrefix: rawToken.slice(0, 16),
      keyHash: sha256(rawToken),
      scope: "admin",
      status: "revoked",
      rpmLimit: 10,
      dailyLimit: 100,
      lastUsedAt: null,
      expiresAt: new Date(now.getTime() - 60_000),
      createdAt: now,
      updatedAt: now,
    });

    const response = await fetch(`${baseUrl}/api/v1/usage/summary`, {
      headers: {
        Authorization: `Bearer ${rawToken}`,
      },
    });

    expect(response.status).toBe(401);

    const payload = (await response.json()) as {
      ok: boolean;
      error?: { code?: string };
    };

    expect(payload.ok).toBe(false);
    expect(payload.error?.code).toBe("UNAUTHORIZED");
  });
});
