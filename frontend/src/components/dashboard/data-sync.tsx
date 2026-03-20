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
  campaigns_synced: number;
  ad_sets_synced: number;
  ads_synced: number;
  creatives_synced: number;
  insights_account_synced: number;
  insights_campaign_synced: number;
  insights_adset_synced: number;
  insights_ad_synced: number;
  error_message: string | null;
  started_at: string | null;
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

interface EntitlementsInfo {
  max_reports_per_month: number;
  reports_used_last_30_days: number;
  reports_remaining_last_30_days: number;
}

interface ConnectionStatus {
  connected: boolean;
}

interface FilePreview {
  fileName: string;
  kind: "csv" | "xlsx";
  headers: string[];
  warnings: string[];
}

export function DataSync({ onSyncComplete }: Props) {
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [activeJob, setActiveJob] = useState<SyncJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [uploadResult, setUploadResult] = useState<ReportImportResult | null>(null);
  const [preview, setPreview] = useState<FilePreview | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [runningAudit, setRunningAudit] = useState(false);
  const [quota, setQuota] = useState<EntitlementsInfo | null>(null);
  const [metaConnected, setMetaConnected] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  async function fetchSummary() {
    try {
      const data = await apiFetch<DataSummary>("/sync/summary");
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sync summary");
    }
  }

  async function fetchQuota() {
    try {
      const ent = await apiFetch<EntitlementsInfo>("/billing/entitlements");
      setQuota(ent);
    } catch {
      setQuota(null);
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
      await Promise.all([fetchSummary(), fetchStatus(), fetchQuota(), fetchMetaStatus()]);
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
      await fetchSummary();
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
      await Promise.all([fetchSummary(), fetchStatus(), fetchQuota(), fetchMetaStatus()]);
      onSyncComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import report");
    } finally {
      setUploading(false);
    }
  }

  async function handleRunAuditNow() {
    setError("");
    setRunningAudit(true);
    try {
      await apiFetch("/audit/run", { method: "POST" });
      await fetchQuota();
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
    if (!normalized.some((item) => item.includes("date") || item.includes("дата") || item.includes("рґр°с‚р°"))) {
      warnings.push("No date column detected.");
    }
    if (!normalized.some((item) => item.includes("campaign") || item.includes("кампан") || item.includes("рєр°рјрї"))) {
      warnings.push("No campaign column detected.");
    }
    if (!normalized.some((item) => item.includes("click") || item.includes("клик") || item.includes("рєр»рёрє"))) {
      warnings.push("No clicks column detected. CTR/CPC may remain 0.");
    }
    if (!normalized.some((item) => item.includes("purchase") || item.includes("conversion") || item.includes("конверс") || item.includes("result") || item.includes("результ"))) {
      warnings.push("No conversion-style columns detected. Findings may be limited.");
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
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-brand-600">Primary Input</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">Import Meta Ads history</h2>
          <p className="mt-1 text-sm text-slate-500">
            Upload raw Facebook Ads exports in CSV or XLSX format to populate dashboard analytics, deterministic audit findings, and the AI explanation layer.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Import Facebook Ads report</h3>
            <p className="mt-1 text-xs text-slate-500">
              The working local MVP path is upload first, then dashboard review, then audit run.
            </p>
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
                ? "The importer will use the first non-empty worksheet."
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
          Replace existing imported history for selected account
        </label>

        <p className="mt-3 text-xs text-slate-500">
          Meta connection is optional for now. This MVP should work from uploaded history files alone.
        </p>

        {uploadResult ? (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
            Imported {uploadResult.campaigns} campaigns, {uploadResult.ad_sets} ad sets, {uploadResult.ads} ads, {uploadResult.insight_rows} insight rows.
            {uploadResult.date_start && uploadResult.date_end ? ` Date range: ${new Date(uploadResult.date_start).toLocaleDateString()} - ${new Date(uploadResult.date_end).toLocaleDateString()}.` : ""}
            {uploadResult.source_sheet ? ` Sheet: ${uploadResult.source_sheet}.` : ""}
            {uploadResult.report_type ? ` Report type: ${uploadResult.report_type.replaceAll("_", " ")}.` : ""}
            {uploadResult.warnings.length > 0 ? (
              <ul className="mt-2 space-y-1 text-amber-800">
                {uploadResult.warnings.map((warning) => (
                  <li key={warning}>- {warning}</li>
                ))}
              </ul>
            ) : null}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Button onClick={() => void handleRunAuditNow()} disabled={runningAudit}>
                {runningAudit ? "Running audit..." : "Run audit now"}
              </Button>
              {quota ? (
                <span className="text-slate-600">
                  Reports left (30 days): {quota.reports_remaining_last_30_days}/{quota.max_reports_per_month}
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Optional live Meta sync</h3>
            <p className="mt-1 text-xs text-slate-500">
              Keep this secondary. Use it later if you want live syncing instead of manual history uploads.
            </p>
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
              No live Meta connection active. Upload files instead.
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

      {syncState === "failed" && activeJob ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <h3 className="font-semibold text-red-900">Sync failed</h3>
          <p className="mt-1 text-sm text-red-700">{activeJob.error_message || "The worker reported a failure."}</p>
        </div>
      ) : null}

      {syncState === "completed" && summary ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <h3 className="font-semibold text-emerald-900">Data available</h3>
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
            Upload a CSV or XLSX export from Facebook Ads Manager to generate dashboard analytics and your first audit report.
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
