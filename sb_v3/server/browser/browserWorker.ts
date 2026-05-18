/**
 * Browser worker — Playwright-based credit score automation.
 * Ported from legacy Python credit_score_bot.
 *
 * Full flow:
 * 1. Generate fresh fingerprint profile
 * 2. Launch browser with proxy and anti-detection config
 * 3. Inject ThreatMetrix noise (canvas, audio, WebGL, battery)
 * 4. Fill 3-step funnel form on universal-credit.com
 * 5. Navigate to documents portal
 * 6. Download Adverse Action Notice PDF
 * 7. Extract credit score (300-850)
 * 8. Build ONE CS result
 */

import type { Browser, Page, BrowserContext } from "playwright";
import { chromium } from "playwright";
import {
  generateFingerprint,
  toPlaywrightContextOptions,
  getAntiDetectInitScript,
} from "./fingerprint";
import { warmUpPage, humanDelay, humanScroll, sleep } from "./humanBehavior";
import { ProxyManager } from "./proxyManager";
import { buildOneCsResult } from "../../shared/oneCsScoring";

const UC_FUNNEL_URL =
  "https://www.universal-credit.com/funnel/personal-information-1/DEBT_CONSOLIDATION/5000?step=contact";
const UC_DOCUMENTS_URL = "https://www.universal-credit.com/portal/profile/documents";
const ACCOUNT_PASSWORD = "Secure#Pass2025!";

export interface CreditScorePayload {
  firstName: string;
  lastName: string;
  street: string;
  city: string;
  state: string;
  zipCode: string;
  dob: string; // MM/DD/YYYY
  annualIncome: string;
  email?: string;
  phone?: string;
  ssn?: string;
}

export interface CreditScoreResult {
  ok: boolean;
  creditScore: number | null;
  source: string;
  productScore: number;
  dataQuality: number;
  adverseReasons: string[];
  priceUsd: number;
  status: string;
  durationMs: number;
  proxyIp?: string;
  error?: string;
  needsSsn?: boolean;
  pdfPath?: string;
}

const STEP_TIMEOUT = 60_000;
const FORM_TIMEOUT = 120_000;
const PDF_TIMEOUT = 60_000;

/** Shared browser instance — reused across requests for performance */
let sharedBrowser: Browser | null = null;
let sharedBrowserFingerprint: ReturnType<typeof generateFingerprint> | null = null;
let sharedBrowserProxy: ProxyManager | null = null;

function getSharedBrowserConfig() {
  return {
    fingerprint: sharedBrowserFingerprint,
    proxy: sharedBrowserProxy,
  };
}

/** Generate a random email */
function randomEmail(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let prefix = "";
  for (let i = 0; i < 10; i++) {
    prefix += chars[Math.floor(Math.random() * chars.length)];
  }
  const domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"];
  return `${prefix}@${
    domains[Math.floor(Math.random() * domains.length)]
  }`;
}

/** Extract text content from PDF buffer using basic parsing */
function extractTextFromPdf(pdfData: Buffer): string {
  // Simple PDF text extraction — look for text between BT/ET markers
  const text = pdfData.toString("latin1", 0, pdfData.length);
  const matches: string[] = [];
  const btMatches = text.match(/BT[\s\S]*?ET/g);
  if (btMatches) {
    for (const block of btMatches) {
      const tjMatches = block.match(/\(((?:[^()\\]|\\.)*)\)/g);
      if (tjMatches) {
        for (const match of tjMatches) {
          const content = match.slice(1, -1)
            .replace(/\\\(/g, "(")
            .replace(/\\\)/g, ")")
            .replace(/\\(\d{3})/g, (_, octal) => String.fromCharCode(parseInt(octal, 8)));
          if (content.trim()) {
            matches.push(content);
          }
        }
      }
    }
  }
  return matches.join(" ");
}

/** Extract credit score from PDF text */
function parseScoreFromText(text: string): number | null {
  const patterns = [
    /(?:credit\s+score|fico\s+score|score\s+value)[^\d]*(\d{3})/i,
    /(?:your\s+score\s+is)[^\d]*(\d{3})/i,
    /score[^\d]*(\d{3})/i,
    /\b([5-8]\d{2})\b/,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) {
      const score = parseInt(m[1], 10);
      if (score >= 300 && score <= 850) {
        return score;
      }
    }
  }

  // Fallback: find any 3-digit number in 500-850 range
  const allNums = text.match(/\b(\d{3})\b/g);
  if (allNums) {
    for (const num of allNums) {
      const score = parseInt(num, 10);
      if (score >= 500 && score <= 850) {
        return score;
      }
    }
  }

  return null;
}

