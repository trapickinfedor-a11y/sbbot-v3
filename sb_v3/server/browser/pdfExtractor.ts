/**
 * PDF extractor for Adverse Action Notice documents.
 * Primary: direct text file reading (already extracted .txt files)
 * Secondary: pdfminer subprocess for .pdf files
 * Features: batch processing, adverse reason parsing, CRA detection
 */
import { readdirSync, readFileSync, writeFileSync, unlinkSync } from "fs";
import { join, dirname, extname } from "path";
import { fileURLToPath } from "url";

const SCORE_PATTERNS = [
  /Your credit score:\s*(\d{3})/i,
  /credit score[.:\s]+(\d{3})/i,
];

const REASON_SECTION_START = /Key factors that adversely affected your credit score:/i;
const REASON_SECTION_END = /\n\s*\n|\nSincerely|\nNOTICE/i;
const REASON_LINE_PREFIX = /^\d+\.\s*/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/m;
const NAME_PATTERN = /^Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/m;
const CRA_PATTERN = /(TransUnion|Consumer Solutions|Experian|Equifax)/i;

export interface ExtractedNotice {
  filename: string;
  score: number | null;
  reasons: string[];
  rawText: string;
  cra: string | null;
  date: string | null;
  applicantName: string | null;
  source: string;
}

export interface BatchResult {
  total: number;
  succeeded: number;
  failed: number;
  notices: ExtractedNotice[];
  errors: Array<{ filename: string; error: string }>;
}

function extractScore(text: string): number | null {
  for (const pat of SCORE_PATTERNS) {
    const m = text.match(pat);
    if (m) {
      const score = parseInt(m[1], 10);
      if (score >= 300 && score <= 850) return score;
    }
  }
  return null;
}

function extractReasons(text: string): string[] {
  const re = new RegExp(`${REASON_SECTION_START.source}([\\s\\S]+?)${REASON_SECTION_END.source}`);
  const m = text.match(re);
  if (!m) return [];
  return m[1]
    .split("\n")
    .map(line => line.replace(REASON_LINE_PREFIX, "").trim())
    .filter(line => line.length > 5 && line.length < 200);
}

function extractName(text: string): string | null {
  const m = text.match(NAME_PATTERN);
  return m ? m[1].trim() : null;
}

function extractCra(text: string): string | null {
  const m = text.match(CRA_PATTERN);
  return m ? m[1] : null;
}

function extractDate(text: string): string | null {
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  for (const line of lines) {
    if (DATE_PATTERN.test(line)) return line;
  }
  return null;
}

export async function extractFromTextFile(filePath: string): Promise<ExtractedNotice> {
  const filename = filePath.split("/").pop() ?? filePath;
  const rawText = readFileSync(filePath, "utf-8");

  return {
    filename,
    score: extractScore(rawText),
    reasons: extractReasons(rawText),
    rawText,
    cra: extractCra(rawText),
    date: extractDate(rawText),
    applicantName: extractName(rawText),
    source: "text_file",
  };
}

export async function extractFromPdf(filePath: string): Promise<ExtractedNotice> {
  const filename = filePath.split("/").pop() ?? filePath;
  try {
    const { execSync } = require("child_process") as any;
    const script = [
      "from pdfminer.high_level import extract_text",
      "import sys",
      "print(extract_text(sys.argv[1]), end='')",
    ].join("\n");
    const tmp = `/tmp/pdf_extract_${Date.now()}.py`;
    writeFileSync(tmp, script);
    const rawText = execSync(`python3 "${tmp}" "${filePath}"`, { timeout: 15000 }).toString();
    try { unlinkSync(tmp); } catch { /* ignore */ }

    return {
      filename,
      score: extractScore(rawText),
      reasons: extractReasons(rawText),
      rawText,
      cra: extractCra(rawText),
      date: extractDate(rawText),
      applicantName: extractName(rawText),
      source: "pdfminer",
    };
  } catch {
    throw new Error(`pdfminer extraction failed for ${filename}`);
  }
}

export async function batchExtract(filePaths: string[], concurrency = 4): Promise<BatchResult> {
  const notices: ExtractedNotice[] = [];
  const errors: Array<{ filename: string; error: string }> = [];

  for (let i = 0; i < filePaths.length; i += concurrency) {
    const chunk = filePaths.slice(i, i + concurrency);
    const results = await Promise.allSettled(
      chunk.map(async (fp) => {
        const ext = extname(fp).toLowerCase();
        if (ext === ".txt") return extractFromTextFile(fp);
        if (ext === ".pdf") return extractFromPdf(fp);
        throw new Error(`Unsupported format: ${ext}`);
      }),
    );
    for (let j = 0; j < results.length; j++) {
      const r = results[j];
      if (r.status === "fulfilled") notices.push(r.value);
      else errors.push({ filename: chunk[j], error: String(r.reason) });
    }
  }

  return { total: filePaths.length, succeeded: notices.length, failed: errors.length, notices, errors };
}

export function validateNotice(n: ExtractedNotice): { valid: boolean; issues: string[] } {
  const issues: string[] = [];
  if (n.score !== null && (n.score < 300 || n.score > 850)) {
    issues.push(`Score ${n.score} out of range`);
  }
  if (n.reasons.length === 0) issues.push("No adverse reasons extracted");
  if (!n.applicantName) issues.push("Applicant name not found");
  if (!n.cra) issues.push("CRA not identified");
  return { valid: issues.length === 0, issues };
}

export function validateExtractedNotice(n: ExtractedNotice): { valid: boolean; issues: string[] } {
  return validateNotice(n);
}