import { describe, expect, it } from "vitest";

describe("legacy secret migration", () => {
  it("loads the migrated non-proxy secrets into the runtime", () => {
    const requiredKeys = [
      "BOT_TOKEN",
      "WORKER_COUNT",
      "ADMIN_USER_IDS",
      "WORKER_ROTATE_ON_SUCCESS",
      "PRIVATE_API_KEY",
      "PRIVATE_API_PORT",
      "ADMIN_PASSWORD",
      "CAPTCHA_SERVICE",
    ] as const;

    for (const key of requiredKeys) {
      expect(process.env[key], `${key} should be defined`).toBeTruthy();
    }

    expect(process.env.BOT_TOKEN).toContain(":");
    expect(process.env.ADMIN_USER_IDS).toMatch(/^\d+(,\d+)*$/);
    expect(Number(process.env.WORKER_COUNT)).toBeGreaterThan(0);
    expect(Number(process.env.WORKER_ROTATE_ON_SUCCESS)).toBeGreaterThan(0);
    expect(process.env.PRIVATE_API_KEY?.length).toBeGreaterThan(10);
    expect(Number(process.env.PRIVATE_API_PORT)).toBe(8000);
    expect(process.env.ADMIN_PASSWORD?.length).toBeGreaterThan(8);
    expect(process.env.CAPTCHA_SERVICE).toBe("2captcha");
  });
});
