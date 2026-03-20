import { SeverityCounts } from "@/lib/audit";

const order: Array<keyof SeverityCounts> = ["critical", "high", "medium", "low"];

const tone: Record<keyof SeverityCounts, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-sky-100 text-sky-700 border-sky-200",
};

interface Props {
  counts: SeverityCounts;
}

export function SeverityBreakdown({ counts }: Props) {
  const total = counts.critical + counts.high + counts.medium + counts.low;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Findings by Severity</h3>
      <p className="mt-1 text-xs text-slate-500">{total} findings in latest run</p>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {order.map((level) => (
          <div key={level} className={`rounded-xl border px-3 py-3 ${tone[level]}`}>
            <p className="text-xs font-semibold uppercase tracking-[0.14em]">{level}</p>
            <p className="mt-1 text-2xl font-bold">{counts[level]}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