async function fillStep1(page: Page, payload: CreditScorePayload): Promise<void> {
  // First name
  await humanDelay(page as never, 200, 400);
  await page.fill("[name='borrowerFirstName']", payload.firstName);

  // Last name
  await humanDelay(page as never, 200, 400);
  await page.fill("[name='borrowerLastName']", payload.lastName);

  // Address — geosuggest autocomplete
  await humanDelay(page as never, 300, 600);
  const addrInput = page.locator("[name='borrowerStreet'], #geosuggest__input--borrowerStreet").first();
  await addrInput.click();
  await addrInput.fill("");
  await sleep(200);

  for (const char of `${payload.street} ${payload.zipCode}`) {
    await addrInput.press(char);
    await sleep(20 + Math.random() * 30);
  }

  await sleep(2000); // Wait for suggestions

  // Select first suggestion matching state
  const suggestions = page.locator(".geosuggest__suggests li, [class*='suggest'] li").first();
  if (await suggestions.count() > 0) {
    await suggestions.click();
  }

  await humanDelay(page as never, 500, 1000);

  // Date of birth
  const dobField = page.locator("[name='borrowerDateOfBirth']").first();
  if (await dobField.count() > 0) {
    await dobField.click();
    await humanDelay(page as never, 100, 300);
    await dobField.fill(payload.dob);
  }
}

async function fillStep2(page: Page, payload: CreditScorePayload): Promise<void> {
  await humanDelay(page as never, 200, 400);
  const incomeField = page.locator("[name='borrowerIncome']").first();
  if (await incomeField.count() > 0) {
    await incomeField.click();
    await incomeField.fill(payload.annualIncome);
  }
}

async function fillStep3(page: Page, email: string): Promise<void> {
  await humanDelay(page as never, 300, 600);

  const emailField = page.locator("[name='username'], [name='email'], input[type='email']").first();
  if (await emailField.count() > 0) {
    await emailField.click();
    await emailField.fill(email);
  }

  await humanDelay(page as never, 300, 700);

  const passField = page.locator("[name='password'], input[type='password']").first();
  if (await passField.count() > 0) {
    await passField.click();
    await passField.fill(ACCOUNT_PASSWORD);
  }

  await humanDelay(page as never, 400, 800);

  // Check agreements if present
  const checkbox = page.locator("[name='agreements'], [type='checkbox']").first();
  if (await checkbox.count() > 0) {
    const isChecked = await checkbox.isChecked();
    if (!isChecked) {
      await checkbox.check();
      await humanDelay(page as never, 200, 500);
    }
  }
}

async function clickContinue(page: Page): Promise<void> {
  const btn = page.locator("button:has-text('Continue'), button[type='submit']").first();
  if (await btn.count() > 0) {
    await btn.click();
  } else {
    await page.keyboard.press("Enter");
  }
  await humanDelay(page as never, 500, 1500);
}

async function submitForm(page: Page): Promise<void> {
  const btn = page.locator("button:has-text('Check Your Rate'), button[type='submit']").first();
  if (await btn.count() > 0) {
    await btn.click();
  } else {
    await page.keyboard.press("Enter");
  }

  await sleep(3000);

  // Handle ThreatMetrix overlay if present
  for (let i = 0; i < 60; i++) {
    const overlay = await page.$("#sec-overlay");
    if (!overlay) break;
    await sleep(1000);
  }
}

async function waitForStep(page: Page, stepName: string, timeout = STEP_TIMEOUT): Promise<void> {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (page.url().includes(`step=${stepName}`)) return;
    await sleep(500);
  }
  throw new Error(`Step '${stepName}' did not appear within ${timeout}ms. URL: ${page.url()}`);
}

async function downloadAdverseActionPdf(page: Page): Promise<Buffer | null> {
  // Intercept network responses for PDF
  let pdfBuffer: Buffer | null = null;

  page.on("response", async response => {
    const ct = response.headers()["content-type"] ?? "";
    const url = response.url();
    if (ct.includes("pdf") || url.endsWith(".pdf") || url.includes(".pdf")) {
      try {
        const body = await response.body();
        if (body && body.slice(0, 4).toString() === "%PDF") {
          pdfBuffer = Buffer.from(body);
        }
      } catch {}
    }
  });

  // Navigate to documents portal
  await page.goto(UC_DOCUMENTS_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await sleep(5000); // Wait for dynamic content

  // Find and click Adverse Action Notice
  await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("li, tr, div"));
    for (const row of rows) {
      if (row.textContent?.toLowerCase().includes("adverse action")) {
        const btn = row.querySelector("a, button");
        if (btn instanceof HTMLElement) btn.click();
        return;
      }
    }
  });

  await sleep(5000);

  page.removeListener("response", () => {});

  return pdfBuffer;
}

/**
 * Execute a single credit score request.
 * Returns a structured result ready for ONE CS scoring.
 */
