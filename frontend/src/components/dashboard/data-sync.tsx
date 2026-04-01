"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface SyncJobLog {
  id: string;
  level: string;
  message: string;
  created_at: string;
}

interface SyncJob {
  id: string;
  sync_type: string;
  status: string;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  completed_at: string | null;
  logs: SyncJobLog[];
}

interface DataSummary {
  campaigns: number;
  ad_sets: number;
  ads: number;
  creatives: number;
  account_insight_rows: number;
  campaign_insight_rows: number;
  adset_insight_rows: number;
  ad_insight_rows: number;
  sync_state: string;
  last_sync: SyncJob | null;
}

interface Props {
  onSyncComplete?: () => void;
}

interface ReportImportResult {
  campaigns: number;
  ad_sets: number;
  ads: number;
  insight_rows: number;
  date_start: string | null;
  date_end: string | null;
  replaced_existing: boolean;
  report_type: string;
  source_sheet: string | null;
  warnings: string[];
}

interface ConnectionStatus {
  connected: boolean;
}

interface AuditJob {
  job_id: string;
  status: string;
}

interface AuditJobStatus {
  job_id: string;
  status: string;
  error?: string | null;
}

interface FilePreview {
  fileName: string;
  kind: "csv" | "xlsx";
  headers: string[];
  warnings: string[];
}

const uploadChecklist = [
  "My export covers 30 or more days.",
  "I selected 'Daily' breakdown (not 'Monthly' or 'Summary').",
  "The export includes spend, clicks, conversions, and ad set columns.",
  "I exported from Ads Manager as CSV or XLSX.",
];

