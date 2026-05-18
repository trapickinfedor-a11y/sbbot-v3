import { describe, expect, it } from "vitest";
import {
  buildSafeLeadImportPayloads,
  parseImportedLeadText,
  toSafeImportedLeadRecord,
} from "../shared/importedLeadFormat";

const syntheticImportedText = `LeadFeed Alpha, [3/30/26 9:13 PM]
Alex Example
123 Example St, Exampletown, CA 90001
28 years old (Jan 1, 1998)
(555) 111-2233
alex@example.com
Your credit score: 720
SSN: 123-45-6789
DOB: 1/1/1998

Jordan Sample
456 Another Ave
Demo City, TX 73301
AGE: 31
BORN: FEB 1995
NF
SSN: 987-65-4321
DOB: 2/2/1995`;

const multiVariantImportedText = `Source Beta [4/1/26 10:30 AM]
Taylor O'Neil
78 River Rd
Austin, TX 78701-4321
(555) 111-2222 and (555) 333-4444
Taylor.ONeil@Example.ORG
SSN: PRESENT
DOB: 04/14/1992

Case Gamma
Morgan Q. Public
902 Market Street
Seattle, WA 98101
AGE: 41
credit score: 688
?
NF

Riley Example
101 Test Blvd
Phoenix, AZ 85001
BORN: MAR 1988
riley@example.net`;

