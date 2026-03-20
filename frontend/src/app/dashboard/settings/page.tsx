"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import { usePlan } from "@/lib/plan";

const freeFeatures = [
  "1 ad account",
  "Health Score and estimated waste",
  "Top 3 findings",
  "Shorter history",
  "No advanced charts",
  "No recurring monitoring",
];

const premiumFeatures = [
  "Longer history",
  "Full findings",
  "Full recommendations",
  "Advanced dashboard",
  "Recurring monitoring readiness",
  "Downloadable reports readiness",
];

export default function SettingsPage() {
  const { plan, isPremium, setPlan, loading } = usePlan();
  const [pendingTier, setPendingTier] = useState<"free" | "premium" | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState("");

  async function switchPlan(nextTier: "free" | "premium") {
    setPendingTier(nextTier);
    try {
      await setPlan(nextTier);
    } finally {
      setPendingTier(null);
    }
  }

  async function resetImportedData() {
    setResetting(true);
    setResetMessage("");
    try {
      const response = await apiFetch<{ message: string }>("/debug/reset-imported-data", { method: "POST" });
      setResetMessage(response.message || "Data reset complete");
    } catch (err) {
      setResetMessage(err instanceof Error ? err.message : "Failed to reset imported data");
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">Plan & Access</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Local MVP Billing</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">
          Stripe is intentionally skipped for now. This page controls backend subscription state directly for local MVP testing.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className={`rounded-2xl border p-6 shadow-sm ${!isPremium ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white"}`}>
          <p className="text-xs font-semibold uppercase tracking-[0.16em]">Free</p>
          <h2 className="mt-2 text-2xl font-semibold">Starter Audit</h2>
          <ul className="mt-4 space-y-2 text-sm">
            {freeFeatures.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => void switchPlan("free")}
            disabled={loading || pendingTier !== null}
            className={`mt-5 rounded-lg px-4 py-2 text-sm font-semibold ${
              isPremium ? "bg-slate-100 text-slate-700" : "bg-white text-slate-900"
            } disabled:opacity-60`}
          >
            {pendingTier === "free" ? "Switching..." : "Use Free Plan"}
          </button>
        </article>

        <article className={`rounded-2xl border p-6 shadow-sm ${isPremium ? "border-emerald-300 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Premium</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">Pro Audit Intelligence</h2>
          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            {premiumFeatures.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => void switchPlan("premium")}
            disabled={loading || pendingTier !== null}
            className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {pendingTier === "premium" ? "Switching..." : isPremium ? "Premium Active" : "Upgrade to Premium"}
          </button>
        </article>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Current Access</h3>
        <p className="mt-2 text-sm text-slate-600">
          Active plan: <span className="font-semibold text-slate-900">{plan}</span>
        </p>
        <p className="mt-2 text-sm text-slate-600">
          Backend entitlements are enforced server-side for dashboard, findings, history, and account limits.
        </p>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Data Reset (Debug)</h3>
        <p className="mt-2 text-sm text-slate-600">
          Clears imported sync data, related audits, and sync job history for your selected account.
        </p>
        <button
          type="button"
          onClick={() => void resetImportedData()}
          disabled={resetting}
          className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
        >
          {resetting ? "Resetting..." : "Reset Imported Data"}
        </button>
        {resetMessage ? <p className="mt-3 text-sm text-slate-600">{resetMessage}</p> : null}
      </section>
    </div>
  );
}
