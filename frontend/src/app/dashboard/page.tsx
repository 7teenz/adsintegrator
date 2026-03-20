"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DataSync } from "@/components/dashboard/data-sync";
import { HealthScore } from "@/components/dashboard/health-score";
import { TopOpportunities } from "@/components/dashboard/top-opportunities";
import { TrendWidget } from "@/components/dashboard/trend-widget";
import { WorstPerformers } from "@/components/dashboard/worst-performers";
import { Spinner } from "@/components/ui/spinner";
import { apiFetch } from "@/lib/api";
import {
  AuditDashboardData,
  analysisWindowDays,
  deriveBiggestLeak,
  deriveConfidence,
  deriveTopActions,
  formatCurrency,
  formatDate,
} from "@/lib/audit";
import { getUser } from "@/lib/auth";

function compactNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export default function DashboardPage() {
  const user = getUser();
  const [data, setData] = useState<AuditDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await apiFetch<AuditDashboardData>("/audit/dashboard");
      setData(response);
      setNeedsSetup(false);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load audit dashboard";
      if (message.includes("No Meta connection") || message.includes("No ad account selected")) {
        setNeedsSetup(true);
        setError(null);
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const report = data?.audit ?? null;
  const confidence = report ? deriveConfidence(report, data?.data_mode) : null;
  const topActions = report ? deriveTopActions(report) : [];
  const biggestLeak = report ? deriveBiggestLeak(report) : null;
  const isAggregateMode = data?.data_mode === "period_aggregate";
  const days = report ? analysisWindowDays(report.analysis_start, report.analysis_end) : 0;

  const executiveSummary = useMemo(() => {
    if (!report) return "Upload a Meta Ads export to generate your first executive audit.";
    if (report.findings_count === 0) return "The latest audit did not detect major issues. Use the full report to review supporting evidence and scope.";
    if (report.health_score >= 75) return "The account looks broadly healthy, but there are still a few concentrated leaks worth fixing.";
    if (report.health_score >= 55) return "The audit found meaningful inefficiencies. Fixing the top issues should improve efficiency quickly.";
    return "The latest audit shows multiple costly issues. This account needs active cleanup, not just monitoring.";
  }, [report]);

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner label="Loading dashboard..." /></div>;
  }

  if (needsSetup) {
    return (
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Upload first</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">
            {user?.full_name ? `${user.full_name}, upload your Meta Ads history to generate the first audit` : "Upload your Meta Ads history to generate the first audit"}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            This local MVP is built around uploaded Meta Ads exports. Import a CSV or XLSX report, then run an audit to unlock the executive dashboard.
          </p>
        </section>
        <DataSync onSyncComplete={() => void load()} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-rose-700">{error}</p>
          <button type="button" onClick={() => void load()} className="text-sm font-semibold text-rose-700 underline">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data || !report) {
    return (
      <div className="space-y-6">
        <DataSync onSyncComplete={() => void load()} />
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Audit dashboard</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">No audit data yet</h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            Import a Meta Ads export, review the import quality, and run your first audit to unlock the executive dashboard and full report.
          </p>
          <Link href="/dashboard/audits" className="mt-5 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Open audit page
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DataSync onSyncComplete={() => void load()} />

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Executive overview</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          {user?.full_name ? `${user.full_name}, here is what needs attention now` : "Here is what needs attention now"}
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">{executiveSummary}</p>
        <div className="mt-5 flex flex-wrap gap-3 text-xs text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1">{report.campaign_count} campaigns · {report.ad_set_count} ad sets · {report.ad_count} ads</span>
          <span className="rounded-full bg-slate-100 px-3 py-1">{formatDate(report.analysis_start)} to {formatDate(report.analysis_end)} · {days} days</span>
          <span className="rounded-full bg-sky-50 px-3 py-1 text-sky-700">Confidence: {confidence?.confidenceLabel}</span>
          <span className="rounded-full bg-slate-100 px-3 py-1">{isAggregateMode ? "Aggregate upload" : "Daily trend data available"}</span>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/dashboard/audits" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Open full report
          </Link>
          <Link href="/dashboard/settings" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
            Data controls
          </Link>
        </div>
      </section>

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
          <p className="mt-2 text-xs text-slate-500">Modeled waste from the latest audit.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Potential Lift</p>
          <p className="mt-3 text-3xl font-semibold text-emerald-700">{formatCurrency(report.total_estimated_uplift)}</p>
          <p className="mt-2 text-xs text-slate-500">Modeled upside if the main issues are fixed.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Confidence</p>
          <p className="mt-3 text-2xl font-semibold text-slate-900">{confidence?.confidenceLabel}</p>
          <p className="mt-2 text-xs text-slate-500">{confidence?.confidenceReason}</p>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">What needs attention now</h3>
              <p className="mt-1 text-xs text-slate-500">The three actions most likely to improve efficiency first.</p>
            </div>
            <p className="text-xs text-slate-500">{report.findings_count} findings</p>
          </div>
          <div className="mt-4 space-y-3">
            {topActions.length > 0 ? topActions.map((action, index) => (
              <article key={action.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex items-start gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                    {index + 1}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{action.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{action.whyItMatters}</p>
                  </div>
                </div>
              </article>
            )) : <p className="text-sm text-slate-500">No urgent actions were triggered in the latest run.</p>}
          </div>
        </div>

        <div className="xl:col-span-5 space-y-4">
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Top performance leak</h3>
            {biggestLeak ? (
              <>
                <p className="mt-3 text-lg font-semibold text-slate-900">{biggestLeak.title}</p>
                <p className="mt-2 text-sm text-slate-600">{biggestLeak.description}</p>
                <p className="mt-3 text-xs font-semibold text-rose-700">
                  Estimated waste: {formatCurrency(biggestLeak.waste)} · {biggestLeak.entityName}
                </p>
              </>
            ) : (
              <p className="mt-3 text-sm text-slate-500">No single leak stands out in the current audit.</p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Scope snapshot</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Spend analyzed</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{formatCurrency(report.total_spend)}</p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Date range</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{days} days</p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Campaigns</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{compactNumber(report.campaign_count)}</p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Data mode</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{isAggregateMode ? "Aggregate" : "Daily"}</p>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <TopOpportunities findings={data.top_opportunities.slice(0, 5)} maxItems={5} />
        </div>
        <div className="xl:col-span-5">
          <WorstPerformers title="Weakest campaigns" items={data.worst_campaigns.slice(0, 5)} />
        </div>
      </section>

      {!isAggregateMode ? (
        <TrendWidget points={data.spend_roas_trend ?? []} showRoas />
      ) : (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Trend layer limited</h3>
          <p className="mt-2 text-sm text-slate-700">
            This upload is an aggregate export, so trend analysis is limited. Use the full report for executive actions and supporting evidence instead.
          </p>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Recommended next move</h3>
            <p className="mt-1 text-xs text-slate-500">Use the full report to inspect evidence, grouped findings, and audit history.</p>
          </div>
          <Link href="/dashboard/audits" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Open full report
          </Link>
        </div>
      </section>
    </div>
  );
}
