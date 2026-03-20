"use client";

import { useState } from "react";

import { usePlan } from "@/lib/plan";

interface UpgradeCtaProps {
  title?: string;
  body?: string;
  buttonLabel?: string;
  compact?: boolean;
}

export function UpgradeCta({
  title = "Unlock Premium Audit Intelligence",
  body = "Get full findings, deeper opportunity blocks, advanced trend charts, and longer performance history.",
  buttonLabel = "Upgrade to Premium",
  compact = false,
}: UpgradeCtaProps) {
  const { setPlan, loading } = usePlan();
  const [pending, setPending] = useState(false);

  async function onUpgrade() {
    setPending(true);
    try {
      await setPlan("premium");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={`rounded-2xl border border-amber-200 bg-amber-50/80 ${compact ? "p-4" : "p-6"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Premium</p>
      <h3 className={`mt-2 font-semibold text-slate-900 ${compact ? "text-base" : "text-xl"}`}>{title}</h3>
      <p className="mt-2 text-sm text-slate-600">{body}</p>
      <button
        type="button"
        onClick={() => void onUpgrade()}
        disabled={pending || loading}
        className="mt-4 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
      >
        {pending ? "Updating..." : buttonLabel}
      </button>
    </div>
  );
}
