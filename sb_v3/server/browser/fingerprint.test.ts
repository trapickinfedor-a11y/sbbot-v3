import { describe, expect, it } from "vitest";
import {
  generateFingerprint,
  toPlaywrightContextOptions,
  getAntiDetectInitScript,
} from "./fingerprint";

const KNOWN_RESOLUTIONS = [
  [1366, 768], [1920, 1080], [1440, 900], [1536, 864],
  [1280, 800], [1600, 900], [1280, 1024], [1024, 768],
  [1680, 1050], [1920, 1200], [2560, 1440], [1360, 768],
];

function resolutionKey(r: [number, number]): string {
  return `${r[0]}x${r[1]}`;
}

const KNOWN_RESOLUTION_KEYS = new Set(KNOWN_RESOLUTIONS.map(resolutionKey));

describe("fingerprint", () => {
  describe("generateFingerprint", () => {
    it("produces a valid profile with all required fields", () => {
      const fp = generateFingerprint();
      expect(fp).toMatchObject({
        userAgent: expect.stringContaining("Mozilla/5.0"),
        screenWidth: expect.any(Number),
        screenHeight: expect.any(Number),
        timezone: expect.any(String),
        languages: expect.any(Array),
        platform: expect.any(String),
        hardwareConcurrency: expect.any(Number),
        deviceMemory: expect.any(Number),
        webglVendor: expect.any(String),
        webglRenderer: expect.any(String),
        canvasNoiseSeed: expect.any(Number),
        audioNoiseSeed: expect.any(Number),
      });
    });

    it("userAgent contains Firefox version", () => {
      const fp = generateFingerprint();
      expect(fp.userAgent).toMatch(/rv:\d+\.\d+/);
      expect(fp.userAgent).toMatch(/Firefox\/\d+\.\d+/);
    });

    it("screen dimensions are in known resolution set", () => {
      for (let i = 0; i < 20; i++) {
        const fp = generateFingerprint();
        expect(KNOWN_RESOLUTION_KEYS.has(resolutionKey([fp.screenWidth, fp.screenHeight]))).toBe(true);
      }
    });

    it("timezone is from the allowed list", () => {
      const allowed = [
        "America/New_York", "America/Chicago", "America/Denver",
        "America/Los_Angeles", "America/Phoenix", "America/Detroit",
        "America/Indiana/Indianapolis", "America/Boise",
        "America/Anchorage", "Pacific/Honolulu",
      ];
      for (let i = 0; i < 20; i++) {
        expect(allowed).toContain(generateFingerprint().timezone);
      }
    });

    it("languages array is non-empty and starts with en", () => {
      const fp = generateFingerprint();
      expect(fp.languages.length).toBeGreaterThan(0);
      expect(fp.languages[0]).toMatch(/^en/);
    });

    it("platform is from allowed list", () => {
      const allowed = ["Win32", "Win32", "Win32", "MacIntel", "Linux x86_64"];
      for (let i = 0; i < 20; i++) {
        expect(allowed).toContain(generateFingerprint().platform);
      }
    });

    it("hardwareConcurrency is in valid range", () => {
      const allowed = [2, 4, 4, 4, 6, 8, 8, 12, 16];
      for (let i = 0; i < 20; i++) {
        expect(allowed).toContain(generateFingerprint().hardwareConcurrency);
      }
    });

    it("deviceMemory is in allowed range", () => {
      const allowed = [2, 4, 4, 8, 8, 16];
      for (let i = 0; i < 20; i++) {
        expect(allowed).toContain(generateFingerprint().deviceMemory);
      }
    });

    it("canvasNoiseSeed and audioNoiseSeed are positive and <= 999999", () => {
      for (let i = 0; i < 20; i++) {
        const fp = generateFingerprint();
        expect(fp.canvasNoiseSeed).toBeGreaterThan(0);
        expect(fp.canvasNoiseSeed).toBeLessThanOrEqual(999999);
        expect(fp.audioNoiseSeed).toBeGreaterThan(0);
        expect(fp.audioNoiseSeed).toBeLessThanOrEqual(999999);
      }
    });

    it("doNotTrack is null or '1'", () => {
      for (let i = 0; i < 20; i++) {
        const fp = generateFingerprint();
        expect(fp.doNotTrack === null || fp.doNotTrack === "1").toBe(true);
      }
    });

    it("webglVendor and webglRenderer are non-empty strings from known set", () => {
      const knownVendors = [
        "Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)",
        "Intel Inc.", "Apple Inc.",
      ];
      for (let i = 0; i < 20; i++) {
        const fp = generateFingerprint();
        expect(knownVendors).toContain(fp.webglVendor);
        expect(fp.webglRenderer.length).toBeGreaterThan(0);
      }
    });
  });

  describe("toPlaywrightContextOptions", () => {
    it("returns valid Playwright context options from a fingerprint", () => {
      const fp = generateFingerprint();
      const opts = toPlaywrightContextOptions(fp);
      expect(opts).toMatchObject({
        userAgent: fp.userAgent,
        viewport: { width: fp.screenWidth, height: fp.screenHeight },
        locale: expect.stringContaining("en"),
        timezoneId: fp.timezone,
        deviceScaleFactor: expect.any(Number),
        isMobile: false,
        hasTouch: false,
      });
    });

    it("deviceScaleFactor is one of the allowed values", () => {
      const allowed = [1, 1.5, 2, 3];
      for (let i = 0; i < 10; i++) {
        expect(allowed).toContain(toPlaywrightContextOptions(generateFingerprint()).deviceScaleFactor);
      }
    });

    it("viewport dimensions match the fingerprint", () => {
      const fp = generateFingerprint();
      const opts = toPlaywrightContextOptions(fp);
      expect(opts.viewport.width).toBe(fp.screenWidth);
      expect(opts.viewport.height).toBe(fp.screenHeight);
    });

    it("Accept-Language header joins languages with q=0.9", () => {
      const fp = generateFingerprint();
      const opts = toPlaywrightContextOptions(fp);
      expect(opts.extraHTTPHeaders["Accept-Language"]).toMatch(/;q=0\.9$/);
      expect(opts.extraHTTPHeaders["Accept-Language"]).toContain(fp.languages.join(","));
    });
  });

  describe("getAntiDetectInitScript", () => {
    it("returns a non-empty string", () => {
      const script = getAntiDetectInitScript();
      expect(typeof script).toBe("string");
      expect(script.length).toBeGreaterThan(0);
    });

    it("contains canvas noise injection patterns", () => {
      const s = getAntiDetectInitScript();
      expect(s).toContain("HTMLCanvasElement.prototype.toDataURL");
      expect(s).toContain("getContext");
    });

    it("contains AudioContext noise injection patterns", () => {
      expect(getAntiDetectInitScript()).toContain("AudioBuffer.prototype.getChannelData");
    });

    it("contains WebGL noise injection patterns", () => {
      expect(getAntiDetectInitScript()).toContain("WebGLRenderingContext.prototype.readPixels");
    });

    it("contains battery API faking patterns", () => {
      const s = getAntiDetectInitScript();
      expect(s).toContain("getBattery");
      expect(s).toContain("charging");
    });

    it("contains navigator.webdriver override to return false", () => {
      expect(getAntiDetectInitScript()).toContain("webdriver");
    });

    it("wraps the entire script in an IIFE", () => {
      const s = getAntiDetectInitScript();
      expect(s).toMatch(/^\s*\(function\(\)\s*\{/);
      expect(s).toMatch(/\}\)\(\)\s*;?\s*$/);
    });

    it("contains permission query override for sensitive permissions", () => {
      const s = getAntiDetectInitScript();
      expect(s).toContain("navigator.permissions");
      expect(s).toContain("prompt");
    });

    it("contains navigator.plugins override with PDF plugins", () => {
      expect(getAntiDetectInitScript()).toContain("PDF Viewer");
    });

    it("does not throw when called multiple times", () => {
      expect(() => getAntiDetectInitScript()).not.toThrow();
      expect(() => getAntiDetectInitScript()).not.toThrow();
    });
  });
});