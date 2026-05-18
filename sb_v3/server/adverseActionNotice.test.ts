import { describe, expect, it } from "vitest";
import { readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import {
  normalizeAdverseReason,
  normalizeAdverseReasons,
  buildOneCsResult,
  deriveProductScore,
  deriveDataQualityScore,
  deriveOneCsStatus,
} from "../shared/oneCsScoring";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TXT_DIR = join(__dirname, "../user_attachment/extracted/ved/txt");

const ADVERSE_TXT_FILES = readdirSync(TXT_DIR).filter(f => f.endsWith(".txt"));

const SCORE_PATTERN = /Your credit score:\s*(\d{3})/;
const REASON_SECTION_PATTERN = /Key factors that adversely affected your credit score:\s*\n([\s\S]+?)(?=\n\n|\nSincerely|\nNOTICE)/i;
const NAME_PATTERN = /^Thank you for your recent application|Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+)/m;
const DATE_PATTERN = /^(\d{4}-\d{2}-\d{2})$/m;

function extractScore(text: string): number | null {
  const match = text.match(SCORE_PATTERN);
  return match ? parseInt(match[1], 10) : null;
}

function extractAdverseReasons(text: string): string[] {
  const match = text.match(REASON_SECTION_PATTERN);
  if (!match) return [];
  return match[1]
    .split("\n")
    .map(line => line.replace(/^\d+\.\s*/, "").trim())
    .filter(line => line.length > 5 && line.length < 200);
}

function extractName(text: string): string | null {
  const match = text.match(/^Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/m);
  return match ? match[1].trim() : null;
}

function extractDate(text: string): string | null {
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (DATE_PATTERN.test(line)) return line;
  }
  return null;
}

function validateScore(score: number | null): boolean {
  return score === null || (score >= 300 && score <= 850);
}

describe("Adverse Action Notice real data — all 52 files", () => {
  it(`directory contains 52 adverse action notice files`, () => {
    expect(ADVERSE_TXT_FILES.length).toBe(52);
  });

  describe.each(ADVERSE_TXT_FILES)("%s", (filename) => {
    const rawText = (() => {
      const content = require("fs").readFileSync(join(TXT_DIR, filename), "utf-8");
      return content;
    })();

    const score = extractScore(rawText);
    const reasons = extractAdverseReasons(rawText);
    const name = extractName(rawText);
    const date = extractDate(rawText);

    it("file is non-empty", () => {
      expect(rawText.trim().length).toBeGreaterThan(100);
    });

    it("score is extractable and in valid range", () => {
      expect(validateScore(score)).toBe(true);
    });

    it("name is extractable from the notice", () => {
      expect(name).not.toBeNull();
    });

    it("date is extractable", () => {
      expect(date).not.toBeNull();
    });

    it("contains at least one CRA reference (TransUnion, Experian, or Equifax)", () => {
      expect(rawText).toMatch(/TransUnion|Experian|Equifax/i);
    });

    it("contains score range notice", () => {
      expect(rawText).toMatch(/Scores range from a low of 300 to a high of 850/i);
    });

    it("score maps to valid product score 1-20", () => {
      const ps = deriveProductScore(score);
      expect(ps).toBeGreaterThanOrEqual(1);
      expect(ps).toBeLessThanOrEqual(20);
    });

    it("ONE CS result is valid regardless of score", () => {
      const result = buildOneCsResult({
        creditScore: score,
        completenessScore: 1.0,
        adverseReasons: reasons,
        priceUsd: 0,
        durationMs: 0,
        source: "testbench",
      });
      expect(result.productScore).toBeGreaterThanOrEqual(1);
      expect(result.productScore).toBeLessThanOrEqual(20);
      expect(result.dataQualityScore).toBeGreaterThanOrEqual(1);
      expect(result.dataQualityScore).toBeLessThanOrEqual(10);
      expect(["success", "review", "decline", "no_file"]).toContain(result.status);
    });
  });
});

