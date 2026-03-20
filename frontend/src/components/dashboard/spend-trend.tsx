"use client";

interface DataPoint {
  label: string;
  spend: number;
  roas: number;
}

interface Props {
  data: DataPoint[];
}

/**
 * Minimal bar+line sparkline for spend (bars) and ROAS (line dots).
 * Pure CSS/SVG — no charting library.
 */
export function SpendTrend({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-slate-400">
        No trend data available
      </div>
    );
  }

  const maxSpend = Math.max(...data.map((d) => d.spend), 1);
  const maxRoas = Math.max(...data.map((d) => d.roas), 1);
  const barWidth = 100 / data.length;

  // SVG dimensions
  const svgW = 400;
  const svgH = 140;
  const padding = 8;

  // Build ROAS line path
  const roasPoints = data.map((d, i) => {
    const x = padding + ((i + 0.5) / data.length) * (svgW - padding * 2);
    const y = svgH - padding - (d.roas / maxRoas) * (svgH - padding * 2 - 20);
    return { x, y };
  });
  const linePath = roasPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <div>
      <div className="relative" style={{ height: `${svgH}px` }}>
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="h-full w-full" preserveAspectRatio="none">
          {/* Spend bars */}
          {data.map((d, i) => {
            const barH = (d.spend / maxSpend) * (svgH - 40);
            const x = padding + (i / data.length) * (svgW - padding * 2) + 2;
            const w = ((svgW - padding * 2) / data.length) - 4;
            return (
              <rect
                key={`bar-${i}`}
                x={x}
                y={svgH - padding - barH}
                width={Math.max(w, 2)}
                height={barH}
                rx={3}
                className="fill-brand-100"
              />
            );
          })}

          {/* ROAS line */}
          <path d={linePath} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {roasPoints.map((p, i) => (
            <circle key={`dot-${i}`} cx={p.x} cy={p.y} r="3.5" fill="#2563eb" />
          ))}
        </svg>
      </div>

      {/* X-axis labels */}
      <div className="mt-1 flex justify-between px-2">
        {data.length <= 8 ? (
          data.map((d) => (
            <span key={d.label} className="text-[10px] text-slate-400">
              {d.label}
            </span>
          ))
        ) : (
          <>
            <span className="text-[10px] text-slate-400">{data[0].label}</span>
            <span className="text-[10px] text-slate-400">{data[data.length - 1].label}</span>
          </>
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-5">
        <div className="flex items-center gap-1.5">
          <div className="h-2.5 w-2.5 rounded-sm bg-brand-100" />
          <span className="text-[11px] text-slate-500">Spend</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-0.5 w-4 rounded-full bg-brand-600" />
          <span className="text-[11px] text-slate-500">ROAS</span>
        </div>
      </div>
    </div>
  );
}
