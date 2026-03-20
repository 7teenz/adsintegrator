export interface ScoreBreakdown {
  id: string;
  score_key: string;
  label: string;
  name: string;
  score: number;
  weight: number;
  description: string;
  details: string;
  findings_count: number;
}

export interface AuditFinding {
  id: string;
  rule_id: string;
  severity: "critical" | "high" | "medium" | "low" | string;
  category: string;
  title: string;
  description: string;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  affected_entity: string;
  affected_entity_id: string;
  metric_value: number | null;
  threshold_value: number | null;
  estimated_waste: number;
  estimated_uplift: number;
  recommendation_key: string | null;
  score_impact: number;
}

export interface Recommendation {
  id: string;
  audit_finding_id?: string | null;
  recommendation_key: string;
  title: string;
  body: string;
}

export interface AuditAISummary {
  id: string;
  audit_run_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  status: "completed" | "failed" | "pending" | string;
  short_executive_summary: string;
  detailed_audit_explanation: string;
  prioritized_action_plan: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditJob {
  job_id: string;
  status: string;
}

export interface AuditJobStatus {
  job_id: string;
  status: string;
  error?: string | null;
  completed_audit_id?: string | null;
}

export interface AuditReport {
  id: string;
  health_score: number;
  total_spend: number;
  total_wasted_spend: number;
  total_estimated_uplift: number;
  findings_count: number;
  analysis_start: string;
  analysis_end: string;
  created_at: string;
  campaign_count: number;
  ad_set_count: number;
  ad_count: number;
  findings: AuditFinding[];
  scores: ScoreBreakdown[];
  pillar_scores: ScoreBreakdown[];
  recommendations: Recommendation[];
  ai_summary: AuditAISummary | null;
  job_status: string;
  job_error: string | null;
  celery_task_id: string | null;
}

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface TrendPoint {
  label: string;
  spend: number;
  roas: number;
}

export interface LeaderboardItem {
  entity_id: string;
  entity_name: string;
  spend: number;
  roas: number;
  cpa: number;
  ctr: number;
}

export interface MetricSplit {
  key: string;
  label: string;
  value: number;
}

export interface AccountKpis {
  spend: number;
  impressions: number;
  reach: number;
  clicks: number;
  ctr: number;
  cpc: number;
  cpm: number;
  conversions: number;
  conversion_value: number;
  roas: number;
  frequency: number;
  cpa: number;
  wow_spend_delta: number;
  wow_ctr_delta: number;
  wow_roas_delta: number;
  wow_cpa_delta: number;
  daily_budget_total: number;
  lifetime_budget_total: number;
  objective_mix: MetricSplit[];
  optimization_goal_mix: MetricSplit[];
  status_mix: MetricSplit[];
}

export interface AuditDashboardData {
  audit: AuditReport | null;
  kpis: AccountKpis;
  data_mode: string;
  limitations: string[];
  severity_counts: SeverityCounts;
  top_opportunities: AuditFinding[];
  spend_roas_trend: TrendPoint[];
  worst_campaigns: LeaderboardItem[];
  worst_adsets: LeaderboardItem[];
}

export interface AuditSummary {
  id: string;
  health_score: number;
  total_spend: number;
  total_wasted_spend: number;
  total_estimated_uplift: number;
  findings_count: number;
  analysis_start: string;
  analysis_end: string;
  created_at: string;
}

export type AuditConfidenceLabel = "High" | "Medium" | "Low";

export interface DerivedTopAction {
  id: string;
  title: string;
  whyItMatters: string;
  impactValue: number;
  severity: string;
  entityName: string;
  category: string;
  metricValue: number | null;
  thresholdValue: number | null;
}

export interface DerivedBiggestLeak {
  id: string;
  title: string;
  description: string;
  waste: number;
  uplift: number;
  entityName: string;
  severity: string;
  category: string;
  metricValue: number | null;
  thresholdValue: number | null;
}

export function formatCurrency(value: number): string {
  return "$" + value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function formatFindingMetric(value: number, category: string): string {
  const normalized = category.toLowerCase();
  if (category === "PERFORMANCE" || normalized.includes("ctr") || normalized.includes("conversion")) {
    return `${(value * 100).toFixed(2)}%`;
  }
  if (category === "BUDGET" || normalized.includes("spend") || normalized.includes("cpa") || normalized.includes("cpc") || normalized.includes("cpm")) {
    return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  }
  if (category === "FREQUENCY") {
    return `${value.toFixed(2)}x`;
  }
  return value.toFixed(2);
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function cleanAiSummaryText(text: string | null | undefined): string | null {
  if (!text) return null;

  return (
    text
      .replace(/AI generation fallback used \([^)]+\)\.?/gi, "")
      .replace(/provider not configured\.?/gi, "")
      .replace(/\s{2,}/g, " ")
      .trim() || null
  );
}

export function analysisWindowDays(start: string, end: string): number {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diff = endDate.getTime() - startDate.getTime();
  return Math.max(1, Math.round(diff / 86400000) + 1);
}

export function deriveConfidence(
  report: AuditReport,
  dataMode: string | null | undefined,
): { confidenceLabel: AuditConfidenceLabel; confidenceReason: string } {
  const days = analysisWindowDays(report.analysis_start, report.analysis_end);
  const spend = report.total_spend;
  const campaigns = report.campaign_count;

  if (dataMode === "period_aggregate") {
    return {
      confidenceLabel: "Low",
      confidenceReason: "This audit comes from an aggregate export, so trend and pacing checks are limited.",
    };
  }

  if (days >= 30 && spend >= 1000 && campaigns >= 3) {
    return {
      confidenceLabel: "High",
      confidenceReason: "This report includes enough time range, spend, and campaign coverage for a strong read.",
    };
  }

  if (days >= 14 && campaigns >= 2) {
    return {
      confidenceLabel: "Medium",
      confidenceReason: "The audit is directionally useful, but a longer or richer dataset would increase confidence.",
    };
  }

  return {
    confidenceLabel: "Low",
    confidenceReason: "The current dataset is short or sparse, so only the clearest issues should be treated as decisive.",
  };
}

export function deriveTopActions(report: AuditReport): DerivedTopAction[] {
  const recommendationByFindingId = new Map(
    report.recommendations.flatMap((item) => (item.audit_finding_id ? [[item.audit_finding_id, item]] : [])),
  );
  const recommendationByKey = new Map(report.recommendations.map((item) => [item.recommendation_key, item]));
  const rankedFindings = [...report.findings].sort((a, b) => {
    const aImpact = a.estimated_waste + a.estimated_uplift + a.score_impact * 100;
    const bImpact = b.estimated_waste + b.estimated_uplift + b.score_impact * 100;
    return bImpact - aImpact;
  });

  return rankedFindings.slice(0, 3).map((finding) => {
    const recommendation =
      recommendationByFindingId.get(finding.id) ||
      (finding.recommendation_key ? recommendationByKey.get(finding.recommendation_key) : undefined);
    return {
      id: finding.id,
      title: recommendation?.title || finding.title,
      whyItMatters:
        recommendation?.body ||
        finding.description ||
        "This issue is large enough to meaningfully affect efficiency if it stays unresolved.",
      impactValue: finding.estimated_waste + finding.estimated_uplift,
      severity: finding.severity,
      entityName: finding.entity_name || finding.affected_entity,
      category: finding.category,
      metricValue: finding.metric_value,
      thresholdValue: finding.threshold_value,
    };
  });
}

export function deriveBiggestLeak(report: AuditReport): DerivedBiggestLeak | null {
  if (!report.findings.length) return null;
  const finding = [...report.findings].sort((a, b) => (b.estimated_waste + b.estimated_uplift) - (a.estimated_waste + a.estimated_uplift))[0];
  return {
    id: finding.id,
    title: finding.title,
    description: finding.description,
    waste: finding.estimated_waste,
    uplift: finding.estimated_uplift,
    entityName: finding.entity_name || finding.affected_entity,
    severity: finding.severity,
    category: finding.category,
    metricValue: finding.metric_value,
    thresholdValue: finding.threshold_value,
  };
}
