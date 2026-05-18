import { describe, expect, it } from "vitest";
import { t, SUPPORTED_LOCALES, LOCALE_FLAGS } from "./i18n";
import { sessionStore } from "./fsm";
import { createBot } from "./bot";

describe("i18n", () => {
  it("t() returns message for all 4 locales", () => {
    for (const locale of SUPPORTED_LOCALES) {
      expect(t(locale, "start").length).toBeGreaterThan(0);
    }
  });

  it("t() substitutes parameters correctly", () => {
    const msg = t("en", "score_result", { score: "720", productScore: 16, dataQuality: 8.2, status: "success" });
    expect(msg).toContain("720");
    expect(msg).toContain("16");
    expect(msg).toContain("8.2");
    expect(msg).toContain("success");
  });

  it("t() falls back to 'en' for unknown key", () => {
    expect(t("xx" as any, "start").length).toBeGreaterThan(0);
  });

  it("LOCALE_FLAGS has all 4 locales", () => {
    expect(Object.keys(LOCALE_FLAGS)).toHaveLength(4);
  });
});

describe("fsm SessionStore", () => {
  it("set/get/update/clear cycle", () => {
    sessionStore.clear(99999);
    expect(sessionStore.get(99999)).toBeUndefined();
    sessionStore.set(99999, { state: "idle", locale: "en", userId: 99999, isAdmin: false, createdAt: new Date() });
    expect(sessionStore.get(99999)?.state).toBe("idle");
    sessionStore.update(99999, { state: "processing" });
    expect(sessionStore.get(99999)?.state).toBe("processing");
    sessionStore.clear(99999);
    expect(sessionStore.get(99999)).toBeUndefined();
  });

  it("gc removes expired sessions", () => {
    sessionStore.set(99998, { state: "idle", locale: "en", userId: 99998, isAdmin: false, createdAt: new Date(Date.now() - 60 * 60 * 1000) });
    sessionStore.gc();
    expect(sessionStore.get(99998)).toBeUndefined();
  });

  it("gc keeps recent sessions", () => {
    sessionStore.set(99997, { state: "idle", locale: "en", userId: 99997, isAdmin: false, createdAt: new Date() });
    sessionStore.gc();
    expect(sessionStore.get(99997)).toBeDefined();
    sessionStore.clear(99997);
  });
});

describe("bot createBot", () => {
  it("createBot returns handleMessage function", () => {
    const bot = createBot("test_token");
    expect(typeof bot.handleMessage).toBe("function");
    expect(typeof bot.token).toBe("string");
  });
});