export async function executeCreditScoreJob(
  payload: CreditScorePayload,
  proxyManager?: ProxyManager,
  headless = true,
): Promise<CreditScoreResult> {
  const startTime = Date.now();
  let browser: Browser | null = null;
  let context: BrowserContext | null = null;

  try {
    const fingerprint = generateFingerprint();
    const ctxOptions = toPlaywrightContextOptions(fingerprint);

    // Build browser launch arguments
    const extraArgs = [
      "--disable-blink-features=AutomationControlled",
      "--no-sandbox",
      "--disable-gpu",
      "--disable-software-rasterizer",
    ];

    // Proxy configuration
    const launchOptions: Parameters<typeof chromium.launch>[0] = {
      headless,
      args: extraArgs,
    };

    if (proxyManager) {
      const pwProxy = proxyManager.toPlaywrightProxy();
      launchOptions.proxy = {
        server: pwProxy.server,
        username: pwProxy.username,
        password: pwProxy.password,
      };
    }

    // Launch browser
    browser = await chromium.launch(launchOptions);
    context = await browser.newContext({
      ...ctxOptions,
      acceptDownloads: true,
    });

    const page = await context.newPage();

    // Inject anti-detection script BEFORE navigation
    await page.addInitScript(getAntiDetectInitScript());

    const email = payload.email ?? randomEmail();

    // Step 1: Personal information
    await page.goto(UC_FUNNEL_URL, { waitUntil: "domcontentloaded", timeout: FORM_TIMEOUT });
    await warmUpPage(page as never);
    await fillStep1(page, payload);
    await clickContinue(page);

    // Step 2: Income
    await waitForStep(page, "income");
    await fillStep2(page, payload);
    await clickContinue(page);

    // Step 3: Account creation
    await waitForStep(page, "login");
    await fillStep3(page, email);
    await submitForm(page);

    // Check result
    const url = page.url();
    if (!url.includes("adverse-page") && !url.includes("offer-page")) {
      return {
        ok: false,
        creditScore: null,
        source: "universal-credit.com",
        productScore: 0,
        dataQuality: 0,
        adverseReasons: [],
        priceUsd: 0,
        status: "failed",
        durationMs: Date.now() - startTime,
        error: `Form did not advance. URL: ${url}`,
      };
    }

    // Download and extract score
    const pdfData = await downloadAdverseActionPdf(page);
    let creditScore: number | null = null;

    if (pdfData) {
      const text = extractTextFromPdf(pdfData);
      creditScore = parseScoreFromText(text);
    }

    const durationMs = Date.now() - startTime;

    if (creditScore === null) {
      return {
        ok: false,
        creditScore: null,
        source: "universal-credit.com",
        productScore: 0,
        dataQuality: 0,
        adverseReasons: [],
        priceUsd: 0,
        status: "failed",
        durationMs,
        error: "PDF downloaded but credit score not found",
        pdfPath: undefined,
      };
    }

    return {
      ok: true,
      creditScore,
      source: "universal-credit.com",
      productScore: 0, // Will be computed by ONE CS scoring
      dataQuality: 0,
      adverseReasons: [],
      priceUsd: 0,
      status: "succeeded",
      durationMs,
      proxyIp: proxyManager?.sessionId,
    };
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      creditScore: null,
      source: "universal-credit.com",
      productScore: 0,
      dataQuality: 0,
      adverseReasons: [],
      priceUsd: 0,
      status: "failed",
      durationMs: Date.now() - startTime,
      error: `Browser execution error: ${error}`,
    };
  } finally {
    if (context) await context.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
  }
}

/** Check if browser automation is available (Playwright installed, proxy configured) */
export function isBrowserAutomationAvailable(): boolean {
  // Browser automation is "available" if the proxy is configured
  // The actual availability is checked at runtime
  const proxyConfig = proxyConfigFromEnvInline();
  return proxyConfig !== null;
}

function proxyConfigFromEnvInline(): {
  host: string;
  port: number;
  username: string;
  password: string;
  protocol: "http" | "socks5";
  country: string;
  rotateOnSuccess: number;
} | null {
  const host = process.env.PROXY_HOST;
  const port = parseInt(process.env.PROXY_PORT ?? "0", 10);
  const username = process.env.PROXY_USERNAME;
  const password = process.env.PROXY_PASSWORD;

  if (!host || !port || !username || !password) {
    return null;
  }

  return {
    host,
    port,
    username,
    password,
    protocol: (process.env.PROXY_PROTOCOL as "http" | "socks5") ?? "http",
    country: process.env.PROXY_COUNTRY ?? "us",
    rotateOnSuccess: parseInt(process.env.WORKER_ROTATE_ON_SUCCESS ?? "3", 10),
  };
}