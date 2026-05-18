import { createApiKeyRecord, getAdminOverview } from "./server/platformService.ts";
import { resetRuntimeStore, listRuntimeAuditTrailEntries } from "./server/runtimeStore.ts";

resetRuntimeStore();

const before = await getAdminOverview();
const result = await createApiKeyRecord(9, {
  label: "Future Key",
  scope: "bulk",
  rpmLimit: 120,
  dailyLimit: 5000,
  expiresAt: "2030-01-01T00:00:00.000Z",
});
const after = await getAdminOverview();

console.log(JSON.stringify({
  keyPrefix: result.record.keyPrefix,
  beforeAuditCount: before.auditTrail.length,
  afterAuditCount: after.auditTrail.length,
  afterAuditTrail: after.auditTrail.map((entry) => ({
    action: entry.action,
    resourceId: entry.resourceId,
    createdAt: entry.createdAt,
  })),
  runtimeAuditTrail: listRuntimeAuditTrailEntries().map((entry) => ({
    action: entry.action,
    resourceId: entry.resourceId,
    createdAt: entry.createdAt,
  })),
}, null, 2));
