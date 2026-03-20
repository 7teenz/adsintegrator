"use client";

import { AuditAISummary, AuditReport, cleanAiSummaryText, deriveTopActions } from "@/lib/audit";

interface Props {
  summary: AuditAISummary;
  report: AuditReport;
  onRegenerate: () => Promise<void>;
  regenerating: boolean;
}

function splitParagraphs(text: string | null | undefined): string[] {
  return (cleanAiSummaryText(text) || text || "")
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function AISummaryBlock({ summary, report, onRegenerate, regenerating }: Props) {
  const executiveVerdict = cleanAiSummaryText(summary.short_executive_summary) || "The audit found clear account-level actions worth prioritizing now.";
  const whyPerformanceIsSlipping = splitParagraphs(summary.detailed_audit_explanation);
  const supportingEvidence = splitParagraphs(summary.prioritized_action_plan);
  const topActions = deriveTopActions(report);
  const wins = report.health_score >= 75
    ? ["The account still shows a healthy baseline despite the issues surfaced in this run."]
    : report.findings_count === 0
      ? ["No major rule-based issues were triggered in the latest audit."]
      : ["The account has enough usable signal to rank the biggest leaks instead of guessing."];

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Consultant interpretation</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">What this likely means</h3>
        </div>
        <div className="flex items-center gap-2">
          <span
            title={`Provider: ${summary.provider} | Model: ${summary.model} | Status: ${summary.status}`}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-300 text-xs text-slate-500"
          >
            i
          </span>
          <button
            type="button"
            onClick={() => void onRegenerate()}
            disabled={regenerating}
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
          >
            {regenerating ? "Regenerating..." : "Regenerate"}
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Executive verdict</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">{executiveVerdict}</p>

          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Top 3 actions</p>
            <div className="mt-2 space-y-2">
              {topActions.map((action, index) => (
                <div key={action.id} className="rounded-lg border border-white bg-white px-3 py-3">
                  <p className="text-sm font-semibold text-slate-900">{index + 1}. {action.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">{action.whyItMatters}</p>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="space-y-4">
          <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detected from data</p>
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              {supportingEvidence.length > 0 ? supportingEvidence.slice(0, 3).map((item) => <p key={item}>{item}</p>) : (
                <p>The rule engine detected the strongest issues and ranked the most meaningful actions for this run.</p>
              )}
            </div>
          </article>

          <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Why performance is slipping</p>
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              {whyPerformanceIsSlipping.length > 0 ? whyPerformanceIsSlipping.slice(0, 3).map((item) => <p key={item}>{item}</p>) : (
                <p>The current mix of findings suggests the account is losing efficiency through a few concentrated weak points rather than across every campaign.</p>
              )}
            </div>
          </article>

          <article className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">What is working well</p>
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              {wins.map((item) => <p key={item}>{item}</p>)}
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