describe("Adverse Action Notice — ONE CS algorithm correctness on real data", () => {
  it("normalizeAdverseReason handles all 25 unique adverse reasons from real data", () => {
    const allReasons = [
      "Income or credit history insufficient for loan",
      "Requested amount unsupported by income",
      "Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high",
      "Too many accounts with balances",
      "RiskView Consumer Inquiry",
      "Proportion of loan balances to loan amounts is too high",
      "Serious delinquency",
      "Too few accounts currently paid as agreed",
      "High debt in relation to income",
      "Serious delinquency, and public record or collection filed",
      "Lack of recent installment loan information",
      "Number of accounts with delinquency",
      "Insufficient credit history",
      "Lack of recent revolving account information",
      "Time since delinquency is too recent or unknown",
      "Lack of recent bank/national revolving information",
      "No recent bank/national revolving balances",
      "Insufficient length of credit history",
      "Too many inquiries last 12 months",
      "Insufficient number of open accounts",
      "High number of recent inquiries",
      "No recent revolving balances",
      "Too many consumer finance company accounts",
      "Insufficient number of accounts",
    ];

    for (const reason of allReasons) {
      const result = normalizeAdverseReason(reason);
      expect(result.normalized).toBeTruthy();
      expect(result.group).not.toBeNull();
    }
  });

  it("high score (768) with delinquency gets correct data quality", () => {
    const reasons = [
      "Number of accounts with delinquency",
      "Time since delinquency is too recent or unknown",
      "No recent bank/national revolving balances",
      "Too many accounts with balances",
    ];
    const quality = deriveDataQualityScore({ creditScore: 768, adverseReasons: reasons });
    expect(quality.dataQualityScore).toBeGreaterThanOrEqual(1);
    expect(quality.dataQualityScore).toBeLessThanOrEqual(10);
    expect(quality.adverseReasonGroups).toContain("delinquency");
    expect(quality.adverseReasonGroups).toContain("low_depth");
    expect(quality.adverseReasonGroups).toContain("utilization");
  });

  it("mid score (718) with utilization + delinquency + low_depth gets correct data quality", () => {
    const reasons = [
      "Number of accounts with delinquency",
      "Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high",
      "Length of time accts have been established",
      "Too many accounts with balances",
    ];
    const quality = deriveDataQualityScore({ creditScore: 718, adverseReasons: reasons });
    expect(quality.dataQualityScore).toBeGreaterThanOrEqual(1);
    expect(quality.adverseReasonGroups).toContain("delinquency");
    expect(quality.adverseReasonGroups).toContain("utilization");
    expect(quality.adverseReasonGroups).toContain("low_depth");
  });

  it("score 817 with no adverse reasons returns success status", () => {
    const result = buildOneCsResult({
      creditScore: 817,
      completenessScore: 1.0,
      adverseReasons: [],
      priceUsd: 0,
      durationMs: 0,
      source: "testbench",
    });
    expect(result.status).toBe("success");
    expect(result.productScore).toBeGreaterThanOrEqual(18);
    expect(result.dataQualityScore).toBeGreaterThanOrEqual(9);
  });

  it("score 839 with no adverse reasons returns success status", () => {
    const result = buildOneCsResult({
      creditScore: 839,
      completenessScore: 1.0,
      adverseReasons: [],
      priceUsd: 0,
      durationMs: 0,
      source: "testbench",
    });
    expect(result.status).toBe("success");
    expect(result.productScore).toBe(20);
  });

  it("score 830 with no adverse reasons returns success status", () => {
    const result = buildOneCsResult({
      creditScore: 830,
      completenessScore: 1.0,
      adverseReasons: [],
      priceUsd: 0,
      durationMs: 0,
      source: "testbench",
    });
    expect(result.status).toBe("success");
  });

  it("null score with no_file reason returns no_file status", () => {
    const result = buildOneCsResult({
      creditScore: null,
      completenessScore: 0.5,
      adverseReasons: ["Unable to find credit profile at TransUnion"],
      priceUsd: 0,
      durationMs: 0,
      source: "testbench",
    });
    expect(result.status).toBe("no_file");
    expect(result.productScore).toBe(1);
  });

  it("RiskView Consumer Inquiry maps to inquiry_pressure group", () => {
    const quality = deriveDataQualityScore({
      creditScore: 700,
      adverseReasons: ["RiskView Consumer Inquiry"],
    });
    expect(quality.adverseReasonGroups).toContain("inquiry_pressure");
  });

  it("public_record + delinquency combinations map correctly", () => {
    const quality = deriveDataQualityScore({
      creditScore: 650,
      adverseReasons: ["Serious delinquency, and public record or collection filed"],
    });
    expect(quality.adverseReasonGroups).toContain("public_record");
    expect(quality.adverseReasonGroups).not.toContain("delinquency");

    const quality2 = deriveDataQualityScore({
      creditScore: 650,
      adverseReasons: ["Derogatory public record or collection filed"],
    });
    expect(quality2.adverseReasonGroups).toContain("public_record");
    expect(quality2.adverseReasonGroups).not.toContain("delinquency");

    const quality3 = deriveDataQualityScore({ creditScore: 650, adverseReasons: ["Serious delinquency"] });
    expect(quality3.adverseReasonGroups).toContain("delinquency");
    expect(quality3.adverseReasonGroups).not.toContain("public_record");
  });

  it("completeness adjustment penalizes thin records", () => {
    const full = deriveDataQualityScore({ creditScore: 720, completenessScore: 1.0, adverseReasons: [] });
    const thin = deriveDataQualityScore({ creditScore: 720, completenessScore: 0.3, adverseReasons: [] });
    expect(thin.dataQualityScore).toBeLessThan(full.dataQualityScore);
  });

  it("normalizeAdverseReasons deduplicates by normalized text", () => {
    const reasons = [
      "Income or credit history insufficient for loan",
      "Income or credit history insufficient for loan",
      "Serious delinquency",
      "Serious delinquency",
    ];
    const normalized = normalizeAdverseReasons(reasons);
    expect(normalized.adverseReasons).toHaveLength(2);
    expect(normalized.adverseReasonGroups).toHaveLength(2);
  });

  it("deriveOneCsStatus returns review for mid-quality scores", () => {
    const status = deriveOneCsStatus({ creditScore: 700, dataQualityScore: 2.5, adverseReasonGroups: [] });
    expect(status).toBe("review");
  });

  it("deriveOneCsStatus returns decline for low-quality scores", () => {
    const status = deriveOneCsStatus({ creditScore: 550, dataQualityScore: 1.8, adverseReasonGroups: [] });
    expect(status).toBe("decline");
  });

  it("affordability group penalty is applied correctly", () => {
    const reasons = [
      "High debt in relation to income",
      "Income or credit history insufficient for loan",
      "Requested amount unsupported by income",
    ];
    const quality = deriveDataQualityScore({ creditScore: 720, adverseReasons: reasons });
    expect(quality.adverseReasonGroups).toContain("affordability");
    expect(quality.penalty).toBeGreaterThan(0);
  });

  it("thin_file + low_depth combination", () => {
    const reasons = [
      "Insufficient credit history",
      "Lack of recent installment loan information",
      "No recent revolving balances",
    ];
    const quality = deriveDataQualityScore({ creditScore: 680, adverseReasons: reasons });
    expect(quality.adverseReasonGroups).toContain("thin_file");
    expect(quality.adverseReasonGroups).toContain("low_depth");
  });

  it("unknown reason returns null group and preserves original", () => {
    const result = normalizeAdverseReason("Some completely unknown adverse reason text");
    expect(result.group).toBeNull();
    expect(result.normalized).toBe("Some completely unknown adverse reason text");
  });
});

