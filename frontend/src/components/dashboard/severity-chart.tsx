"use client";

interface Props {
  critical: number;
  warning: number;
  info: number;
}

const SEG_COLORS = [
  { key: "critical", color: "#ef4444", label: "Critical" },
  { key: "warning", color: "#f59e0b", label: "Warning" },
  { key: "info", color: "#3b82f6", label: "Info" },
] as const;

/**
 * Pure-CSS donut chart for findings by severity.
 * No chart library required — uses conic-gradient.
 */
export function SeverityChart({ critical, warning, info }: Props) {
  const total = critical + warning + info;

  // Build conic-gradient segments
  const segments: { color: string; pct: number }[] = [];
  if (critical > 0) segments.push({ color: "#ef4444", pct: (critical / total) * 100 });
  if (warning > 0) segments.push({ color: "#f59e0b", pct: (warning / total) * 100 });
  if (info > 0) segments.push({ color: "#3b82f6", pct: (info / total) * 100 });

  let gradient = "conic-gradient(";
  let cum = 0;
  segments.forEach((seg, i) => {
    gradient += `${seg.color} ${cum}% ${cum + seg.pct}%`;
    cum += seg.pct;
    if (i < segments.length - 1) gradient += ", ";
  });
  gradient += ")";

  if (total === 0) {
    gradient = "conic-gradient(#e2e8f0 0% 100%)";
  }

  return (
    <div className="flex items-center gap-6">
      {/* Donut */}
      <div className="relative h-28 w-28 flex-shrink-0">
        <div
          className="h-full w-full rounded-full"
          style={{ background: gradient }}
        />
        {/* Inner circle to create donut hole */}
        <div className="absolute inset-0 m-auto h-16 w-16 rounded-full bg-white flex items-center justify-center">
          <span className="text-lg font-bold text-slate-900">{total}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="space-y-2">
        {SEG_COLORS.map((s) => {
          const count = s.key === "critical" ? critical : s.key === "warning" ? warning : info;
          return (
            <div key={s.key} className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-sm text-slate-600">
                {s.label}: <span className="font-semibold text-slate-900">{count}</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
