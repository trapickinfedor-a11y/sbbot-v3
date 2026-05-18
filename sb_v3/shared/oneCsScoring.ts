import { z } from "zod";

export const oneCsStatusValues = ["success", "review", "decline", "no_file", "error"] as const;
export const adverseReasonGroupValues = [
  "no_file",
  "thin_file",
  "low_depth",
  "affordability",
  "utilization",
  "delinquency",
  "public_record",
  "inquiry_pressure",
  "consumer_finance",
] as const;

export type OneCsStatus = (typeof oneCsStatusValues)[number];
export type AdverseReasonGroup = (typeof adverseReasonGroupValues)[number];

export const oneCsResultSchema = z.object({
  creditScore: z.number().int().min(300).max(850).nullable(),
  productScore: z.number().min(1).max(20),
  dataQualityScore: z.number().min(1).max(10),
  adverseReasons: z.array(z.string()),
  adverseReasonGroups: z.array(z.enum(adverseReasonGroupValues)),
  status: z.enum(oneCsStatusValues),
  priceUsd: z.number().min(0),
  durationMs: z.number().int().min(0),
  source: z.enum(["dashboard", "api", "telegram", "import", "system", "testbench"]),
  explanations: z.array(z.string()),
  completenessScore: z.number().min(0).max(1).optional(),
});

export type OneCsResult = z.infer<typeof oneCsResultSchema>;

export type BuildOneCsResultInput = {
  creditScore: number | null;
  completenessScore?: number | null;
  adverseReasons?: string[];
  priceUsd?: number;
  durationMs?: number;
  source: "dashboard" | "api" | "telegram" | "import" | "system" | "testbench";
};

const REASON_TO_GROUP: Array<{ pattern: RegExp; normalized: string; group: AdverseReasonGroup }> = [
  {
    pattern: /^Unable to find credit profile at TransUnion$/i,
    normalized: "Unable to find credit profile at TransUnion",
    group: "no_file",
  },
  {
    pattern: /^Insufficient credit history$/i,
    normalized: "Insufficient credit history",
    group: "thin_file",
  },
  {
    pattern: /^Insufficient length of credit history$/i,
    normalized: "Insufficient length of credit history",
    group: "thin_file",
  },
  {
    pattern: /^Insufficient number of accounts$/i,
    normalized: "Insufficient number of accounts",
    group: "thin_file",
  },
  {
    pattern: /^Insufficient number of open accounts$/i,
    normalized: "Insufficient number of open accounts",
    group: "thin_file",
  },
  {
    pattern: /^Lack of recent installment loan information$/i,
    normalized: "Lack of recent installment loan information",
    group: "low_depth",
  },
  {
    pattern: /^Lack of recent revolving account information$/i,
    normalized: "Lack of recent revolving account information",
    group: "low_depth",
  },
  {
    pattern: /^Lack of recent bank\/national revolving information$/i,
    normalized: "Lack of recent bank/national revolving information",
    group: "low_depth",
  },
  {
    pattern: /^No recent revolving balances$/i,
    normalized: "No recent revolving balances",
    group: "low_depth",
  },
  {
    pattern: /^No recent bank\/national revolving balances$/i,
    normalized: "No recent bank/national revolving balances",
    group: "low_depth",
  },
  {
    pattern: /^Length of time (revolving |bank\/national )?accts? (have been|has been) established$/i,
    normalized: "Length of time revolving accounts have been established",
    group: "low_depth",
  },
  {
    pattern: /^Derogatory public record or collection filed$/i,
    normalized: "Derogatory public record or collection filed",
    group: "public_record",
  },
  {
    pattern: /^Too few accounts currently paid as agreed$/i,
    normalized: "Too few accounts currently paid as agreed",
    group: "low_depth",
  },
  {
    pattern: /^Income or credit history insufficient for loan$/i,
    normalized: "Income or credit history insufficient for loan",
    group: "affordability",
  },
  {
    pattern: /^Requested amount unsupported by income$/i,
    normalized: "Requested amount unsupported by income",
    group: "affordability",
  },
  {
    pattern: /^High debt in relation to income$/i,
    normalized: "High debt in relation to income",
    group: "affordability",
  },
  {
    pattern: /^Proportion of loan balances to loan amounts is too high$/i,
    normalized: "Proportion of loan balances to loan amounts is too high",
    group: "affordability",
  },
  {
    pattern: /^Proportion of balances to credit limits on bank\/national revolving or other revolving accounts is too high$/i,
    normalized: "Proportion of balances to credit limits on bank/national revolving or other revolving accounts is too high",
    group: "utilization",
  },
  {
    pattern: /^Too many accounts with balances$/i,
    normalized: "Too many accounts with balances",
    group: "utilization",
  },
  {
    pattern: /^Serious delinquency$/i,
    normalized: "Serious delinquency",
    group: "delinquency",
  },
  {
    pattern: /^Number of accounts with delinquency$/i,
    normalized: "Number of accounts with delinquency",
    group: "delinquency",
  },
  {
    pattern: /^Time since delinquency is too recent or unknown$/i,
    normalized: "Time since delinquency is too recent or unknown",
    group: "delinquency",
  },
  {
    pattern: /^Serious delinquency, (and )?public record,? or collection filed$/i,
    normalized: "Serious delinquency, and public record or collection filed",
    group: "public_record",
  },
  {
    pattern: /^Derogatory public record or collection filed$/i,
    normalized: "Derogatory public record or collection filed",
    group: "public_record",
  },
  {
    pattern: /^RiskView Consumer Inquiry$/i,
    normalized: "RiskView Consumer Inquiry",
    group: "inquiry_pressure",
  },
  {
    pattern: /^Too many inquiries last 12 months$/i,
    normalized: "Too many inquiries last 12 months",
    group: "inquiry_pressure",
  },
  {
    pattern: /^High number of recent inquiries$/i,
    normalized: "High number of recent inquiries",
    group: "inquiry_pressure",
  },
  {
    pattern: /^Too many consumer finance company accounts$/i,
    normalized: "Too many consumer finance company accounts",
    group: "consumer_finance",
  },
];

