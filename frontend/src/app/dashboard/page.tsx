"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DataSync } from "@/components/dashboard/data-sync";
import { HealthScore } from "@/components/dashboard/health-score";
import { SeverityBreakdown } from "@/components/dashboard/severity-breakdown";
import { TopOpportunities } from "@/components/dashboard/top-opportunities";
import { TrendWidget } from "@/components/dashboard/trend-widget";
import { WorstPerformers } from "@/components/dashboard/worst-performers";
import { apiFetch } from "@/lib/api";
import { AuditDashboardData, AuditFinding, MetricSplit, cleanAiSummaryText, formatCurrency, formatDate } from "@/lib/audit";
import { getUser } from "@/lib/auth";
import { usePlan } from "@/lib/plan";

function shortSummary(score: number, waste: number, findings: number): string {
  if (score >= 75) return `Strong overall efficiency. ${findings} findings, ${formatCurrency(waste)} estimated waste to reclaim.`;
  if (score >= 55) return `Mixed efficiency profile. ${findings} findings with ${formatCurrency(waste)} likely wasted spend.`;
  return `High-risk efficiency state. ${findings} findings and ${formatCurrency(waste)} estimated waste require action.`;
}

function formatCompact(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function formatDelta(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function formatWindow(start: string, end: string): string {
  if (start === end) return formatDate(start);
  return `${formatDate(start)} to ${formatDate(end)}`;
}

function severityBadgeClass(severity: string): string {
  switch (severity) {
    case "critical":
      return "border-rose-200 bg-rose-50 text-rose-700";
    case "high":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "medium":
      return "border-amber-200 bg-amber-50 text-amber-700";
    default:
      return "border-sky-200 bg-sky-50 text-sky-700";
  }
}

function MetricCard({ label, value, tone = "default", note }: { label: string; value: string; tone?: "default" | "danger" | "success"; note?: string }) {
  const valueClass = tone === "danger" ? "text-rose-700" : tone === "success" ? "text-emerald-700" : "text-slate-900";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${valueClass}`}>{value}</p>
      {note ? <p className="mt-2 text-xs text-slate-500">{note}</p> : null}
    </div>
  );
}

function MixCard({ title, items }: { title: string; items: MetricSplit[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {items.length > 0 ? (
        <div className="mt-3 space-y-2">
          {items.slice(0, 5).map((item) => (
            <div key={item.key} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs">
              <span className="text-slate-700">{item.label}</span>
              <span className="font-semibold text-slate-900">{item.value.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No data yet</p>
      )}
    </div>
  );
}

function AggregateSummaryLayout({
  data,
  summary,
  freeFindings,
  userName,
  isPremium,
}: {
  data: AuditDashboardData;
  summary: string;
  freeFindings: { id: string; title: string; entity_name: string; affected_entity: string; }[];
  userName?: string;
  isPremium: boolean;
}) {
  const report = data.audit!;
  const kpis = data.kpis;
  const mixSections: { title: string; items: MetricSplit[] }[] = [
    { title: "Objectives", items: kpis.objective_mix },
    { title: "Optimization Goals", items: kpis.optimization_goal_mix },
    { title: "Statuses", items: kpis.status_mix },
  ];
  const highlightFindings = data.top_opportunities.slice(0, 3);
  const primaryRisk = highlightFindings[0];
  const cleanedAiSummary =
    cleanAiSummaryText(report.ai_summary?.short_executive_summary) ||
    "This imported report points to efficiency issues around click quality, conversion output, and budget concentration. The full report expands those findings into deterministic recommendations.";
  const summaryCards = [
    {
      label: "Health Score",
      value: report.health_score.toFixed(1),
      note: `${report.findings_count} deterministic findings across ${report.campaign_count} campaigns`,
      tone: "default" as const,
    },
    {
      label: "Estimated Waste",
      value: formatCurrency(report.total_wasted_spend),
      note: "Spend likely recoverable from the issues detected in this upload",
      tone: "danger" as const,
    },
    {
      label: "Potential Uplift",
      value: formatCurrency(report.total_estimated_uplift),
      note: "Modeled upside if the top findings are addressed",
      tone: "success" as const,
    },
    {
      label: "Report Coverage",
      value: `${report.campaign_count} campaigns`,
      note: `${report.ad_set_count} ad sets analyzed from the imported Meta export`,
      tone: "default" as const,
    },
  ];

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-slate-50 p-8 shadow-sm">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">Imported Meta Report Summary</p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900">
              {userName ? `${userName}, here is what stands out in your uploaded account history` : "Here is what stands out in your uploaded account history"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">{summary}</p>
            <p className="mt-4 max-w-2xl text-sm text-slate-600">
              This file is a period aggregate Meta export, so the dashboard is optimized for account efficiency review, ranking weak campaigns and ad sets, and surfacing the most actionable cost leaks from the imported period.
            </p>
            {primaryRisk ? (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Primary risk in this upload</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">{primaryRisk.title}</p>
                <p className="mt-2 text-sm text-slate-600">{primaryRisk.description}</p>
              </div>
            ) : null}
            {data.limitations.length ? (
              <div className="mt-4 rounded-2xl border border-amber-200 bg-white/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">How to read this report</p>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  {data.limitations.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3 xl:max-w-xs xl:flex-col xl:items-stretch">
            <Link href="/dashboard/audits" className="rounded-lg bg-slate-900 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-slate-800">
              Open Full Report
            </Link>
            {!isPremium ? (
              <Link href="/dashboard/settings" className="rounded-lg border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700 hover:bg-slate-100">
                Upgrade to Premium
              </Link>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Health Score</p>
          <div className="mt-3 flex justify-center">
            <HealthScore score={report.health_score} size="lg" />
          </div>
        </div>
        {summaryCards.slice(1).map((card) => (
          <MetricCard key={card.label} label={card.label} value={card.value} tone={card.tone} note={card.note} />
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Executive Readout</p>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">What this imported report is saying</h3>
            </div>
            <Link href="/dashboard/audits" className="text-sm font-semibold text-slate-700 hover:text-slate-900">
              View report
            </Link>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">{cleanedAiSummary}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Imported window</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">{formatWindow(report.analysis_start, report.analysis_end)}</p>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Account footprint</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">{report.campaign_count} campaigns / {report.ad_set_count} ad sets</p>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Current objective</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">{kpis.objective_mix[0]?.label || "Unknown"}</p>
            </div>
          </div>
        </div>
        <div className="xl:col-span-5">
          <SeverityBreakdown counts={data.severity_counts} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">What needs attention first</h3>
              <p className="mt-1 text-xs text-slate-500">The highest-impact issues surfaced from the uploaded aggregate report.</p>
            </div>
            <p className="text-xs text-slate-500">{report.findings_count} findings detected</p>
          </div>
          <div className="mt-4 space-y-3">
            {highlightFindings.map((finding) => (
              <article key={finding.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${severityBadgeClass(finding.severity)}`}>
                        {finding.severity}
                      </span>
                      <span className="text-xs text-slate-500">{finding.entity_name || finding.affected_entity}</span>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{finding.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{finding.description}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-right">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Waste</p>
                    <p className="mt-1 text-sm font-semibold text-rose-700">{formatCurrency(finding.estimated_waste)}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="xl:col-span-5">
          <TopOpportunities findings={isPremium ? data.top_opportunities : data.top_opportunities.slice(0, 3)} maxItems={isPremium ? 5 : 3} />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Imported performance snapshot</h3>
            <p className="mt-1 text-xs text-slate-500">Core account metrics extracted directly from your uploaded Meta export.</p>
          </div>
          <p className="text-xs text-slate-500">This view is focused on efficiency and allocation, not day-by-day trend analysis.</p>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Spend", formatCurrency(kpis.spend)],
            ["Impressions", formatCompact(kpis.impressions)],
            ["Reach", formatCompact(kpis.reach)],
            ["Clicks", formatCompact(kpis.clicks)],
            ["CTR", `${kpis.ctr.toFixed(2)}%`],
            ["CPC", `$${kpis.cpc.toFixed(2)}`],
            ["CPM", `$${kpis.cpm.toFixed(2)}`],
            ["CPA", `$${kpis.cpa.toFixed(2)}`],
            ["ROAS", `${kpis.roas.toFixed(2)}x`],
            ["Frequency", kpis.frequency.toFixed(2)],
            ["Conversions", formatCompact(kpis.conversions)],
            ["Conversion Value", formatCurrency(kpis.conversion_value)],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <WorstPerformers title="Worst Campaigns" items={isPremium ? data.worst_campaigns : data.worst_campaigns.slice(0, 3)} />
        <WorstPerformers title="Worst Ad Sets" items={isPremium ? data.worst_adsets : data.worst_adsets.slice(0, 3)} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {mixSections.map((section) => (
          <MixCard key={section.title} title={section.title} items={section.items} />
        ))}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Report preview</h3>
            <p className="mt-1 text-xs text-slate-500">A quick snapshot of the findings currently visible from this imported report.</p>
          </div>
          <Link href="/dashboard/audits" className="text-sm font-semibold text-slate-700 hover:text-slate-900">
            Open detailed audit
          </Link>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {freeFindings.length > 0 ? (
            freeFindings.map((finding) => (
              <article key={finding.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">{finding.title}</p>
                <p className="mt-1 text-xs text-slate-500">{finding.entity_name || finding.affected_entity}</p>
              </article>
            ))
          ) : (
            <p className="text-sm text-slate-500">No findings are available to preview yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

export default function DashboardPage() {
  const user = getUser();
  const { isPremium } = usePlan();

  const [data, setData] = useState<AuditDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await apiFetch<AuditDashboardData>("/audit/dashboard");
      setData(response);
      setNeedsSetup(false);
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

  const trendPoints = useMemo(() => {
    if (!data) return [];
    return isPremium ? data.spend_roas_trend : data.spend_roas_trend.slice(-6);
  }, [data, isPremium]);
  const isAggregateMode = data?.data_mode === "period_aggregate";

  if (loading) {
    return <div className="py-20 text-center text-sm text-slate-500">Loading dashboard...</div>;
  }

  if (needsSetup) {
    return (
      <div className="space-y-6">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Upload First</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">
            {user?.full_name ? `${user.full_name}, upload your ads history to generate your first audit` : "Upload your ads history to generate your first audit"}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            For the local MVP, the primary workflow is report upload. Import a raw Facebook Ads CSV or XLSX export, review the dashboard analytics, then run the deterministic audit and AI explanation layer.
          </p>
        </section>
        <DataSync onSyncComplete={() => void load()} />
        <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
          Meta account connection is optional for now and can stay in sample mode. The working MVP path is file upload to analytics and report generation.
        </section>
      </div>
    );
  }

  if (error) {
    return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>;
  }

  if (!data || !data.audit) {
    const kpis = data?.kpis;
    return (
      <div className="space-y-6">
        <DataSync onSyncComplete={() => void load()} />
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Audit Dashboard</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">No audit data yet</h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            Upload a Facebook Ads report file, confirm the dashboard metrics, and run your first audit to unlock score, waste, findings, recommendations, and AI explanation blocks.
          </p>
          <Link href="/dashboard/audits" className="mt-5 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Go to Audit Report
          </Link>
        </section>
        {kpis ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900">Imported Performance Snapshot</h3>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Spend", formatCurrency(kpis.spend)],
                ["Impressions", formatCompact(kpis.impressions)],
                ["Reach", formatCompact(kpis.reach)],
                ["Clicks", formatCompact(kpis.clicks)],
                ["CTR", `${kpis.ctr.toFixed(2)}%`],
                ["CPC", `$${kpis.cpc.toFixed(2)}`],
                ["CPM", `$${kpis.cpm.toFixed(2)}`],
                ["ROAS", `${kpis.roas.toFixed(2)}x`],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    );
  }

  const report = data.audit;
  const kpis = data.kpis;
  const mixSections: { title: string; items: MetricSplit[] }[] = [
    { title: "Objectives", items: kpis.objective_mix },
    { title: "Optimization Goals", items: kpis.optimization_goal_mix },
    { title: "Statuses", items: kpis.status_mix },
  ];
  const freeFindings = report.findings.slice(0, 3);
  const summary = shortSummary(report.health_score, report.total_wasted_spend, report.findings_count);

  if (isAggregateMode) {
    return (
      <div className="space-y-6">
        <DataSync onSyncComplete={() => void load()} />
        <AggregateSummaryLayout
          data={data}
          summary={summary}
          freeFindings={freeFindings}
          userName={user?.full_name ?? undefined}
          isPremium={isPremium}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DataSync onSyncComplete={() => void load()} />

      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">Audit Overview</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">
          {user?.full_name ? `${user.full_name}, here is your account health snapshot` : "Your account health snapshot"}
        </h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">{summary}</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/dashboard/audits" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
            Open Full Report
          </Link>
          {!isPremium ? (
            <Link href="/dashboard/settings" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Upgrade to Premium
            </Link>
          ) : null}
        </div>
        {report.findings_count === 0 ? (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            No deterministic issues were triggered in the latest run. This often happens when imported report fields are limited (for example, no click/conversion-depth columns).
          </div>
        ) : null}
      </section>

      {report.ai_summary ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI Explanation Preview</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">{cleanAiSummaryText(report.ai_summary.short_executive_summary) || report.ai_summary.short_executive_summary}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/dashboard/audits" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
              Open full AI report
            </Link>
            {!isPremium ? (
              <span className="text-xs text-slate-500">Premium unlocks the detailed explanation and prioritized action plan.</span>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Health Score</p>
          <div className="mt-3 flex justify-center">
            <HealthScore score={report.health_score} size="lg" />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Estimated Waste</p>
          <p className="mt-3 text-3xl font-semibold text-rose-700">{formatCurrency(report.total_wasted_spend)}</p>
          <p className="mt-2 text-xs text-slate-500">Visible on free plan</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Potential Uplift</p>
          <p className="mt-3 text-3xl font-semibold text-emerald-700">{formatCurrency(report.total_estimated_uplift)}</p>
          <p className="mt-2 text-xs text-slate-500">Modeled deterministic opportunity</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Window</p>
          <p className="mt-3 text-lg font-semibold text-slate-900">{isPremium ? "Extended history" : "Last 30 days"}</p>
          <p className="mt-2 text-xs text-slate-500">Premium unlocks deeper history and trend context</p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Performance Metrics</h3>
            <p className="mt-1 text-xs text-slate-500">Imported/synced account-level metrics for deterministic analysis.</p>
          </div>
          <p className="text-xs text-slate-500">
            WoW: spend {formatDelta(kpis.wow_spend_delta)}, CTR {formatDelta(kpis.wow_ctr_delta)}, ROAS {formatDelta(kpis.wow_roas_delta)}, CPA {formatDelta(kpis.wow_cpa_delta)}
          </p>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Spend", formatCurrency(kpis.spend)],
            ["Impressions", formatCompact(kpis.impressions)],
            ["Reach", formatCompact(kpis.reach)],
            ["Clicks", formatCompact(kpis.clicks)],
            ["CTR", `${kpis.ctr.toFixed(2)}%`],
            ["CPC", `$${kpis.cpc.toFixed(2)}`],
            ["CPM", `$${kpis.cpm.toFixed(2)}`],
            ["CPA", `$${kpis.cpa.toFixed(2)}`],
            ["ROAS", `${kpis.roas.toFixed(2)}x`],
            ["Frequency", kpis.frequency.toFixed(2)],
            ["Conversions", formatCompact(kpis.conversions)],
            ["Conversion Value", formatCurrency(kpis.conversion_value)],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {mixSections.map((section) => (
          <MixCard key={section.title} title={section.title} items={section.items} />
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-4">
          <SeverityBreakdown counts={data.severity_counts} />
        </div>
        <div className="xl:col-span-8">
          <TopOpportunities findings={isPremium ? data.top_opportunities : data.top_opportunities.slice(0, 3)} maxItems={isPremium ? 5 : 3} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-7">
          {!isPremium ? <TrendWidget title="Spend Trend (Free)" points={trendPoints} showRoas={false} /> : <TrendWidget points={trendPoints} showRoas />}
          {!isPremium ? <p className="mt-2 text-xs text-slate-500">Free plan shows a shorter trend window. Premium unlocks full spend + ROAS history.</p> : null}
        </div>
        <div className="xl:col-span-5">
          <WorstPerformers title="Worst Campaigns" items={isPremium ? data.worst_campaigns : data.worst_campaigns.slice(0, 3)} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-12">
        <div className="xl:col-span-12">
          <WorstPerformers title="Worst Ad Sets" items={isPremium ? data.worst_adsets : data.worst_adsets.slice(0, 3)} />
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Free Plan Snapshot</h3>
        <p className="mt-1 text-xs text-slate-500">Health score, estimated waste, and top findings preview</p>
        <div className="mt-4 space-y-3">
          {freeFindings.map((finding) => (
            <article key={finding.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <p className="text-sm font-semibold text-slate-900">{finding.title}</p>
              <p className="mt-1 text-xs text-slate-600">{finding.entity_name || finding.affected_entity}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
