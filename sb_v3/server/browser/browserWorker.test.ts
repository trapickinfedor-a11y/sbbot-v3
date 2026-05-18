import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";

// Mock playwright — no real browser in test environment
vi.mock("playwright", () => ({
  chromium: {
    launch: vi.fn(async () => {
      throw new Error("Playwright mocked — no real browser");
    }),
  },
}));

import { isBrowserAutomationAvailable, type CreditScorePayload } from "./browserWorker";

function stubProxyEnv(vars: Record<string, string>) {
  Object.entries(vars).forEach(([k, v]) => { process.env[k] = v; });
}

function clearProxyEnv() {
  delete process.env.PROXY_HOST;
  delete process.env.PROXY_PORT;
  delete process.env.PROXY_USERNAME;
  delete process.env.PROXY_PASSWORD;
  delete process.env.PROXY_COUNTRY;
  delete process.env.PROXY_PROTOCOL;
  delete process.env.WORKER_ROTATE_ON_SUCCESS;
}

describe("isBrowserAutomationAvailable", () => {
  beforeEach(clearProxyEnv);
  afterEach(clearProxyEnv);

  it("returns false when proxy env vars are not set", () => {
    expect(isBrowserAutomationAvailable()).toBe(false);
  });

  it("returns true when all required proxy env vars are present", () => {
    stubProxyEnv({
      PROXY_HOST: "proxy.test",
      PROXY_PORT: "8080",
      PROXY_USERNAME: "user",
      PROXY_PASSWORD: "pass",
    });
    expect(isBrowserAutomationAvailable()).toBe(true);
  });

  it("returns false when only PROXY_HOST is set", () => {
    stubProxyEnv({ PROXY_HOST: "proxy.test" });
    expect(isBrowserAutomationAvailable()).toBe(false);
  });

  it("returns false when port is invalid", () => {
    stubProxyEnv({
      PROXY_HOST: "proxy.test",
      PROXY_PORT: "invalid",
      PROXY_USERNAME: "user",
      PROXY_PASSWORD: "pass",
    });
    expect(isBrowserAutomationAvailable()).toBe(false);
  });
});

describe("CreditScorePayload type", () => {
  it("accepts valid payload shape", () => {
    const p: CreditScorePayload = {
      firstName: "John",
      lastName: "Doe",
      street: "123 Main St",
      city: "New York",
      state: "NY",
      zipCode: "10001",
      dob: "01/01/1990",
      annualIncome: "50000",
      email: "test@example.com",
    };
    expect(p.firstName).toBe("John");
    expect(p.dob).toBe("01/01/1990");
  });

  it("optional email and phone fields", () => {
    const p: CreditScorePayload = {
      firstName: "Jane",
      lastName: "Smith",
      street: "456 Oak Ave",
      city: "Los Angeles",
      state: "CA",
      zipCode: "90001",
      dob: "05/15/1985",
      annualIncome: "75000",
    };
    expect(p.email).toBeUndefined();
    expect(p.phone).toBeUndefined();
  });
});