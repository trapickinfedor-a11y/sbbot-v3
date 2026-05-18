import { readdirSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { buildOneCsResult } from "./shared/oneCsScoring.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TXT_DIR = join(__dirname, "user_attachment/extracted/ved/txt");
const FILES = readdirSync(TXT_DIR).filter(f => f.endsWith(".txt"));

const SCORE_RE = /Your credit score:\s*(\d{3})/;
const REASON_SECTION_RE = /Key factors that adversely affected your credit score:\s*\n([\s\S]+?)(?=\n\n|\nSincerely|\nNOTICE)/i;

function extractScore(text) {
  const m = text.match(SCORE_RE);
  return m ? parseInt(m[1], 10) : null;
}

function extractReasons(text) {
  const m = text.match(REASON_SECTION_RE);
  if (!m) return [];
  return m[1].split("\n").map(l => l.replace(/^\d+\.\s*/, "").trim()).filter(l => l.length > 5);
}

// Parallel processing of all 52 files — maximum throughput
const startAll = Date.now();
const CHUNK_SIZE = 8;

const chunks = [];
for (let i = 0; i < FILES.length; i += CHUNK_SIZE) {
  chunks.push(FILES.slice(i, i + CHUNK_SIZE));
}

const allResults = [];
let chunkIndex = 0;

for (const chunk of chunks) {
  const chunkStart = Date.now();
  const results = await Promise.all(chunk.map(async (filename) => {
    const content = readFileSync(join(TXT_DIR, filename), "utf-8");
    const score = extractScore(content);
    const reasons = extractReasons(content);
    const nameMatch = content.match(/^Dear\s+([A-Z][a-z]+\s+[A-Z][a-z]+)/m);
    const craMatch = content.match(/(TransUnion|Experian|Equifax)/i);
    const dateMatch = content.match(/^(\d{4}-\d{2}-\d{2})$/m);

    const oneCs = buildOneCsResult({
      creditScore: score,
      completenessScore: 1.0,
      adverseReasons: reasons,
      priceUsd: 0,
      durationMs: 0,
      source: "testbench",
    });

    return { filename, score, reasons: reasons.length, name: nameMatch?.[1] ?? "?", cra: craMatch?.[1] ?? "?", date: dateMatch?.[1] ?? "?", oneCs };
  }));
  allResults.push(...results);
  console.log(`  Chunk ${++chunkIndex}/${chunks.length} (${chunk.length} files, ${(Date.now() - chunkStart).toFixed(0)}ms)`);
}

const totalMs = Date.now() - startAll;

// Report
console.log("\n" + "=".repeat(80));
console.log("  ADVERSE ACTION NOTICE PIPELINE — FULL 52-FILE RUN");
console.log("=".repeat(80));
console.log(`  Total files:    ${allResults.length}`);
console.log(`  Total time:    ${totalMs}ms (${(totalMs / 1000).toFixed(2)}s)`);
console.log(`  Throughput:     ${(allResults.length / (totalMs / 1000)).toFixed(1)} files/sec`);
console.log();

const scores = allResults.map(r => r.score).filter(s => s !== null);
const avg = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "N/A";
const min = scores.length > 0 ? Math.min(...scores) : "N/A";
const max = scores.length > 0 ? Math.max(...scores) : "N/A";

const statuses = allResults.map(r => r.oneCs.status);
const success = statuses.filter(s => s === "success").length;
const review = statuses.filter(s => s === "review").length;
const decline = statuses.filter(s => s === "decline").length;
const noFile = statuses.filter(s => s === "no_file").length;

console.log(`  SCORE DISTRIBUTION (${scores.length} extracted)`);
console.log(`    Average: ${avg}  |  Min: ${min}  |  Max: ${max}`);
console.log();

console.log(`  ONE CS STATUS DISTRIBUTION`);
console.log(`    success: ${success}  |  review: ${review}  |  decline: ${decline}  |  no_file: ${noFile}`);
console.log();

// Adverse reason group frequency
const groupCounts = {};
for (const r of allResults) {
  for (const g of r.oneCs.adverseReasonGroups) {
    groupCounts[g] = (groupCounts[g] || 0) + 1;
  }
}
console.log(`  ADVERSE REASON GROUPS (across all 52 files)`);
const sortedGroups = Object.entries(groupCounts).sort((a, b) => b[1] - a[1]);
for (const [group, count] of sortedGroups) {
  const bar = "█".repeat(Math.round(count / 52 * 40));
  console.log(`    ${group.padEnd(20)} ${String(count).padStart(2)}/52  ${bar}`);
}
console.log();

// CRA breakdown
const craCounts = {};
for (const r of allResults) {
  craCounts[r.cra] = (craCounts[r.cra] || 0) + 1;
}
console.log(`  CRA BREAKDOWN`);
for (const [cra, count] of Object.entries(craCounts).sort((a, b) => b[1] - a[1])) {
  console.log(`    ${cra.padEnd(20)} ${count}/52`);
}
console.log();

// Product score distribution
const psBuckets = { "1-5": 0, "6-10": 0, "11-15": 0, "16-20": 0 };
for (const r of allResults) {
  const ps = r.oneCs.productScore;
  if (ps <= 5) psBuckets["1-5"]++;
  else if (ps <= 10) psBuckets["6-10"]++;
  else if (ps <= 15) psBuckets["11-15"]++;
  else psBuckets["16-20"]++;
}
console.log(`  PRODUCT SCORE DISTRIBUTION`);
for (const [bucket, count] of Object.entries(psBuckets)) {
  const bar = "█".repeat(Math.round(count / 52 * 40));
  console.log(`    ${bucket.padEnd(10)} ${String(count).padStart(2)}/52  ${bar}`);
}
console.log();

// Sample of all records
console.log(`  DETAILED RECORDS (${allResults.length} total)`);
console.log(`  #   Name                    Score  PS  DQ   Status   CRA`);
console.log(`  ${"-".repeat(70)}`);
for (let i = 0; i < allResults.length; i++) {
  const r = allResults[i];
  const scoreStr = r.score !== null ? String(r.score) : "N/A";
  console.log(
    `  ${String(i+1).padStart(2)}. ${(r.name ?? "?").slice(0,20).padEnd(20)} ` +
    `${scoreStr.padStart(4)}  ${String(r.oneCs.productScore).padStart(2)} ` +
    `${r.oneCs.dataQualityScore.toFixed(1).padStart(4)}  ${r.oneCs.status.padEnd(8)} ${r.cra}`
  );
}
console.log("=".repeat(80));