const GROUP_PENALTIES: Record<AdverseReasonGroup, number> = {
  no_file: 5.0,
  thin_file: 1.6,
  low_depth: 1.0,
  affordability: 1.6,
  utilization: 1.2,
  delinquency: 1.6,
  public_record: 2.0,
  inquiry_pressure: 0.8,
  consumer_finance: 0.6,
};

function clamp(min: number, value: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}

export function normalizeAdverseReason(reason: string) {
  const compact = reason.replace(/\s+/g, " ").trim().replace(/\.$/, "");
  const matched = REASON_TO_GROUP.find(entry => entry.pattern.test(compact));
  if (!matched) {
    return {
      original: compact,
      normalized: compact,
      group: null,
    } as const;
  }

  return {
    original: compact,
    normalized: matched.normalized,
    group: matched.group,
  } as const;
}

export function normalizeAdverseReasons(reasons: string[] = []) {
  const seenReasons = new Set<string>();
  const seenGroups = new Set<AdverseReasonGroup>();
  const normalizedReasons: string[] = [];
  const groups: AdverseReasonGroup[] = [];

  for (const reason of reasons) {
    const normalized = normalizeAdverseReason(reason);
    if (!seenReasons.has(normalized.normalized)) {
      seenReasons.add(normalized.normalized);
      normalizedReasons.push(normalized.normalized);
    }
    if (normalized.group && !seenGroups.has(normalized.group)) {
      seenGroups.add(normalized.group);
      groups.push(normalized.group);
    }
  }

  return {
    adverseReasons: normalizedReasons,
    adverseReasonGroups: groups,
  } as const;
}

export function deriveProductScore(creditScore: number | null) {
  if (creditScore == null) return 1;
  const transformed = Math.round(((creditScore - 300) / 550) * 19) + 1;
  return clamp(1, transformed, 20);
}

export function getBaseQualityFromCreditScore(creditScore: number | null) {
  if (creditScore == null) return 3.5;
  if (creditScore >= 800) return 9.7;
  if (creditScore >= 760) return 9.0;
  if (creditScore >= 720) return 8.2;
  if (creditScore >= 680) return 7.4;
  if (creditScore >= 640) return 6.5;
  if (creditScore >= 600) return 5.5;
  if (creditScore >= 560) return 4.5;
  if (creditScore >= 520) return 3.5;
  if (creditScore >= 480) return 2.5;
  return 1.5;
}

export function getCompletenessAdjustment(completenessScore: number | null | undefined) {
  const value = completenessScore ?? 0;
  if (value >= 0.95) return 0.5;
  if (value >= 0.8) return 0.3;
  if (value >= 0.65) return 0.1;
  if (value >= 0.5) return 0.0;
  if (value >= 0.35) return -0.3;
  return -0.5;
}

export function derivePenaltyFromReasonGroups(groups: AdverseReasonGroup[]) {
  const total = groups.reduce((sum, group) => sum + GROUP_PENALTIES[group], 0);
  return Math.min(6.5, round1(total));
}