describe("importedLeadFormat", () => {
  it("parses imported text blocks into normalized structural records", () => {
    const records = parseImportedLeadText(syntheticImportedText);

    expect(records).toHaveLength(2);
    expect(records[0]).toMatchObject({
      blockIndex: 1,
      sourceLabel: "LeadFeed Alpha, [3/30/26 9:13 PM]",
      fullName: "Alex Example",
      city: "Exampletown",
      state: "CA",
      postalCode: "90001",
      age: 28,
      hasSsn: true,
      email: "alex@example.com",
      emailDomain: "example.com",
      creditScore: 720,
    });
    expect(records[0]?.phoneNumbers).toEqual(["(555) 111-2233"]);
    expect(records[0]?.oneCsResult).toMatchObject({
      creditScore: 720,
      productScore: 16,
      status: "success",
    });
    expect(records[0]?.oneCsResult.dataQualityScore).toBeGreaterThanOrEqual(8);
    expect(records[1]).toMatchObject({
      blockIndex: 2,
      sourceLabel: null,
      fullName: "Jordan Sample",
      city: "Demo City",
      state: "TX",
      postalCode: "73301",
      age: 31,
      hasSsn: true,
      dobText: "2/2/1995",
    });
    expect(records[1]?.flags).toContain("no_phone_or_email_marker");
    expect(records[1]?.oneCsResult).toMatchObject({
      creditScore: null,
      productScore: 1,
      status: "decline",
    });
  });

  it("supports multiple imported variants including zip+4, multiple phones and uncertain markers", () => {
    const records = parseImportedLeadText(multiVariantImportedText);

    expect(records).toHaveLength(3);

    expect(records[0]).toMatchObject({
      blockIndex: 1,
      sourceLabel: "Source Beta [4/1/26 10:30 AM]",
      fullName: "Taylor O'Neil",
      city: "Austin",
      state: "TX",
      postalCode: "78701",
      email: "taylor.oneil@example.org",
      emailDomain: "example.org",
      hasSsn: true,
      dobText: "04/14/1992",
    });
    expect(records[0]?.phoneNumbers).toEqual(["(555) 111-2222", "(555) 333-4444"]);

    expect(records[1]).toMatchObject({
      sourceLabel: "Case Gamma",
      fullName: "Morgan Q. Public",
      city: "Seattle",
      state: "WA",
      postalCode: "98101",
      age: 41,
      creditScore: 688,
      hasSsn: false,
      email: null,
    });
    expect(records[1]?.flags).toEqual(
      expect.arrayContaining(["contains_uncertain_marker", "no_phone_or_email_marker"]),
    );

    expect(records[2]).toMatchObject({
      sourceLabel: null,
      fullName: "Riley Example",
      city: "Phoenix",
      state: "AZ",
      postalCode: "85001",
      bornText: "MAR 1988",
      email: "riley@example.net",
      emailDomain: "example.net",
      hasSsn: false,
    });
  });

  it("redacts sensitive fields when converting parsed records to safe records", () => {
    const [first] = parseImportedLeadText(syntheticImportedText);
    if (!first) throw new Error("Expected first record");

    const safeRecord = toSafeImportedLeadRecord(first);

    expect(safeRecord.piiRedacted).toBe(true);
    expect(safeRecord.fullName).not.toBe(first.fullName);
    expect(safeRecord.fullName.startsWith("A")).toBe(true);
    expect(safeRecord.email).toBeNull();
    expect(safeRecord.phoneNumbers[0]).toBe("(***) ***-**33");
    expect(safeRecord.normalizedTarget).toBe("mock://lead-import/1");
  });

  it("keeps structural compatibility while masking names and phones across multiple variants", () => {
    const [first] = parseImportedLeadText(multiVariantImportedText);
    if (!first) throw new Error("Expected first multi-variant record");

    const safeRecord = toSafeImportedLeadRecord(first);

    expect(safeRecord.fullName).toBe("T***** O'****");
    expect(safeRecord.phoneNumbers).toEqual(["(***) ***-**22", "(***) ***-**44"]);
    expect(safeRecord.email).toBeNull();
    expect(safeRecord.emailDomain).toBe("example.org");
    expect(safeRecord.piiRedacted).toBe(true);
  });

  it("builds safe test payloads compatible with the job creation contract", () => {
    const payloads = buildSafeLeadImportPayloads(syntheticImportedText);

    expect(payloads).toHaveLength(2);
    expect(payloads[0]).toMatchObject({
      queueName: "lead-import",
      priority: 110,
      safeTestMode: true,
      payload: {
        target: "mock://lead-import/1",
        action: "normalize_imported_lead_record",
        piiRedacted: true,
        state: "CA",
        phoneCount: 1,
        emailDomain: "example.com",
        hasCreditScore: true,
        productScore: 16,
        oneCsStatus: "success",
      },
    });
    expect(payloads[0]?.payload.dataQualityScore).toBeGreaterThanOrEqual(8);
    expect(payloads[1]?.payload).toMatchObject({
      target: "mock://lead-import/2",
      hasDob: true,
      hasSsn: true,
      phoneCount: 0,
    });
  });

  it("preserves safe batch compatibility for the broader imported variants set", () => {
    const payloads = buildSafeLeadImportPayloads(multiVariantImportedText);

    expect(payloads).toHaveLength(3);
    expect(payloads[0]).toMatchObject({
      targetLabel: "T***** O'****",
      queueName: "lead-import",
      safeTestMode: true,
      payload: {
        target: "mock://lead-import/1",
        state: "TX",
        postalCode: "78701",
        phoneCount: 2,
        emailDomain: "example.org",
        hasDob: true,
        hasSsn: true,
      },
    });
    expect(payloads[1]?.payload).toMatchObject({
      target: "mock://lead-import/2",
      flags: expect.arrayContaining(["contains_uncertain_marker", "no_phone_or_email_marker"]),
      hasCreditScore: true,
      phoneCount: 0,
      hasDob: false,
      hasSsn: false,
      productScore: 14,
      oneCsStatus: "success",
    });
    expect(payloads[1]?.payload.dataQualityScore).toBeCloseTo(5.5, 1);
    expect(payloads[2]?.payload).toMatchObject({
      target: "mock://lead-import/3",
      state: "AZ",
      emailDomain: "example.net",
      phoneCount: 0,
      hasDob: false,
      hasSsn: false,
    });
  });
});
