"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiFetch } from "@/lib/api";

export type PlanTier = "free" | "premium" | "agency";

export interface PlanLimits {
  maxFindings: number;
  maxHistory: number;
  showDetailedOpportunities: boolean;
  showAdvancedCharts: boolean;
  showDeepAnalysis: boolean;
  showRecommendations: boolean;
  dateRangeDays: number;
}

interface EntitlementsApiResponse {
  plan_tier: string;
  max_ad_accounts: number;
  max_findings: number;
  max_recommendations: number;
  max_history_items: number;
  max_trend_points: number;
  max_reports_per_month: number;
  show_advanced_charts: boolean;
  show_recurring_monitoring: boolean;
  show_full_recommendations: boolean;
}

function defaultLimits(): PlanLimits {
  return {
    maxFindings: 3,
    maxHistory: 4,
    showDetailedOpportunities: false,
    showAdvancedCharts: false,
    showDeepAnalysis: false,
    showRecommendations: false,
    dateRangeDays: 30,
  };
}

export interface PlanContextValue {
  tier: PlanTier;
  plan: PlanTier;
  limits: PlanLimits;
  isPremium: boolean;
  loading: boolean;
  setTier: (tier: PlanTier) => Promise<void>;
  setPlan: (tier: PlanTier) => Promise<void>;
  refresh: () => Promise<void>;
}

const defaultContext: PlanContextValue = {
  tier: "free",
  plan: "free",
  limits: defaultLimits(),
  isPremium: false,
  loading: true,
  setTier: async () => {},
  setPlan: async () => {},
  refresh: async () => {},
};

const PlanContext = createContext<PlanContextValue>(defaultContext);

function normalizeTier(tier: string): PlanTier {
  if (tier === "premium" || tier === "agency") return tier;
  return "free";
}

function toLimits(ent: EntitlementsApiResponse): PlanLimits {
  return {
    maxFindings: ent.max_findings,
    maxHistory: ent.max_history_items,
    showDetailedOpportunities: ent.show_full_recommendations,
    showAdvancedCharts: ent.show_advanced_charts,
    showDeepAnalysis: ent.show_advanced_charts,
    showRecommendations: ent.show_full_recommendations,
    dateRangeDays: ent.show_advanced_charts ? 365 : 30,
  };
}

export function PlanProvider({ children }: { children: ReactNode }) {
  const [tier, setTierState] = useState<PlanTier>("free");
  const [limits, setLimits] = useState<PlanLimits>(defaultLimits());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const ent = await apiFetch<EntitlementsApiResponse>("/billing/entitlements");
      setTierState(normalizeTier(ent.plan_tier));
      setLimits(toLimits(ent));
    } catch {
      setTierState("free");
      setLimits(defaultLimits());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setTier = useCallback(async (nextTier: PlanTier) => {
    await apiFetch("/billing/dev/plan", {
      method: "POST",
      body: JSON.stringify({ plan_tier: nextTier }),
    });
    await refresh();
  }, [refresh]);

  const value = useMemo<PlanContextValue>(
    () => ({
      tier,
      plan: tier,
      limits,
      isPremium: tier === "premium" || tier === "agency",
      loading,
      setTier,
      setPlan: setTier,
      refresh,
    }),
    [tier, limits, loading, setTier, refresh],
  );

  return <PlanContext.Provider value={value}>{children}</PlanContext.Provider>;
}

export function usePlan(): PlanContextValue {
  return useContext(PlanContext);
}
