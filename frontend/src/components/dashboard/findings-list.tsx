"use client";

import { useState } from "react";

import { AuditFinding, Recommendation, formatCurrency, formatFindingMetric } from "@/lib/audit";

interface Props {
  findings: AuditFinding[];
  recommendations?: Recommendation[];
  maxItems?: number;
  title?: string;
}

const severityConfig: Record<string, { badge: string; label: string }> = {
  critical: { badge: "bg-rose-100 text-rose-700", label: "Critical" },
  high: { badge: "bg-orange-100 text-orange-700", label: "High" },
  medium: { badge: "bg-amber-100 text-amber-700", label: "Medium" },
  low: { badge: "bg-sky-100 text-sky-700", label: "Low" },
};

export function FindingsList({ findings, recommendations = [], maxItems, title = "Findings" }: Props) {
  const categories = ["All", ...Array.from(new Set(findings.map((finding) => finding.category)))];
  const [activeTab, setActiveTab] = useState("All");
  const rows = (activeTab === "All" ? findings : findings.filter((finding) => finding.category === activeTab)).slice(0, maxItems ?? Infinity);
  const recommendationMap = new Map(
    recommendations.flatMap((item) => item.audit_finding_id ? [[item.audit_finding_id, item]] : []),
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-xs text-slate-500">Performance findings with explainable signals</p>
      {categories.length > 1 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {categories.map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => setActiveTab(category)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                activeTab === category ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      ) : null}

      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-emerald-700">No major issues detected in the latest run.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((finding) => {
            const config = severityConfig[finding.severity] || severityConfig.low;
            const recommendation = recommendationMap.get(finding.id);
            const hasDollarImpact = finding.estimated_waste > 0 || finding.estimated_uplift > 0;
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
                    {finding.metric_value !== null ? (
                      <div className="mt-2 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
                        <span className="text-slate-500">Actual</span>
                        <span className="font-semibold text-rose-700">{formatFindingMetric(finding.metric_value, finding.category)}</span>
                        {finding.threshold_value !== null ? (
                          <>
                            <span className="text-slate-300">vs</span>
                            <span className="text-slate-500">Threshold</span>
                            <span className="font-semibold text-slate-700">{formatFindingMetric(finding.threshold_value, finding.category)}</span>
                          </>
                        ) : null}
                      </div>
                    ) : null}
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                      <span
                        className={`rounded-full px-2 py-1 font-semibold ${
                          finding.confidence_label === "High"
                            ? "bg-emerald-100 text-emerald-700"
                            : finding.confidence_label === "Medium"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {finding.confidence_label} confidence
                      </span>
                      <span className="text-slate-500">{finding.confidence_reason}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{finding.entity_name || finding.affected_entity}</p>
                    <p className="mt-2 text-xs text-slate-600">
                      <span className="font-semibold text-slate-700">Inspect next:</span> {finding.inspection_target}
                    </p>
                  </div>
                  <div className="text-right text-xs">
                    <p className="text-rose-700">Waste {formatCurrency(finding.estimated_waste)}</p>
                    <p className="text-emerald-700">Uplift {formatCurrency(finding.estimated_uplift)}</p>
                    {!hasDollarImpact ? (
                      <p className="mt-1 text-slate-500">Qualitative risk: the signal matters even when modeled dollar impact is low.</p>
                    ) : null}
                  </div>
                </div>
                {recommendation ? (
                  <div className="mt-3 rounded-xl border border-sky-100 bg-white px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-sky-700">Recommended action</p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{recommendation.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{recommendation.body}</p>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
