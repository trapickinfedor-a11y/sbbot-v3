import { describe, expect, it } from "vitest";
import { readdirSync } from "fs";
import { join, extname } from "path";
import {
  extractFromTextFile,
  batchExtract,
  validateExtractedNotice,
  type ExtractedNotice,
} from "./pdfExtractor";

const TXT_DIR = join(process.cwd(), "user_attachment/extracted/ved/txt");

function getTxtFiles(): string[] {
  return readdirSync(TXT_DIR)
    .filter(f => extname(f).toLowerCase() === ".txt")
    .map(f => join(TXT_DIR, f))
    .sort();
}

describe("extractFromTextFile", () => {
  const txtFiles = getTxtFiles();
  const firstFile = txtFiles[0];

  it("loads a real .txt file and returns a structured notice", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice).toMatchObject({
      filename: expect.stringContaining("Adverse Action Notice"),
      rawText: expect.any(String),
      source: "text_file",
    });
    expect(notice.rawText.length).toBeGreaterThan(200);
  });

  it("extracts credit score from real file", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice.score).not.toBeNull();
    expect(notice.score).toBeGreaterThanOrEqual(300);
    expect(notice.score).toBeLessThanOrEqual(850);
  });

  it("extracts adverse reasons from real file", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice.reasons.length).toBeGreaterThan(0);
  });

  it("extracts CRA from real file", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice.cra).toBeTruthy();
  });

  it("extracts applicant name from real file", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice.applicantName).toBeTruthy();
    expect(notice.applicantName).toMatch(/^[A-Z][a-z]+ [A-Z][a-z]+/);
  });

  it("extracts date from real file", async () => {
    const notice = await extractFromTextFile(firstFile);
    expect(notice.date).toBeTruthy();
    expect(notice.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("throws for non-existent file", async () => {
    await expect(extractFromTextFile("/nonexistent/file.txt")).rejects.toThrow();
  });
});

describe("score extraction across all 52 files", () => {
  const txtFiles = getTxtFiles();

  it("processes all 52 txt files", async () => {
    expect(txtFiles.length).toBe(52);
  });

  it("45+ files have credit scores extracted", async () => {
    const result = await batchExtract(txtFiles);
    const withScores = result.notices.filter(n => n.score !== null);
    expect(withScores.length).toBeGreaterThanOrEqual(45);
  });

  it("all extracted scores are in valid range 300-850", async () => {
    const result = await batchExtract(txtFiles);
    for (const notice of result.notices) {
      if (notice.score !== null) {
        expect(notice.score).toBeGreaterThanOrEqual(300);
        expect(notice.score).toBeLessThanOrEqual(850);
      }
    }
  });

  it("no file processing errors", async () => {
    const result = await batchExtract(txtFiles);
    expect(result.failed).toBe(0);
    expect(result.errors).toHaveLength(0);
  });
});

describe("reason extraction", () => {
  it("extracts reasons from real file with multiple reasons", async () => {
    const txtFiles = getTxtFiles();
    const notice = await extractFromTextFile(txtFiles[0]);
    expect(notice.reasons.length).toBeGreaterThanOrEqual(1);
    for (const reason of notice.reasons) {
      expect(reason.length).toBeGreaterThan(5);
      expect(reason.length).toBeLessThan(200);
    }
  });

  it("returns array (empty or not) for any file without throwing", async () => {
    const txtFiles = getTxtFiles();
    for (const fp of txtFiles) {
      const notice = await extractFromTextFile(fp);
      expect(Array.isArray(notice.reasons)).toBe(true);
    }
  });
});

describe("batchExtract with concurrency=4", () => {
  const txtFiles = getTxtFiles();

  it("processes all 52 files with concurrency=4", async () => {
    const result = await batchExtract(txtFiles, 4);
    expect(result.total).toBe(52);
    expect(result.succeeded).toBe(52);
    expect(result.failed).toBe(0);
    expect(result.notices).toHaveLength(52);
  });

  it("returns proper BatchExtractionResult shape", async () => {
    const result = await batchExtract(txtFiles.slice(0, 8), 4);
    expect(result).toMatchObject({
      total: 8,
      succeeded: 8,
      failed: 0,
      notices: expect.any(Array),
      errors: expect.any(Array),
    });
  });
});

describe("validateExtractedNotice", () => {
  it("returns valid=true for a complete notice from real file", async () => {
    const txtFiles = getTxtFiles();
    const notice = await extractFromTextFile(txtFiles[0]);
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(true);
    expect(validation.issues).toHaveLength(0);
  });

  it("null score is allowed (some real files have no score)", async () => {
    const notice: ExtractedNotice = {
      filename: "test.txt",
      score: null,
      reasons: ["Insufficient credit history"],
      rawText: "Dear Test User",
      cra: "TransUnion",
      date: "2026-03-09",
      applicantName: "Test User",
      source: "text_file",
    };
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(true);
  });

  it("detects out-of-range score", async () => {
    const notice: ExtractedNotice = {
      filename: "test.txt",
      score: 999,
      reasons: ["Insufficient credit history"],
      rawText: "Dear Test User",
      cra: "TransUnion",
      date: "2026-03-09",
      applicantName: "Test User",
      source: "text_file",
    };
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(false);
    expect(validation.issues).toContain("Score 999 out of range");
  });

  it("detects missing reasons", async () => {
    const notice: ExtractedNotice = {
      filename: "test.txt",
      score: 768,
      reasons: [],
      rawText: "Dear Test User",
      cra: "TransUnion",
      date: "2026-03-09",
      applicantName: "Test User",
      source: "text_file",
    };
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(false);
    expect(validation.issues).toContain("No adverse reasons extracted");
  });

  it("detects missing applicant name", async () => {
    const notice: ExtractedNotice = {
      filename: "test.txt",
      score: 768,
      reasons: ["Insufficient credit history"],
      rawText: "Dear Test User",
      cra: "TransUnion",
      date: "2026-03-09",
      applicantName: null,
      source: "text_file",
    };
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(false);
    expect(validation.issues).toContain("Applicant name not found");
  });

  it("detects missing CRA", async () => {
    const notice: ExtractedNotice = {
      filename: "test.txt",
      score: 768,
      reasons: ["Insufficient credit history"],
      rawText: "Dear Test User",
      cra: null,
      date: "2026-03-09",
      applicantName: "Test User",
      source: "text_file",
    };
    const validation = validateExtractedNotice(notice);
    expect(validation.valid).toBe(false);
    expect(validation.issues).toContain("CRA not identified");
  });
});

describe("CRA detection", () => {
  const txtFiles = getTxtFiles();

  it("detects TransUnion from real notices", async () => {
    const notice = await extractFromTextFile(txtFiles[0]);
    expect(notice.cra).toMatch(/TransUnion/i);
  });

  it("all 52 files have CRA identified", async () => {
    const result = await batchExtract(txtFiles);
    const withoutCra = result.notices.filter(n => n.cra === null);
    expect(withoutCra).toHaveLength(0);
  });
});

describe("name extraction", () => {
  const txtFiles = getTxtFiles();

  it("extracts names from all real files", async () => {
    const result = await batchExtract(txtFiles);
    const withoutName = result.notices.filter(n => n.applicantName === null);
    expect(withoutName).toHaveLength(0);
  });

  it("extracted names match First Last format", async () => {
    const notice = await extractFromTextFile(txtFiles[0]);
    expect(notice.applicantName).toMatch(/^[A-Z][a-z]+ [A-Z][a-z]+/);
  });
});

describe("date extraction", () => {
  const txtFiles = getTxtFiles();

  it("extracts date from all real files", async () => {
    const result = await batchExtract(txtFiles);
    const withoutDate = result.notices.filter(n => n.date === null);
    expect(withoutDate).toHaveLength(0);
  });

  it("extracted dates match YYYY-MM-DD format", async () => {
    const notice = await extractFromTextFile(txtFiles[0]);
    expect(notice.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("dates correspond to March 2026 documents", async () => {
    const result = await batchExtract(txtFiles);
    for (const notice of result.notices) {
      if (notice.date) {
        expect(notice.date).toMatch(/^2026-03-/);
      }
    }
  });
});
