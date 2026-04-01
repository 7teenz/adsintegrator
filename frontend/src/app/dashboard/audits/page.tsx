"use client";

import { useCallback, useEffect, useState } from "react";

import { AISummaryBlock } from "@/components/dashboard/ai-summary-block";
import { FindingsList } from "@/components/dashboard/findings-list";
import { HealthScore } from "@/components/dashboard/health-score";
import { PillarScores } from "@/components/dashboard/pillar-scores";
import { TrendWidget } from "@/components/dashboard/trend-widget";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch } from "@/lib/api";
import {
  AuditAISummary,
  AuditDashboardData,
  AuditJob,
  AuditJobStatus,
  AuditReport,
  AuditSummary,
  analysisWindowDays,
  deriveBiggestLeak,
  deriveConfidence,
  deriveTopActions,
  formatCurrency,
  formatDate,
  formatFindingMetric,
} from "@/lib/audit";

type ReportTab = "overview" | "campaigns" | "structure" | "tracking" | "trend" | "history";

const tabs: { id: ReportTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "campaigns", label: "Campaigns" },
  { id: "structure", label: "Structure" },
  { id: "tracking", label: "Tracking" },
  { id: "trend", label: "Trend" },
  { id: "history", label: "History" },
];

function severityTone(severity: string): string {
  switch (severity) {
    case "critical":
      return "bg-rose-100 text-rose-700";
    case "high":
      return "bg-orange-100 text-orange-700";
    case "medium":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-sky-100 text-sky-700";
  }
}

function verdictForReport(report: AuditReport, isAggregateMode: boolean): string {
  if (report.findings_count === 0) return "The account looks stable with no major issues triggered in the current audit.";
  if (isAggregateMode) return "This audit found actionable efficiency issues, but the export limits trend-level confidence.";
  if (report.health_score >= 75) return "The account is broadly healthy, but a few clear leaks are still worth fixing now.";
  if (report.health_score >= 55) return "The account is mixed: there is usable traction, but enough waste to justify immediate cleanup.";
  return "The account is underperforming and the current audit shows multiple issues with direct cost impact.";
}

