"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface AdAccount {
  id: string;
  account_id: string;
  account_name: string | null;
  currency: string | null;
  timezone: string | null;
  business_name: string | null;
  account_status: number | null;
  is_selected: boolean;
}

const STATUS_LABELS: Record<number, string> = {
  1: "Active",
  2: "Disabled",
  3: "Unsettled",
  7: "Pending Review",
  8: "Pending Closure",
  9: "In Grace Period",
  100: "Temporarily Unavailable",
  101: "Closed",
};

interface Props {
  onSelect: () => void;
}

export function AdAccountSelector({ onSelect }: Props) {
  const [accounts, setAccounts] = useState<AdAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function loadAccounts(refresh = false) {
    try {
      if (refresh) {
        setRefreshing(true);
        const refreshed = await apiFetch<AdAccount[]>("/meta/ad-accounts/refresh", { method: "POST" });
        setAccounts(refreshed);
      } else {
        const data = await apiFetch<AdAccount[]>("/meta/ad-accounts");
        setAccounts(data);
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ad accounts")
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadAccounts(false);
  }, []);

  async function handleSelect(accountId: string) {
    setSelecting(accountId);
    setError("");
    try {
      await apiFetch("/meta/ad-accounts/select", {
        method: "POST",
        body: JSON.stringify({ account_id: accountId }),
      });
      onSelect();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to select ad account")
    } finally {
      setSelecting(null);
    }
  }

  if (loading) {
    return (
      <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-6">
        <div className="space-y-3">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-20 animate-pulse rounded-2xl bg-slate-200" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Select an ad account</h3>
          <p className="mt-1 text-sm text-slate-500">
            We only store the chosen account pointer now. Campaign, ad set, and audit sync come in the next phase.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void loadAccounts(true)} disabled={refreshing}>
          {refreshing ? "Refreshing..." : "Refresh from Meta"}
        </Button>
      </div>

      {error ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {accounts.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">
          No ad accounts were returned by Meta for this user yet.
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {accounts.map((account) => (
            <article
              key={account.account_id}
              className={`rounded-2xl border bg-white p-4 transition ${
                account.is_selected ? "border-brand-500 shadow-sm" : "border-slate-200"
              }`}
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-semibold text-slate-900">
                      {account.account_name || account.account_id}
                    </h4>
                    {account.account_status !== null ? (
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                        {STATUS_LABELS[account.account_status] || `Status ${account.account_status}`}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span>{account.account_id}</span>
                    {account.currency ? <span>{account.currency}</span> : null}
                    {account.timezone ? <span>{account.timezone}</span> : null}
                    {account.business_name ? <span>{account.business_name}</span> : null}
                  </div>
                </div>
                <Button
                  onClick={() => void handleSelect(account.account_id)}
                  disabled={selecting === account.account_id}
                  variant={account.is_selected ? "primary" : "secondary"}
                >
                  {selecting === account.account_id
                    ? "Saving..."
                    : account.is_selected
                      ? "Selected"
                      : "Use this account"}
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
