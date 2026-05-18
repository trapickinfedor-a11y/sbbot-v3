import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import DashboardLayout from "@/components/DashboardLayout";
import { trpc } from "@/lib/trpc";
import { AlertCircle, CheckCircle2, Loader2, ShieldCheck, UploadCloud } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

const exampleImportedText = `LeadFeed Alpha, [3/30/26 9:13 PM]
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

export default function ImportedData() {
  const [inputText, setInputText] = useState(exampleImportedText);
  const [lastImportedBatchId, setLastImportedBatchId] = useState<string | null>(null);
  const utils = trpc.useUtils();

  const previewMutation = trpc.importedData.preview.useMutation({
    onError: error => {
      toast.error(error.message || "Failed to generate a safe preview.");
    },
  });

  const safeBatchMutation = trpc.importedData.createSafeBatch.useMutation({
    onSuccess: async result => {
      setLastImportedBatchId(result.data.batchId);
      toast.success(`Safe batch created: ${result.data.itemCount} items prepared.`);
      await utils.jobs.list.invalidate();
      await utils.platform.overview.invalidate();
      await utils.telemetry.summary.invalidate();
    },
    onError: error => {
      toast.error(error.message || "Failed to create a safe imported batch.");
    },
  });

  const previewData = previewMutation.data;
  const batchResult = safeBatchMutation.data?.data;
  const trimmedInput = inputText.trim();
  const sampleRecords: NonNullable<typeof previewData>["sampleRecords"] = previewData?.sampleRecords ?? [];

  const summaryCards = useMemo(() => {
    if (!previewData) return [];

    return [
      { label: "Records", value: String(previewData.totalRecords) },
      { label: "With phone", value: String(previewData.withPhone) },
      { label: "With email domain", value: String(previewData.withEmailDomain) },
      { label: "With DOB", value: String(previewData.withDob) },
      { label: "With SSN marker", value: String(previewData.withSsnMarker) },
    ];
  }, [previewData]);

  const handlePreview = async () => {
    if (!trimmedInput) {
      toast.error("Paste imported text before running preview.");
      return;
    }

    await previewMutation.mutateAsync({ inputText: trimmedInput });
  };

  const handleSafeBatch = async () => {
    if (!trimmedInput) {
      toast.error("Paste imported text before creating a safe batch.");
      return;
    }

    await safeBatchMutation.mutateAsync({ inputText: trimmedInput });
  };

  const hasPreview = Boolean(previewData);
  const isBusy = previewMutation.isPending || safeBatchMutation.isPending;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <CardTitle className="text-2xl tracking-tight">Imported data safe preview</CardTitle>
                  <CardDescription>
                    Эта панель позволяет проверить присланный текстовый формат, обезличить чувствительные поля и
                    подготовить безопасный batch для тестового контура без использования исходных значений.
                  </CardDescription>
                </div>
                <Badge variant="secondary" className="gap-1.5 px-3 py-1 text-xs">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Safe bench only
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Imported text payload</label>
                <Textarea
                  value={inputText}
                  onChange={event => setInputText(event.target.value)}
                  className="min-h-[260px] resize-y font-mono text-xs"
                  placeholder="Paste imported text blocks here"
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <Button onClick={handlePreview} disabled={isBusy || !trimmedInput} className="gap-2">
                  {previewMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                  Generate safe preview
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSafeBatch}
                  disabled={isBusy || !trimmedInput}
                  className="gap-2"
                >
                  {safeBatchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  Create safe batch
                </Button>
              </div>

              <Alert>
                <ShieldCheck className="h-4 w-4" />
                <AlertTitle>Protected operator workflow</AlertTitle>
                <AlertDescription>
                  Preview results are redacted. Emails are nulled, phone numbers are masked, and downstream targets are
                  converted to synthetic safe identifiers before batch creation.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Current run status</CardTitle>
              <CardDescription>
                Live operator state for preview/import actions, including last successful batch creation.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <StatusTile
                  label="Preview status"
                  value={previewMutation.isSuccess ? "Ready" : previewMutation.isPending ? "Running" : "Idle"}
                />
                <StatusTile
                  label="Safe batch status"
                  value={safeBatchMutation.isSuccess ? "Created" : safeBatchMutation.isPending ? "Running" : "Idle"}
                />
              </div>

              {lastImportedBatchId ? (
                <Alert className="border-primary/20 bg-primary/5">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <AlertTitle>Latest batch created</AlertTitle>
                  <AlertDescription>
                    Batch <span className="font-mono text-xs">{lastImportedBatchId}</span> was prepared in safe mode.
                    Use it for mock execution and regression validation only.
                  </AlertDescription>
                </Alert>
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No batch created yet</EmptyTitle>
                    <EmptyDescription>
                      Run a preview first, then create a safe batch when the structural summary looks correct.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}

              {safeBatchMutation.error ? (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Safe batch error</AlertTitle>
                  <AlertDescription>{safeBatchMutation.error.message}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Compatibility summary</CardTitle>
              <CardDescription>
                Structural signals extracted from the imported format after redaction and normalization.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!hasPreview && !previewMutation.isPending ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No preview generated</EmptyTitle>
                    <EmptyDescription>
                      Generate a safe preview to inspect counts, sample records and converted batch payloads.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : previewMutation.isPending ? (
                <div className="flex min-h-[220px] items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  {summaryCards.map(card => (
                    <div key={card.label} className="rounded-xl border bg-muted/30 p-4">
                      <p className="text-sm text-muted-foreground">{card.label}</p>
                      <p className="mt-2 text-2xl font-semibold tracking-tight">{card.value}</p>
                    </div>
                  ))}
                </div>
              )}

              {previewMutation.error ? (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Preview error</AlertTitle>
                  <AlertDescription>{previewMutation.error.message}</AlertDescription>
                </Alert>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Redacted sample records</CardTitle>
              <CardDescription>
                Operator-facing preview of sanitized records. Sensitive fields are redacted before display.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!hasPreview && !previewMutation.isPending ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No records to display</EmptyTitle>
                    <EmptyDescription>
                      Once preview runs, this table shows masked names, regions, completeness and flags.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : previewMutation.isPending ? (
                <div className="flex min-h-[260px] items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ScrollArea className="w-full">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Record</TableHead>
                        <TableHead>Target</TableHead>
                        <TableHead>Region</TableHead>
                        <TableHead>Phones</TableHead>
                        <TableHead>ONE CS</TableHead>
                        <TableHead>Completeness</TableHead>
                        <TableHead>Flags</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sampleRecords.map((record: (typeof sampleRecords)[number]) => (
                        <TableRow key={record.blockIndex}>
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-medium">{record.fullName}</p>
                              <p className="text-xs text-muted-foreground">Block #{record.blockIndex}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-xs">{record.normalizedTarget}</TableCell>
                          <TableCell>{[record.city, record.state].filter(Boolean).join(", ") || "—"}</TableCell>
                          <TableCell>{record.phoneNumbers.length}</TableCell>
                          <TableCell>
                            <div className="space-y-1 text-xs">
                              <div className="flex flex-wrap gap-1.5">
                                <Badge variant="secondary">CS {record.oneCsResult.creditScore ?? "—"}</Badge>
                                <Badge variant="outline">P {record.oneCsResult.productScore}/20</Badge>
                                <Badge variant="outline">Q {record.oneCsResult.dataQualityScore}/10</Badge>
                              </div>
                              <p className="capitalize text-muted-foreground">{record.oneCsResult.status.replace(/_/g, " ")}</p>
                            </div>
                          </TableCell>
                          <TableCell>{Math.round(record.completenessScore * 100)}%</TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1.5">
                              {record.flags.length > 0 ? (
                                record.flags.map((flag: string) => (
                                  <Badge key={`${record.blockIndex}-${flag}`} variant="outline" className="text-[10px]">
                                    {flag}
                                  </Badge>
                                ))
                              ) : (
                                <span className="text-xs text-muted-foreground">None</span>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Safe payload conversion</CardTitle>
              <CardDescription>
                Preview of normalized job payloads that are compatible with the safe batch contract.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!hasPreview && !previewMutation.isPending ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No safe payloads yet</EmptyTitle>
                    <EmptyDescription>
                      Generate preview to inspect downstream-safe payloads before creating a batch.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : previewMutation.isPending ? (
                <div className="flex min-h-[240px] items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ScrollArea className="h-[260px] rounded-xl border bg-muted/20 p-4">
                  <pre className="text-xs leading-5 text-foreground whitespace-pre-wrap break-all">
                    {JSON.stringify(previewData?.safePayloads ?? [], null, 2)}
                  </pre>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm">
            <CardHeader>
              <CardTitle>Batch execution output</CardTitle>
              <CardDescription>
                Latest safe batch result returned by the admin mutation. This helps validate job creation before broader regression testing.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!batchResult && !safeBatchMutation.isPending ? (
                <Empty>
                  <EmptyHeader>
                    <EmptyTitle>No batch output yet</EmptyTitle>
                    <EmptyDescription>
                      Create a safe batch to review item counts, queue assignment and resulting mock jobs.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : safeBatchMutation.isPending ? (
                <div className="flex min-h-[240px] items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <ScrollArea className="h-[260px] rounded-xl border bg-muted/20 p-4">
                  <pre className="text-xs leading-5 text-foreground whitespace-pre-wrap break-all">
                    {JSON.stringify(batchResult ?? {}, null, 2)}
                  </pre>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </DashboardLayout>
  );
}

type StatusTileProps = {
  label: string;
  value: string;
};

function StatusTile({ label, value }: StatusTileProps) {
  return (
    <div className="rounded-xl border bg-muted/30 p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}
