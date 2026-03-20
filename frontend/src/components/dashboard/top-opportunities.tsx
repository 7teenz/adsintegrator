import { AuditFinding, formatCurrency } from "@/lib/audit";

interface Props {
  findings: AuditFinding[];
  maxItems?: number;
}

export function TopOpportunities({ findings, maxItems = 5 }: Props) {
  const items = findings.slice(0, maxItems);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Top Opportunities</h3>
      <p className="mt-1 text-xs text-slate-500">Ranked by estimated uplift</p>

      {items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">
          No opportunities were triggered in the latest run. Ensure CSV includes click and conversion-depth columns, then re-run audit.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <p className="text-sm font-semibold text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs text-slate-500">{item.entity_name || item.affected_entity}</p>
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-emerald-700">Uplift {formatCurrency(item.estimated_uplift)}</span>
                <span className="text-rose-700">Waste {formatCurrency(item.estimated_waste)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
