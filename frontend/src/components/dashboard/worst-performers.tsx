import { LeaderboardItem, formatCurrency, formatPercent } from "@/lib/audit";

interface Props {
  title: string;
  items: LeaderboardItem[];
}

export function WorstPerformers({ title, items }: Props) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <div className="mt-4 space-y-2">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">No records available.</p>
        ) : (
          items.map((item) => (
            <article key={item.entity_id} className="rounded-xl border border-slate-100 px-3 py-3">
              <p className="truncate text-sm font-semibold text-slate-900">{item.entity_name}</p>
              <div className="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-600">
                <span>Spend {formatCurrency(item.spend)}</span>
                <span>ROAS {item.roas.toFixed(2)}</span>
                <span>CPA {formatCurrency(item.cpa)}</span>
                <span>CTR {formatPercent(item.ctr)}</span>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