export function DataSync({ onSyncComplete }: Props) {
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [activeJob, setActiveJob] = useState<SyncJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [checklist, setChecklist] = useState<boolean[]>(uploadChecklist.map(() => false));
  const [uploadResult, setUploadResult] = useState<ReportImportResult | null>(null);
  const [preview, setPreview] = useState<FilePreview | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [runningAudit, setRunningAudit] = useState(false);
  const [metaConnected, setMetaConnected] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  async function fetchSummary() {
    try {
      const data = await apiFetch<DataSummary>("/sync/summary");
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load import summary");
    }
  }

  async function fetchMetaStatus() {
    try {
      const data = await apiFetch<ConnectionStatus>("/meta/connection");
      setMetaConnected(Boolean(data.connected));
    } catch {
      setMetaConnected(false);
    }
  }

  async function fetchStatus() {
    try {
      const data = await apiFetch<SyncJob | null>("/sync/status");
      setActiveJob(data);
      if (data && ["pending", "running"].includes(data.status)) {
        startPolling();
      } else {
        stopPolling();
        await fetchSummary();
        if (data?.status === "completed") {
          onSyncComplete?.();
        }
      }
    } catch (err) {
      stopPolling();
      setError(err instanceof Error ? err.message : "Failed to load sync status");
    }
  }

  function startPolling() {
    if (pollRef.current) return;
    pollRef.current = setInterval(() => {
      void fetchStatus();
    }, 2500);
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    async function init() {
      await Promise.all([fetchSummary(), fetchStatus(), fetchMetaStatus()]);
      setLoading(false);
    }

    void init();
    return () => stopPolling();
  }, []);

  async function handleStart(syncType: "initial" | "incremental") {
    setStarting(syncType);
    setError("");
    try {
      const response = await apiFetch<{ job: SyncJob }>("/sync/start", {
        method: "POST",
        body: JSON.stringify({ sync_type: syncType }),
      });
      setActiveJob(response.job);
      startPolling();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start sync");
    } finally {
      setStarting(null);
    }
  }

  async function handleUploadReport(file: File) {
    setError("");
    setUploadResult(null);
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("replace_existing", String(replaceExisting));
      const result = await apiFetch<ReportImportResult>("/sync/import-report", {
        method: "POST",
        body: formData,
      });
      setUploadResult(result);
      setSelectedFile(null);
      setPreview(null);
      await Promise.all([fetchSummary(), fetchStatus()]);
      onSyncComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import report");
    } finally {
      setUploading(false);
    }
  }

  async function pollAuditJob(jobId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const status = await apiFetch<AuditJobStatus>(`/audit/job/${jobId}`);
      if (status.status === "completed") return;
      if (status.status === "failed") throw new Error(status.error || "Audit failed");
    }

    throw new Error("Audit timed out. Please try again.");
  }

  async function handleRunAuditNow() {
    setError("");
    setRunningAudit(true);
    try {
      const job = await apiFetch<AuditJob>("/audit/run", { method: "POST" });
      await pollAuditJob(job.job_id);
      onSyncComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run audit");
    } finally {
      setRunningAudit(false);
    }
  }

  async function buildPreview(file: File) {
    if (file.name.toLowerCase().endsWith(".xlsx")) {
      setPreview({
        fileName: file.name,
        kind: "xlsx",
        headers: [],
        warnings: ["Workbook preview is limited in-browser. Import will parse the first non-empty worksheet."],
      });
      return;
    }

    const text = await file.text();
    const firstLine = text.split(/\r?\n/).find((line) => line.trim().length > 0) || "";
    const headers = firstLine
      .split(",")
      .map((item) => item.replace(/^"|"$/g, "").trim())
      .filter(Boolean);

    const normalized = headers.map((item) => item.toLowerCase());
    const warnings: string[] = [];
    if (!normalized.some((item) => item.includes("date"))) warnings.push("No date column detected.");
    if (!normalized.some((item) => item.includes("campaign"))) warnings.push("No campaign column detected.");
    if (!normalized.some((item) => item.includes("click"))) warnings.push("No clicks column detected. CTR and CPC may remain weak.");
    if (!normalized.some((item) => item.includes("purchase") || item.includes("conversion") || item.includes("result"))) {
      warnings.push("No conversion-style columns detected. The audit may produce lower-confidence recommendations.");
    }

    setPreview({ fileName: file.name, kind: "csv", headers: headers.slice(0, 12), warnings });
  }

  if (loading) {
    return <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading import state...</div>;
  }

  const syncState = activeJob?.status || summary?.sync_state || "pending";
  const hasData = Boolean(summary && (summary.campaigns > 0 || summary.campaign_insight_rows > 0));

  return (
    <section className="space-y-4 rounded-[1.5rem] border border-slate-200 bg-white p-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-brand-600">Primary input</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-900">Import Meta Ads history</h2>
        <p className="mt-1 text-sm text-slate-500">
          Upload first: import a Meta Ads export, verify the file quality, then run the audit.
        </p>
      </div>

      <div className="rounded-2xl border border-sky-100 bg-sky-50 p-4">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-slate-900">Before you upload — quick check</h3>
          {checklist.every(Boolean) ? (
            <span className="rounded-full bg-emerald-100 px-3 py-0.5 text-xs font-semibold text-emerald-700">Ready to import</span>
          ) : (
            <span className="text-xs text-slate-400">{checklist.filter(Boolean).length}/{uploadChecklist.length} checked</span>
          )}
        </div>
        <div className="mt-3 space-y-2">
          {uploadChecklist.map((item, index) => (
            <label key={item} className="flex cursor-pointer items-start gap-3 rounded-xl bg-white px-3 py-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={checklist[index]}
                onChange={() => setChecklist((prev) => prev.map((v, i) => (i === index ? !v : v)))}
                className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 accent-sky-600"
              />
              <span className={checklist[index] ? "line-through text-slate-400" : ""}>{item}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Import a Meta Ads report</h3>
            <p className="mt-1 text-xs text-slate-500">CSV and XLSX exports from Ads Manager work best.</p>
          </div>
          <label className="inline-flex cursor-pointer items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            {uploading ? "Importing..." : "Select CSV or XLSX"}
            <input
              type="file"
              accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              disabled={uploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setSelectedFile(file);
                  void buildPreview(file);
                }
                event.currentTarget.value = "";
              }}
            />
          </label>
        </div>

        {preview ? (
          <div className="mt-3 rounded-xl border border-slate-200 bg-white px-3 py-3 text-xs text-slate-700">
            <p className="font-semibold text-slate-900">Selected file: {preview.fileName}</p>
            <p className="mt-2 text-slate-500">
              {preview.kind === "xlsx"
                ? "Workbook preview is limited in-browser. The importer will choose the best worksheet automatically."
                : `Detected columns: ${preview.headers.join(", ") || "None"}`}
            </p>
            {preview.warnings.length > 0 ? (
              <ul className="mt-2 space-y-1 text-amber-700">
                {preview.warnings.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-emerald-700">Column check passed.</p>
            )}
            <div className="mt-3">
              <Button onClick={() => selectedFile && void handleUploadReport(selectedFile)} disabled={!selectedFile || uploading}>
                {uploading ? "Importing..." : "Import selected report"}
              </Button>
            </div>
          </div>
        ) : null}

        <label className="mt-3 inline-flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={replaceExisting}
            onChange={(event) => setReplaceExisting(event.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          Replace existing imported history for the selected account
        </label>

        {uploadResult ? (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-xs text-emerald-800">
            <p>
              Imported {uploadResult.campaigns} campaigns, {uploadResult.ad_sets} ad sets, {uploadResult.ads} ads, and {uploadResult.insight_rows} rows.
            </p>
            <p className="mt-1">
              {uploadResult.date_start && uploadResult.date_end
                ? `Period: ${new Date(uploadResult.date_start).toLocaleDateString()} to ${new Date(uploadResult.date_end).toLocaleDateString()}. `
                : ""}
              {uploadResult.source_sheet ? `Sheet: ${uploadResult.source_sheet}. ` : ""}
              {uploadResult.report_type ? `Row type: ${uploadResult.report_type.replaceAll("_", " ")}.` : ""}
            </p>
            {uploadResult.warnings.length > 0 ? (
              <ul className="mt-2 space-y-1 text-amber-800">
                {uploadResult.warnings.map((warning) => (
                  <li key={warning}>- {warning}</li>
                ))}
              </ul>
            ) : null}
            <p className="mt-2 text-slate-700">
              {uploadResult.report_type === "period_aggregate"
                ? "This looks like an aggregate export, so the audit will focus on the clearest leaks and skip deeper trend checks."
                : "This file has the right shape for a stronger diagnostic read."}
            </p>
            <div className="mt-3">
              <Button onClick={() => void handleRunAuditNow()} disabled={runningAudit}>
                {runningAudit ? "Running audit..." : "Run audit now"}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Optional live Meta sync</h3>
            <p className="mt-1 text-xs text-slate-500">Keep this secondary. Uploaded exports are the recommended primary data source.</p>
          </div>
          {metaConnected ? (
            <div className="flex gap-3">
              <Button variant="secondary" disabled={Boolean(starting) || ["pending", "running"].includes(syncState)} onClick={() => void handleStart("incremental")}>
                {starting === "incremental" ? "Starting..." : "Run incremental sync"}
              </Button>
              <Button disabled={Boolean(starting) || ["pending", "running"].includes(syncState)} onClick={() => void handleStart("initial")}>
                {starting === "initial" ? "Starting..." : hasData ? "Re-run initial sync" : "Run initial sync"}
              </Button>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
              No live Meta connection active. Upload a file instead.
            </div>
          )}
        </div>
      </div>

      {error ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}

      {activeJob && ["pending", "running"].includes(activeJob.status) ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-sky-900">Sync in progress</h3>
              <p className="text-sm text-sky-700">{activeJob.current_step || "Preparing sync"}</p>
            </div>
            <span className="text-sm font-semibold text-sky-700">{activeJob.progress}%</span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-sky-200">
            <div className="h-full rounded-full bg-sky-600 transition-all duration-500" style={{ width: `${activeJob.progress}%` }} />
          </div>
        </div>
      ) : null}

      {syncState === "completed" && summary ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <h3 className="font-semibold text-emerald-900">Imported data ready</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Campaigns", summary.campaigns],
              ["Ad Sets", summary.ad_sets],
              ["Ads", summary.ads],
              ["Creatives", summary.creatives],
              ["Account Daily", summary.account_insight_rows],
              ["Campaign Daily", summary.campaign_insight_rows],
              ["Ad Set Daily", summary.adset_insight_rows],
              ["Ad Daily", summary.ad_insight_rows],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-xl bg-white px-4 py-3 text-center">
                <p className="text-2xl font-semibold text-slate-900">{value}</p>
                <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              </div>
            ))}
          </div>
          {summary.last_sync?.completed_at ? (
            <p className="mt-3 text-xs text-slate-500">Last live sync completed: {new Date(summary.last_sync.completed_at).toLocaleString()}</p>
          ) : null}
        </div>
      ) : null}

      {syncState === "pending" && !hasData ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
          <h3 className="font-semibold text-slate-900">No imported data yet</h3>
          <p className="mt-1 text-sm text-slate-500">
            Upload a Meta Ads export to populate the dashboard and generate the first audit report.
          </p>
        </div>
      ) : null}

      {activeJob?.logs?.length ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <h4 className="text-sm font-semibold text-slate-900">Recent sync logs</h4>
          <div className="mt-3 space-y-2 text-xs text-slate-600">
            {activeJob.logs.slice(0, 5).map((log) => (
              <div key={log.id} className="rounded-xl bg-white px-3 py-2">
                <span className="font-medium uppercase tracking-wide text-slate-400">{log.level}</span> {log.message}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
