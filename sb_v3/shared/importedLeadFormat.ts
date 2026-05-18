import { z } from "zod";
import { buildOneCsResult, oneCsResultSchema } from "./oneCsScoring";

const emailPattern = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const phonePattern = /\(\d{3}\)\s*\d{3}-\d{4}/g;
const scorePattern = /credit score:\s*(\d{3})/i;
const agePattern = /^(\d{1,3})\s+years?\s+old/i;
const ageLabelPattern = /^AGE:\s*(\d{1,3})/i;
const dobPattern = /^DOB:\s*(.+)$/i;
const bornPattern = /^BORN:\s*(.+)$/i;
const ssnPattern = /^SSN:\s*(.+)$/i;
const headerPattern = /\[[^\]]+\]$/;
const stateZipPattern = /,?\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?$/;

export const importedLeadRecordSchema = z.object({
  blockIndex: z.number().int().min(1),
  sourceLabel: z.string().nullable(),
  fullName: z.string().min(1),
  addressRaw: z.string().nullable(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  postalCode: z.string().nullable(),
  age: z.number().int().nullable(),
  bornText: z.string().nullable(),
  dobText: z.string().nullable(),
  hasSsn: z.boolean(),
  email: z.string().nullable(),
  emailDomain: z.string().nullable(),
  phoneNumbers: z.array(z.string()),
  creditScore: z.number().int().nullable(),
  flags: z.array(z.string()),
  completenessScore: z.number().min(0).max(1),
  oneCsResult: oneCsResultSchema,
});

export const safeImportedLeadRecordSchema = importedLeadRecordSchema.extend({
  fullName: z.string(),
  email: z.null(),
  phoneNumbers: z.array(z.string()),
  normalizedTarget: z.string(),
  piiRedacted: z.literal(true),
});

export type ImportedLeadRecord = z.infer<typeof importedLeadRecordSchema>;
export type SafeImportedLeadRecord = z.infer<typeof safeImportedLeadRecordSchema>;

function compactWhitespace(value: string) {
  return value.replace(/\s+/g, " ").trim();
}

function isSourceHeader(line: string) {
  return line.includes(", [") || headerPattern.test(line);
}

function shouldTreatFirstLineAsSourceHeader(lines: string[]) {
  if (lines.length < 3) return false;

  const [first, second, third] = lines;
  if (!first || !second || !third) return false;

  return isLikelyName(first) && isLikelyName(second) && !isLikelyName(third);
}

function isLikelyName(line: string) {
  return /^[A-Za-z][A-Za-z'?. -]+$/.test(line) && !/^DOB:/i.test(line) && !/^SSN:/i.test(line);
}

function extractEmailDomain(email: string | null) {
  if (!email || !email.includes("@")) return null;
  return email.split("@")[1]?.toLowerCase() ?? null;
}

function maskName(fullName: string) {
  const tokens = compactWhitespace(fullName).split(" ").filter(Boolean);
  return tokens
    .map(token => {
      const [firstChar = "X", ...restChars] = Array.from(token);
      const maskedRest = restChars
        .map(char => (/^[A-Za-z0-9]$/.test(char) ? "*" : char))
        .join("");
      return `${firstChar.toUpperCase()}${maskedRest}`;
    })
    .join(" ");
}

function maskPhone(phone: string) {
  const digits = phone.replace(/\D/g, "");
  const last2 = digits.slice(-2).padStart(2, "0");
  return `(***) ***-**${last2}`;
}

function parseAddress(addressLines: string[]) {
  if (addressLines.length === 0) {
    return {
      addressRaw: null,
      city: null,
      state: null,
      postalCode: null,
    };
  }

  const addressRaw = compactWhitespace(addressLines.join(", "));
  const stateZipMatch = addressRaw.match(stateZipPattern);

  let state: string | null = null;
  let postalCode: string | null = null;
  let city: string | null = null;

  if (stateZipMatch) {
    state = stateZipMatch[1] ?? null;
    postalCode = stateZipMatch[2] ?? null;
    const beforeState = addressRaw.slice(0, stateZipMatch.index).trim();
    const segments = beforeState.split(",").map(segment => compactWhitespace(segment)).filter(Boolean);
    city = segments.length > 0 ? segments[segments.length - 1] ?? null : null;
  }

  return {
    addressRaw,
    city,
    state,
    postalCode,
  };
}

function parseBlock(block: string, blockIndex: number): ImportedLeadRecord | null {
  const rawLines = block
    .split(/\r?\n/)
    .map(line => compactWhitespace(line))
    .filter(Boolean);

  if (rawLines.length === 0) return null;

  let sourceLabel: string | null = null;
  const lines = [...rawLines];

  if (isSourceHeader(lines[0] ?? "") || shouldTreatFirstLineAsSourceHeader(lines)) {
    sourceLabel = lines.shift() ?? null;
  }

  const fullName = lines.shift();
  if (!fullName || !isLikelyName(fullName)) {
    return null;
  }

  const addressLines: string[] = [];
  const phoneNumbers = new Set<string>();
  const flags = new Set<string>();
  let age: number | null = null;
  let bornText: string | null = null;
  let dobText: string | null = null;
  let hasSsn = false;
  let email: string | null = null;
  let creditScore: number | null = null;

  for (const line of lines) {
    const upperLine = line.toUpperCase();
    if (upperLine === "NF") {
      flags.add("no_phone_or_email_marker");
      continue;
    }

    if (line.includes("?")) {
      flags.add("contains_uncertain_marker");
    }

    const ageMatch = line.match(agePattern) ?? line.match(ageLabelPattern);
    if (ageMatch) {
      age = Number(ageMatch[1]);
      continue;
    }

    const bornMatch = line.match(bornPattern);
    if (bornMatch) {
      bornText = compactWhitespace(bornMatch[1] ?? "");
      continue;
    }

    const dobMatch = line.match(dobPattern);
    if (dobMatch) {
      dobText = compactWhitespace(dobMatch[1] ?? "");
      continue;
    }

    if (ssnPattern.test(line)) {
      hasSsn = true;
      continue;
    }

    const emailMatch = line.match(emailPattern);
    if (emailMatch) {
      email = emailMatch[0].toLowerCase();
      continue;
    }

    const phoneMatches = Array.from(line.matchAll(phonePattern), match => match[0]);
    if (phoneMatches.length > 0) {
      phoneMatches.forEach(match => phoneNumbers.add(match));
      continue;
    }

    const scoreMatch = line.match(scorePattern);
    if (scoreMatch) {
      creditScore = Number(scoreMatch[1]);
      continue;
    }

    addressLines.push(line);
  }

  const address = parseAddress(addressLines.slice(0, 2));
  const completenessSignals = [address.addressRaw, age, dobText, email, phoneNumbers.size > 0 ? "phones" : null, creditScore, hasSsn ? "ssn" : null];
  const completenessScore = Number(
    (
      completenessSignals.filter(Boolean).length / completenessSignals.length
    ).toFixed(2),
  );

  const inferredAdverseReasons: string[] = [];
  if (creditScore === null) {
    inferredAdverseReasons.push("Insufficient credit history");
  }
  if (completenessScore < 0.5) {
    inferredAdverseReasons.push("Insufficient number of accounts");
  }

  const oneCsResult = buildOneCsResult({
    creditScore,
    completenessScore,
    adverseReasons: inferredAdverseReasons,
    priceUsd: 0,
    durationMs: 0,
    source: "import",
  });

  return importedLeadRecordSchema.parse({
    blockIndex,
    sourceLabel,
    fullName,
    addressRaw: address.addressRaw,
    city: address.city,
    state: address.state,
    postalCode: address.postalCode,
    age,
    bornText,
    dobText,
    hasSsn,
    email,
    emailDomain: extractEmailDomain(email),
    phoneNumbers: Array.from(phoneNumbers),
    creditScore,
    flags: Array.from(flags),
    completenessScore,
    oneCsResult,
  });
}

export function parseImportedLeadText(input: string) {
  return input
    .split(/\n\s*\n+/)
    .map((block, index) => parseBlock(block, index + 1))
    .filter((record): record is ImportedLeadRecord => record !== null);
}

export function toSafeImportedLeadRecord(record: ImportedLeadRecord): SafeImportedLeadRecord {
  return safeImportedLeadRecordSchema.parse({
    ...record,
    fullName: maskName(record.fullName),
    email: null,
    phoneNumbers: record.phoneNumbers.map(maskPhone),
    normalizedTarget: `mock://lead-import/${record.blockIndex}`,
    piiRedacted: true,
  });
}

export function buildSafeLeadImportPayloads(input: string) {
  return parseImportedLeadText(input).map(record => {
    const safeRecord = toSafeImportedLeadRecord(record);

    return {
      targetLabel: safeRecord.fullName,
      queueName: "lead-import",
      priority: 110,
      safeTestMode: true,
      payload: {
        target: safeRecord.normalizedTarget,
        action: "normalize_imported_lead_record",
        piiRedacted: true,
        sourceLabel: safeRecord.sourceLabel,
        city: safeRecord.city,
        state: safeRecord.state,
        postalCode: safeRecord.postalCode,
        age: safeRecord.age,
        hasSsn: safeRecord.hasSsn,
        hasDob: Boolean(safeRecord.dobText),
        phoneCount: safeRecord.phoneNumbers.length,
        emailDomain: safeRecord.emailDomain,
        hasCreditScore: safeRecord.creditScore !== null,
        flags: safeRecord.flags,
        completenessScore: safeRecord.completenessScore,
        productScore: safeRecord.oneCsResult.productScore,
        dataQualityScore: safeRecord.oneCsResult.dataQualityScore,
        oneCsStatus: safeRecord.oneCsResult.status,
        adverseReasonGroups: safeRecord.oneCsResult.adverseReasonGroups,
      },
    };
  });
}
