import { TrendPoint, formatCurrency } from "@/lib/audit";

interface Props {
  title?: string;
  points: TrendPoint[];
  showRoas?: boolean;
}

function chartPath(values: number[], height: number, width: number): string {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

export function TrendWidget({ title = "Spend and ROAS Trend", points, showRoas = true }: Props) {
  const spendValues = points.map((point) => point.spend);
  const roasValues = points.map((point) => point.roas);
  const spendPath = chartPath(spendValues, 96, 420);
  const roasPath = chartPath(roasValues, 96, 420);

  const latest = points[points.length - 1];

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-xs text-slate-500">Recent account performance window</p>

      {points.length < 2 ? (
        <p className="mt-4 text-sm text-slate-500">Trend data will appear after sync and at least two days of insights.</p>
      ) : (
        <>
          <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-3">
            <svg viewBox="0 0 420 96" className="h-28 w-full">
              <path d={spendPath} fill="none" stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" />
              {showRoas ? <path d={roasPath} fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" /> : null}
            </svg>
            <div className="mt-2 flex items-center gap-4 text-xs">
              <span className="text-slate-700">Spend</span>
              {showRoas ? <span className="text-sky-700">ROAS</span> : null}
            </div>
          </div>
          {latest ? (
            <div className="mt-3 flex items-center justify-between text-sm text-slate-600">
              <span>Latest spend {formatCurrency(latest.spend)}</span>
              {showRoas ? <span>Latest ROAS {latest.roas.toFixed(2)}</span> : <span>Upgrade for ROAS trend</span>}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
