"use client";

import { ReactNode } from "react";

import { usePlan } from "@/lib/plan";
import { UpgradeCta } from "@/components/billing/upgrade-cta";

interface PlanGateProps {
  children: ReactNode;
  title?: string;
  message?: string;
  compact?: boolean;
}

export function PlanGate({
  children,
  title = "Premium Feature",
  message = "This section is available on Premium.",
  compact = false,
}: PlanGateProps) {
  const { isPremium } = usePlan();

  if (isPremium) {
    return <>{children}</>;
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="pointer-events-none blur-[2px] opacity-50">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center bg-white/75 p-4">
        <UpgradeCta title={title} body={message} compact={compact} buttonLabel="Unlock Premium" />
      </div>
    </div>
  );
}