export default function AuditsPage() {
  const [report, setReport] = useState<AuditReport | null>(null);
  const [aiSummary, setAiSummary] = useState<AuditAISummary | null>(null);
  const [dashboardData, setDashboardData] = useState<AuditDashboardData | null>(null);
  const [history, setHistory] = useState<AuditSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [regeneratingSummary, setRegeneratingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("overview");
  const [copyDone, setCopyDone] = useState(false);

  function handlePrint() {
    window.print();
  }

  function handleCopyLink() {
    void navigator.clipboard.writeText(window.location.href).then(() => {
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    });
  }

  const loadData = useCallback(async () => {
    try {
      const [latest, dashboard, hist, summary] = await Promise.all([
        apiFetch<AuditReport | null>("/audit/latest"),
        apiFetch<AuditDashboardData>("/audit/dashboard"),
        apiFetch<AuditSummary[]>("/audit/history"),
        apiFetch<AuditAISummary | null>("/audit/latest/ai-summary"),
      ]);
      setReport(latest);
      setDashboardData(dashboard);
      setHistory(hist);
      setAiSummary(summary);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audits");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function pollJobUntilDone(jobId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const status = await apiFetch<AuditJobStatus>(`/audit/job/${jobId}`);
      if (status.status === "completed") return;
      if (status.status === "failed") throw new Error(status.error || "Audit failed");
    }
    throw new Error("Audit timed out. Please try again.");
  }

  async function runAudit() {
    setRunning(true);
    setError(null);
    try {
      const job = await apiFetch<AuditJob>("/audit/run", { method: "POST" });
      await pollJobUntilDone(job.job_id);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run audit");
    } finally {
      setRunning(false);
    }
  }

  async function regenerateSummary() {
    setRegeneratingSummary(true);
    setError(null);
    try {
      const summary = await apiFetch<AuditAISummary>("/audit/latest/ai-summary/regenerate", { method: "POST" });
      setAiSummary(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to regenerate AI summary");
    } finally {
      setRegeneratingSummary(false);
    }
  }

  const isAggregateMode = dashboardData?.data_mode === "period_aggregate";
  const visibleTabs = tabs.filter((tab) => tab.id !== "trend" || !isAggregateMode);
  const confidence = report ? deriveConfidence(report, dashboardData?.data_mode) : null;
  const biggestLeak = report ? deriveBiggestLeak(report) : null;
  const topActions = report ? deriveTopActions(report) : [];
  const verdict = report ? verdictForReport(report, isAggregateMode) : "";
  const days = report ? analysisWindowDays(report.analysis_start, report.analysis_end) : 0;
  const modeledImpact = report ? report.total_wasted_spend + report.total_estimated_uplift : 0;

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner label="Loading audits..." />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-6">
        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-rose-700">{error}</p>
              <button type="button" onClick={() => void loadData()} className="text-sm font-semibold text-rose-700 underline">
                Retry
              </button>
            </div>
          </div>
        ) : null}
        <section className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">No audit runs yet</h3>
          <p className="mt-2 text-sm text-slate-500">
            Upload a Meta Ads CSV or XLSX export first, then run your first audit to unlock the executive view.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Audit Report</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900">Executive Audit Summary</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">{verdict}</p>
            <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">
              <span className="rounded-full bg-slate-100 px-3 py-1">
                {report.campaign_count} campaigns · {report.ad_set_count} ad sets · {report.ad_count} ads
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                {formatDate(report.analysis_start)} to {formatDate(report.analysis_end)} · {days} days
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Spend analyzed: {formatCurrency(report.total_spend)}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Data mode: {isAggregateMode ? "Aggregate upload" : "Daily time series"}
              </span>
              {confidence ? (
                <span className="rounded-full bg-sky-50 px-3 py-1 text-sky-700">
                  Confidence: {confidence.confidenceLabel}
                </span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleCopyLink}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              {copyDone ? "Copied!" : "Copy link"}
            </button>
            <button
              type="button"
              onClick={handlePrint}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 print:hidden"
            >
              Export PDF
            </button>
            <button
              type="button"
              onClick={runAudit}
              disabled={running}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {running ? "Analyzing..." : "Run Audit"}
            </button>
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-rose-700">{error}</p>
            <button type="button" onClick={() => void loadData()} className="text-sm font-semibold text-rose-700 underline">
              Retry
            </button>
          </div>
        </div>
      ) : null}

      {running ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-700">
          Analyzing your account now. This usually takes under 30 seconds.
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Account Health</p>
          <div className="mt-3 flex justify-center">
            <HealthScore score={report.health_score} size="lg" />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Spend At Risk</p>
          <p className="mt-3 text-3xl font-semibold text-rose-700">{formatCurrency(report.total_wasted_spend)}</p>
          <p className="mt-2 text-xs text-slate-500">Estimated waste surfaced from the current audit.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Potential Lift</p>
          <p className="mt-3 text-3xl font-semibold text-emerald-700">{formatCurrency(report.total_estimated_uplift)}</p>
          <p className="mt-2 text-xs text-slate-500">Modeled upside if the top issues are addressed.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Confidence</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">{confidence?.confidenceLabel || "Low"}</p>
          <p className="mt-2 text-xs text-slate-500">{confidence?.confidenceReason}</p>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">What needs attention now</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">Top 3 actions</h2>
              <p className="mt-1 text-xs text-slate-500">The first fixes worth making based on the strongest evidence in this audit.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
              {report.findings_count} findings detected
            </span>
          </div>
          <div className="mt-4 space-y-3">
            {topActions.length > 0 ? (
              topActions.map((action, index) => (
                <article key={action.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                      {index + 1}
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${severityTone(action.severity)}`}>
                          {action.severity}
                        </span>
                        <span className="text-[11px] uppercase tracking-[0.12em] text-slate-500">{action.category}</span>
                      </div>
                      <p className="mt-2 text-sm font-semibold text-slate-900">{action.title}</p>
                      <p className="mt-1 text-xs font-medium text-slate-500">{action.entityName}</p>
                      <p className="mt-1 text-sm text-slate-600">{action.whyItMatters}</p>
                      {action.metricValue !== null ? (
                        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-white bg-white px-3 py-2 text-xs">
                          <span className="text-slate-500">Actual</span>
                          <span className="font-semibold text-rose-700">{formatFindingMetric(action.metricValue, action.category)}</span>
                          {action.thresholdValue !== null ? (
                            <>
                              <span className="text-slate-300">vs</span>
                              <span className="text-slate-500">Threshold</span>
                              <span className="font-semibold text-slate-700">
                                {formatFindingMetric(action.thresholdValue, action.category)}
                              </span>
                            </>
                          ) : null}
                        </div>
                      ) : null}
                      <p className="mt-2 text-xs font-semibold text-slate-500">
                        Why this matters: {action.impactValue > 0
                          ? `${formatCurrency(action.impactValue)} of modeled impact is tied to this issue.`
                          : "It is one of the clearest performance drags in the current audit, even before strong dollar impact appears."}
                      </p>
                    </div>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-slate-500">No urgent actions were triggered in this run.</p>
            )}
          </div>
        </div>

        <div className="xl:col-span-5 space-y-4">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Biggest leak</p>
            {biggestLeak ? (
              <>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${severityTone(biggestLeak.severity)}`}>
                    {biggestLeak.severity}
                  </span>
                  <span className="text-[11px] uppercase tracking-[0.12em] text-slate-500">{biggestLeak.category}</span>
                </div>
                <h3 className="mt-2 text-lg font-semibold text-slate-900">{biggestLeak.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{biggestLeak.description}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Affected area</p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{biggestLeak.entityName}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Modeled impact</p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">
                      {formatCurrency(biggestLeak.waste + biggestLeak.uplift)}
                    </p>
                  </div>
                </div>
                {biggestLeak.metricValue !== null ? (
                  <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs">
                    <span className="text-slate-500">Actual</span>
                    <span className="font-semibold text-rose-700">{formatFindingMetric(biggestLeak.metricValue, biggestLeak.category)}</span>
                    {biggestLeak.thresholdValue !== null ? (
                      <>
                        <span className="text-slate-300">vs</span>
                        <span className="text-slate-500">Threshold</span>
                        <span className="font-semibold text-slate-700">
                          {formatFindingMetric(biggestLeak.thresholdValue, biggestLeak.category)}
                        </span>
                      </>
                    ) : null}
                  </div>
                ) : null}
                <p className="mt-3 text-xs font-semibold text-slate-500">
                  Why this matters: {biggestLeak.waste + biggestLeak.uplift > 0
                    ? `This issue accounts for ${formatCurrency(biggestLeak.waste + biggestLeak.uplift)} of modeled downside or upside in the current report.`
                    : "This is the clearest efficiency break in the current dataset even though the modeled dollar impact is still low."}
                </p>
              </>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No single leak stands out in the latest report.</p>
            )}
          </section>

          {(isAggregateMode || report.total_wasted_spend === 0 || report.total_estimated_uplift === 0 || days < 14) ? (
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Data limitations</p>
              <p className="mt-2 text-sm text-slate-700">
                {isAggregateMode
                  ? "This file is an aggregate export, so pacing and trend checks are limited."
                  : days < 14
                    ? "This audit uses a short date range, so the strongest conclusions are around clear outliers only."
                    : "The current file has limited waste or uplift signals, which usually means the export window or conversion detail is too thin."}
              </p>
              <p className="mt-3 text-xs text-amber-900/80">
                Current read: {formatCurrency(report.total_spend)} analyzed across {report.campaign_count} campaigns with {confidence?.confidenceLabel.toLowerCase() || "low"} confidence.
              </p>
            </section>
          ) : null}
        </div>
      </section>

      {report.total_wasted_spend === 0 && report.total_estimated_uplift === 0 ? (
        <section className="rounded-2xl border border-sky-100 bg-sky-50 p-5">
          <p className="text-sm font-semibold text-sky-900">
            {report.findings_count > 0 ? "The audit found qualitative issues before strong dollar impact" : "No waste detected in this dataset"}
          </p>
          <p className="mt-1 text-sm text-sky-700">
            {report.findings_count > 0
              ? "The current issues still matter, but the dataset is too small or too aggregate to model strong waste and uplift values. Use the findings as directional advice and upload 30+ days with daily rows for a stronger read."
              : "This usually means the file covers a short period, low spend, or lacks enough conversion detail. Upload 30+ days with daily rows for a stronger audit."}
          </p>
        </section>
      ) : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                activeTab === tab.id ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mt-5">
          {activeTab === "overview" ? (
            <div className="space-y-5">
              <section className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Executive verdict</p>
                  <p className="mt-2 text-sm text-slate-700">{verdict}</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Modeled impact</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">{formatCurrency(modeledImpact)}</p>
                  <p className="mt-1 text-xs text-slate-500">Combined waste and potential uplift from the current run.</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Decision signal</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">{report.findings_count} findings</p>
                  <p className="mt-1 text-xs text-slate-500">Use the evidence below to inspect the specific campaigns and issues driving them.</p>
                </div>
              </section>

              {aiSummary ? (
                <AISummaryBlock
                  summary={aiSummary}
                  report={report}
                  onRegenerate={regenerateSummary}
                  regenerating={regeneratingSummary}
                />
              ) : (
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900">AI interpretation</h3>
                  <p className="mt-2 text-sm text-slate-600">No AI interpretation exists for this run yet. Re-run the audit to generate it.</p>
                </section>
              )}
              <FindingsList findings={report.findings} recommendations={report.recommendations} title="Supporting evidence" />
            </div>
          ) : null}

          {activeTab === "campaigns" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">Weakest campaigns</h3>
                <div className="mt-4 space-y-3">
                  {dashboardData?.worst_campaigns.length ? dashboardData.worst_campaigns.map((item) => (
                    <div key={item.entity_id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-sm font-semibold text-slate-900">{item.entity_name}</p>
                      <p className="mt-1 text-xs text-slate-500">ROAS {item.roas.toFixed(2)}x · CPA {formatCurrency(item.cpa)} · CTR {item.ctr.toFixed(2)}%</p>
                    </div>
                  )) : <p className="text-sm text-slate-500">No campaign-level data yet.</p>}
                </div>
              </section>
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">Weakest ad sets</h3>
                <div className="mt-4 space-y-3">
                  {dashboardData?.worst_adsets.length ? dashboardData.worst_adsets.map((item) => (
                    <div key={item.entity_id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                      <p className="text-sm font-semibold text-slate-900">{item.entity_name}</p>
                      <p className="mt-1 text-xs text-slate-500">ROAS {item.roas.toFixed(2)}x · CPA {formatCurrency(item.cpa)} · CTR {item.ctr.toFixed(2)}%</p>
                    </div>
                  )) : <p className="text-sm text-slate-500">No ad-set-level data yet.</p>}
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "structure" ? (
            <div className="space-y-4">
              {report.pillar_scores.length > 0 ? <PillarScores pillars={report.pillar_scores} /> : null}
              <FindingsList
                findings={report.findings.filter((finding) => ["STRUCTURE", "BUDGET", "FREQUENCY"].includes(finding.category))}
                recommendations={report.recommendations}
                title="Structure and budget findings"
              />
            </div>
          ) : null}

          {activeTab === "tracking" ? (
            <div className="space-y-4">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">Tracking and conversion read</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Use this section to verify whether the audit has enough click, conversion, and revenue signal to support stronger conclusions.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Spend analyzed</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{formatCurrency(report.total_spend)}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Findings</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{report.findings_count}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Confidence</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{confidence?.confidenceLabel}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Data mode</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{isAggregateMode ? "Aggregate" : "Daily"}</p>
                  </div>
                </div>
              </section>
              <FindingsList
                findings={report.findings.filter((finding) => ["PERFORMANCE", "CONVERSION", "ACCOUNT"].includes(finding.category))}
                recommendations={report.recommendations}
                title="Tracking and conversion findings"
              />
            </div>
          ) : null}

          {activeTab === "trend" && !isAggregateMode ? (
            <TrendWidget points={dashboardData?.spend_roas_trend ?? []} showRoas />
          ) : null}

          {activeTab === "history" ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Audit history</h3>
              {history.length >= 2 ? (
                <div className="mb-4 mt-4 rounded-xl bg-slate-50 p-3">
                  <p className="mb-2 text-xs text-slate-500">Score trend</p>
                  <svg width="100%" height="40" viewBox={`0 0 ${history.length * 60} 40`} preserveAspectRatio="none">
                    <polyline
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                      points={history.map((item, i) => {
                        const x = i * 60 + 30;
                        const y = 40 - ((item.health_score / 100) * 36);
                        return `${x},${y}`;
                      }).join(" ")}
                    />
                  </svg>
                </div>
              ) : null}
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                      <th className="px-2 py-3">Date</th>
                      <th className="px-2 py-3">Score</th>
                      <th className="px-2 py-3">Spend</th>
                      <th className="px-2 py-3">Waste</th>
                      <th className="px-2 py-3">Uplift</th>
                      <th className="px-2 py-3">Findings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr key={item.id} className="border-b border-slate-100">
                        <td className="px-2 py-3 text-slate-700">{formatDate(item.created_at)}</td>
                        <td className="px-2 py-3 font-semibold text-slate-900">{Math.round(item.health_score)}</td>
                        <td className="px-2 py-3 text-slate-700">{formatCurrency(item.total_spend)}</td>
                        <td className="px-2 py-3 text-rose-700">{formatCurrency(item.total_wasted_spend)}</td>
                        <td className="px-2 py-3 text-emerald-700">{formatCurrency(item.total_estimated_uplift)}</td>
                        <td className="px-2 py-3 text-slate-700">{item.findings_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
