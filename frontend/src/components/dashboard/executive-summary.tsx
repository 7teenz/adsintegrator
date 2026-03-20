import { AuditReport, formatCurrency, formatDate } from "@/lib/audit";

interface Props {
  report: AuditReport;
  compact?: boolean;
}

export function ExecutiveSummary({ report, compact = false }: Props) {
  const scoreLabel = report.health_score >= 75 ? "strong" : report.health_score >= 55 ? "mixed" : "at risk";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Executive Summary</p>
      <h2 className={`mt-2 font-semibold text-slate-900 ${compact ? "text-lg" : "text-2xl"}`}>
        Account efficiency is currently {scoreLabel}
      </h2>
      <p className="mt-2 text-sm text-slate-600">
        Between {formatDate(report.analysis_start)} and {formatDate(report.analysis_end)}, the engine detected {report.findings_count} findings with estimated waste of {formatCurrency(report.total_wasted_spend)} and a modeled uplift opportunity of {formatCurrency(report.total_estimated_uplift)}.
      </p>
      <p className="mt-2 text-sm text-slate-600">
        This summary is generated from the current audit results and is designed to give a fast read on account health before you dive into the full report.
      </p>
    </section>
  );
}
