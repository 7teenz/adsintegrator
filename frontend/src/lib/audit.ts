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

export function formatCurrency(value: number): string {
  return "$" + value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
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
