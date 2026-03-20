"use client";

import { AuditAISummary } from "@/lib/audit";

interface Props {
  summary: AuditAISummary;
  canViewDetailed: boolean;
  onRegenerate: () => Promise<void>;
  regenerating: boolean;
}

export function AISummaryBlock({ summary, canViewDetailed, onRegenerate, regenerating }: Props) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">AI Explanation Layer</p>
          <p className="mt-1 text-xs text-slate-500">
            Provider: {summary.provider} | Model: {summary.model} | Status: {summary.status}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void onRegenerate()}
          disabled={regenerating}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
        >
          {regenerating ? "Regenerating..." : "Regenerate"}
        </button>
      </div>

      <article className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4">
        <h3 className="text-sm font-semibold text-slate-900">Short Executive Summary</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">{summary.short_executive_summary}</p>
      </article>

      {canViewDetailed ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">Detailed Audit Explanation</h3>
            <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">{summary.detailed_audit_explanation}</p>
          </article>
          <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">Prioritized Action Plan</h3>
            <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">{summary.prioritized_action_plan}</p>
          </article>
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-slate-900">Premium unlock</p>
          <p className="mt-1 text-sm text-slate-600">
            Upgrade to view detailed explanation and full prioritized action plan.
          </p>
        </div>
      )}

      {summary.status === "failed" && summary.error_message ? (
        <p className="mt-3 text-xs text-rose-600">Generation fallback used: {summary.error_message}</p>
      ) : null}
    </section>
  );
}
