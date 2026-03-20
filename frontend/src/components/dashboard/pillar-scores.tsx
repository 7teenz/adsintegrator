"use client";

interface PillarScore {
  id: string;
  name: string;
  score: number;
  weight: number;
  description: string;
}

interface Props {
  pillars: PillarScore[];
}

function barColor(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-amber-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-rose-500";
}

export function PillarScores({ pillars }: Props) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Score Breakdown</h3>
      <div className="mt-4 space-y-4">
        {pillars.map((pillar) => (
          <article key={pillar.id}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-800">{pillar.name}</p>
              <p className="text-sm font-semibold text-slate-900">{Math.round(pillar.score)}</p>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className={`h-full rounded-full ${barColor(pillar.score)}`} style={{ width: `${Math.max(0, Math.min(100, pillar.score))}%` }} />
            </div>
            <p className="mt-1 text-xs text-slate-500">{Math.round(pillar.weight * 100)}% weight. {pillar.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