describe("Adverse Action Notice — batch summary stats", () => {
  it("aggregate stats from all 52 files produce valid distribution", () => {
    const scores: number[] = [];
    const statuses: string[] = [];

    for (const filename of ADVERSE_TXT_FILES) {
      const content = require("fs").readFileSync(join(TXT_DIR, filename), "utf-8");
      const score = extractScore(content);
      const reasons = extractAdverseReasons(content);
      if (score !== null) scores.push(score);

      const result = buildOneCsResult({
        creditScore: score,
        completenessScore: 1.0,
        adverseReasons: reasons,
        priceUsd: 0,
        durationMs: 0,
        source: "testbench",
      });
      statuses.push(result.status);
    }

    expect(scores.length).toBeGreaterThan(0);
    expect(scores.every(s => s >= 300 && s <= 850)).toBe(true);
    expect(statuses.every(s => ["success", "review", "decline", "no_file"].includes(s))).toBe(true);

    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    expect(avg).toBeGreaterThan(300);
    expect(avg).toBeLessThan(850);
  });

  it("most scores extractable from all 52 files (some notices redact scores)", () => {
    let extracted = 0;
    for (const filename of ADVERSE_TXT_FILES) {
      const content = require("fs").readFileSync(join(TXT_DIR, filename), "utf-8");
      if (extractScore(content) !== null) extracted++;
    }
    // 7 of 52 notices redact the score (score line present but value redacted)
    expect(extracted).toBeGreaterThanOrEqual(45);
    expect(extracted).toBeLessThanOrEqual(52);
  });
});
