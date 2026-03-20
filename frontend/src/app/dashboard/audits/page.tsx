"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PlanGate } from "@/components/billing/plan-gate";
import { UpgradeCta } from "@/components/billing/upgrade-cta";
import { AISummaryBlock } from "@/components/dashboard/ai-summary-block";
import { ExecutiveSummary } from "@/components/dashboard/executive-summary";
import { FindingsList } from "@/components/dashboard/findings-list";
import { HealthScore } from "@/components/dashboard/health-score";
import { PillarScores } from "@/components/dashboard/pillar-scores";
import { TrendWidget } from "@/components/dashboard/trend-widget";
import { apiFetch } from "@/lib/api";
import {
  AuditAISummary,
  AuditDashboardData,
  AuditJob,
  AuditJobStatus,
  AuditReport,
  AuditSummary,
  formatCurrency,
  formatDate,
} from "@/lib/audit";
import { usePlan } from "@/lib/plan";

export default function AuditsPage() {
  const { isPremium } = usePlan();

  const [report, setReport] = useState<AuditReport | null>(null);
  const [aiSummary, setAiSummary] = useState<AuditAISummary | null>(null);
  const [dashboardData, setDashboardData] = useState<AuditDashboardData | null>(null);
  const [history, setHistory] = useState<AuditSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [regeneratingSummary, setRegeneratingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audits");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

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

  async function pollJobUntilDone(jobId: string) {
    const maxAttempts = 60;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const status = await apiFetch<AuditJobStatus>(`/audit/job/${jobId}`);
      if (status.status === "completed") return;
      if (status.status === "failed") {
        throw new Error(status.error || "Audit failed");
      }
    }
    throw new Error("Audit timed out. Please try again.");
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

  const shownHistory = useMemo(() => (isPremium ? history : history.slice(0, 4)), [history, isPremium]);
  const isAggregateMode = dashboardData?.data_mode === "period_aggregate";

  if (loading) {
    return <div className="py-20 text-center text-sm text-slate-500">Loading audits...</div>;
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Audit Report</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Deterministic Account Diagnosis</h1>
          <p className="mt-2 text-sm text-slate-600">Run audits on demand and review findings, waste signals, recommendations, and AI explanations.</p>
        </div>
        <button
          type="button"
          onClick={runAudit}
          disabled={running}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {running ? "Analyzing..." : "Run Audit"}
        </button>
      </section>

      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div> : null}
      {running ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-700">
          Analyzing your account. This usually takes 15-30 seconds.
        </div>
      ) : null}

      {!report ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">No audit runs yet</h3>
          <p className="mt-2 text-sm text-slate-500">Upload a CSV or XLSX Facebook Ads export first, then run the deterministic audit engine.</p>
        </div>
      ) : (
        <>
          <section className="grid gap-4 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Health Score</p>
              <div className="mt-3 flex justify-center">
                <HealthScore score={report.health_score} size="lg" />
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Estimated Waste</p>
              <p className="mt-2 text-3xl font-semibold text-rose-700">{formatCurrency(report.total_wasted_spend)}</p>
              <p className="mt-1 text-xs text-slate-500">Always visible</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Potential Uplift</p>
              <p className="mt-2 text-3xl font-semibold text-emerald-700">{formatCurrency(report.total_estimated_uplift)}</p>
              <p className="mt-1 text-xs text-slate-500">Based on deterministic rules</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Analysis Range</p>
              <p className="mt-2 text-lg font-semibold text-slate-900">{isPremium ? "Extended" : "Limited"} window</p>
              <p className="mt-1 text-xs text-slate-500">
                {formatDate(report.analysis_start)} to {formatDate(report.analysis_end)}
              </p>
            </div>
          </section>

          <ExecutiveSummary report={report} />

          {aiSummary ? (
            <AISummaryBlock
              summary={aiSummary}
              canViewDetailed={isPremium}
              onRegenerate={regenerateSummary}
              regenerating={regeneratingSummary}
            />
          ) : (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">AI Explanation Layer</h3>
              <p className="mt-2 text-sm text-slate-600">No summary generated yet. Run or re-run an audit to generate explanation blocks.</p>
            </section>
          )}

          {isAggregateMode ? (
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">Aggregate Report Context</h3>
              <p className="mt-2 text-sm text-slate-600">
                This audit was generated from a period aggregate Meta export. Deterministic findings are limited to rules that do not require daily time-series data.
              </p>
            </section>
          ) : null}

          <section className="grid gap-4 xl:grid-cols-12">
            <div className="xl:col-span-8">
              <FindingsList findings={report.findings} maxItems={isPremium ? undefined : 3} title={isPremium ? "All Findings" : "Top 3 Findings (Free)"} />
            </div>
            <div className="xl:col-span-4 space-y-4">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">Recommendations</h3>
                <div className="mt-3 space-y-3">
                  {(isPremium ? report.recommendations : report.recommendations.slice(0, 2)).map((recommendation) => (
                    <article key={recommendation.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                      <p className="text-sm font-semibold text-slate-900">{recommendation.title}</p>
                      <p className="mt-1 text-xs text-slate-600">{recommendation.body}</p>
                    </article>
                  ))}
                </div>
              </section>

              {!isPremium ? (
                <UpgradeCta
                  title="Unlock complete recommendations"
                  body="Premium gives the full finding list, deeper opportunity context, and advanced report sections."
                />
              ) : null}
            </div>
          </section>

          {report.pillar_scores.length > 0 ? (
            isPremium ? (
              <PillarScores pillars={report.pillar_scores} />
            ) : (
              <PlanGate title="Deep Score Breakdown" message="Premium unlocks full pillar diagnostics and score impact details.">
                <PillarScores pillars={report.pillar_scores} />
              </PlanGate>
            )
          ) : null}

          <section className="grid gap-4 xl:grid-cols-12">
            <div className="xl:col-span-8">
              {isAggregateMode ? (
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900">Trend Layer Unavailable</h3>
                  <p className="mt-2 text-sm text-slate-600">This uploaded report does not include daily breakdown rows, so trend analysis is hidden for this run.</p>
                </section>
              ) : isPremium ? (
                <TrendWidget points={dashboardData?.spend_roas_trend ?? []} showRoas />
              ) : (
                <PlanGate title="Advanced Charts" message="Premium unlocks the full spend/ROAS trend layer and longer history.">
                  <TrendWidget points={dashboardData?.spend_roas_trend ?? []} showRoas />
                </PlanGate>
              )}
            </div>
            <div className="xl:col-span-4">
              {!isPremium ? (
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900">Premium Analysis Blocks</h3>
                  <p className="mt-2 text-sm text-slate-600">Unlock deeper analysis by funnel stages, spend concentration diagnostics, and opportunity impact layers.</p>
                  <UpgradeCta compact title="Deeper Analysis" body="Unlock all advanced report blocks." />
                </section>
              ) : (
                <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                  <h3 className="text-sm font-semibold text-slate-900">Premium Blocks Enabled</h3>
                  <p className="mt-2 text-sm text-slate-600">Advanced charting and deeper analysis are active for this report.</p>
                </section>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Audit History</h3>
            {!isPremium ? <p className="mt-1 text-xs text-slate-500">Free plan shows recent history only.</p> : null}
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
                  {shownHistory.map((item) => (
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
            {!isPremium && history.length > shownHistory.length ? (
              <p className="mt-3 text-xs text-slate-500">Upgrade to unlock full historical comparisons.</p>
            ) : null}
          </section>
        </>
      )}
    </div>
  );
}