export function deriveOneCsStatus(input: { creditScore: number | null; dataQualityScore: number; adverseReasonGroups: AdverseReasonGroup[] }) {
  if (input.creditScore == null && input.adverseReasonGroups.includes("no_file")) {
    return "no_file" satisfies OneCsStatus;
  }
  if (input.creditScore != null && input.dataQualityScore >= 3.5) {
    return "success" satisfies OneCsStatus;
  }
  if (input.creditScore != null && input.dataQualityScore >= 2.0) {
    return "review" satisfies OneCsStatus;
  }
  if (input.creditScore == null && input.dataQualityScore >= 3.5) {
    return "success" satisfies OneCsStatus;
  }
  if (input.creditScore == null && input.dataQualityScore >= 2.0) {
    return "review" satisfies OneCsStatus;
  }
  return "decline" satisfies OneCsStatus;
}

export function buildOneCsExplanations(result: {
  creditScore: number | null;
  completenessScore?: number | null;
  adverseReasons: string[];
  adverseReasonGroups: AdverseReasonGroup[];
  productScore: number;
  dataQualityScore: number;
  status: OneCsStatus;
}) {
  const explanations: string[] = [];

  if (result.creditScore == null) {
    explanations.push("Credit score was not found, so the profile starts from a low confidence baseline.");
  } else {
    explanations.push(`Raw credit score ${result.creditScore} mapped to product score ${result.productScore}/20.`);
  }

  if (typeof result.completenessScore === "number") {
    explanations.push(`Record completeness contributed ${Math.round(result.completenessScore * 100)}% of the available lead signals.`);
  }

  if (result.adverseReasonGroups.includes("public_record")) {
    explanations.push("Public record or collection signals materially reduced data quality.");
  }
  if (result.adverseReasonGroups.includes("delinquency")) {
    explanations.push("Recent or repeated delinquency pressure reduced the final score.");
  }
  if (result.adverseReasonGroups.includes("affordability")) {
    explanations.push("Income and debt affordability signals indicate lower financing readiness.");
  }
  if (result.adverseReasonGroups.includes("thin_file") || result.adverseReasonGroups.includes("low_depth")) {
    explanations.push("Thin or shallow credit history reduced confidence in profile stability.");
  }
  if (result.adverseReasonGroups.includes("utilization")) {
    explanations.push("High utilization or too many balances reduced quality despite other available signals.");
  }
  if (result.adverseReasonGroups.includes("inquiry_pressure")) {
    explanations.push("Recent inquiry pressure added a smaller negative adjustment.");
  }
  if (result.adverseReasons.length === 0 && (result.creditScore ?? 0) >= 720) {
    explanations.push("No adverse reasons were detected for a strong score band, so the profile received a small positive bonus.");
  }

  explanations.push(`Final status: ${result.status}, data quality ${result.dataQualityScore}/10.`);
  return explanations;
}

export function deriveDataQualityScore(input: {
  creditScore: number | null;
  completenessScore?: number | null;
  adverseReasons?: string[];
}) {
  const normalized = normalizeAdverseReasons(input.adverseReasons ?? []);
  const baseQuality = getBaseQualityFromCreditScore(input.creditScore);
  const completenessAdjustment = getCompletenessAdjustment(input.completenessScore);
  const penalty = derivePenaltyFromReasonGroups(normalized.adverseReasonGroups);
  const bonus = normalized.adverseReasonGroups.length === 0 && (input.creditScore ?? 0) >= 680 ? 0.5 : 0;
  const dataQualityScore = round1(clamp(1, baseQuality + completenessAdjustment + bonus - penalty, 10));

  return {
    dataQualityScore,
    baseQuality,
    completenessAdjustment,
    penalty,
    bonus,
    adverseReasons: normalized.adverseReasons,
    adverseReasonGroups: normalized.adverseReasonGroups,
  } as const;
}

export function buildOneCsResult(input: BuildOneCsResultInput): OneCsResult {
  const productScore = deriveProductScore(input.creditScore);
  const quality = deriveDataQualityScore({
    creditScore: input.creditScore,
    completenessScore: input.completenessScore,
    adverseReasons: input.adverseReasons,
  });
  const status = deriveOneCsStatus({
    creditScore: input.creditScore,
    dataQualityScore: quality.dataQualityScore,
    adverseReasonGroups: quality.adverseReasonGroups,
  });

  return oneCsResultSchema.parse({
    creditScore: input.creditScore,
    productScore,
    dataQualityScore: quality.dataQualityScore,
    adverseReasons: quality.adverseReasons,
    adverseReasonGroups: quality.adverseReasonGroups,
    status,
    priceUsd: Number((input.priceUsd ?? 0).toFixed(2)),
    durationMs: Math.max(0, Math.round(input.durationMs ?? 0)),
    source: input.source,
    explanations: buildOneCsExplanations({
      creditScore: input.creditScore,
      completenessScore: input.completenessScore,
      adverseReasons: quality.adverseReasons,
      adverseReasonGroups: quality.adverseReasonGroups,
      productScore,
      dataQualityScore: quality.dataQualityScore,
      status,
    }),
    completenessScore: input.completenessScore ?? undefined,
  });
}
