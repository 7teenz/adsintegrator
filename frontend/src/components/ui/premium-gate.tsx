"use client";

import { type ReactNode } from "react";
import { usePlan } from "@/lib/plan";

interface Props {
  children: ReactNode;
  /** Label shown on the lock overlay */
  label?: string;
  /** Extra description below the label */
  description?: string;
  /** Minimum height for the blurred placeholder */
  minHeight?: string;
}

export function PremiumGate({
  children,
  label = "Premium Feature",
  description = "Upgrade to unlock this section and get the full picture.",
  minHeight = "180px",
}: Props) {
  const { isPremium } = usePlan();

  if (isPremium) return <>{children}</>;

  return (
    <div className="relative overflow-hidden rounded-2xl" style={{ minHeight }}>
      {/* Blurred content underneath — visible but unreadable */}
      <div className="pointer-events-none select-none blur-[6px] opacity-60" aria-hidden="true">
        {children}
      </div>

      {/* Lock overlay */}
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/60 backdrop-blur-[2px]">
        <div className="flex flex-col items-center text-center px-6 max-w-sm">
          {/* Lock icon */}
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-50 mb-3">
            <svg
              className="h-5 w-5 text-brand-600"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
              />
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="mt-1 text-xs text-slate-500 leading-relaxed">{description}</p>
          <a
            href="/dashboard/upgrade"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-brand-700 transition-colors"
          >
            Unlock with Premium
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  );
}
