"use client";

import { AuditFinding, formatCurrency } from "@/lib/audit";

interface Props {
  findings: AuditFinding[];
  maxItems?: number;
  title?: string;
}

const severityConfig: Record<string, { badge: string; label: string }> = {
  critical: { badge: "bg-rose-100 text-rose-700", label: "Critical" },
  high: { badge: "bg-orange-100 text-orange-700", label: "High" },
  medium: { badge: "bg-amber-100 text-amber-700", label: "Medium" },
  low: { badge: "bg-sky-100 text-sky-700", label: "Low" },
};

export function FindingsList({ findings, maxItems, title = "Findings" }: Props) {
  const rows = typeof maxItems === "number" ? findings.slice(0, maxItems) : findings;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-xs text-slate-500">Deterministic findings with explainable signals</p>

      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-emerald-700">No major issues detected in the latest run.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((finding) => {
            const config = severityConfig[finding.severity] || severityConfig.low;
            return (
              <article key={finding.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${config.badge}`}>{config.label}</span>
                      <span className="text-xs uppercase tracking-[0.12em] text-slate-500">{finding.category}</span>
                    </div>
                    <h4 className="mt-2 text-sm font-semibold text-slate-900">{finding.title}</h4>
                    <p className="mt-1 text-sm text-slate-600">{finding.description}</p>
                    <p className="mt-1 text-xs text-slate-500">{finding.entity_name || finding.affected_entity}</p>
                  </div>
                  <div className="text-right text-xs">
                    <p className="text-rose-700">Waste {formatCurrency(finding.estimated_waste)}</p>
                    <p className="text-emerald-700">Uplift {formatCurrency(finding.estimated_uplift)}</p>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
