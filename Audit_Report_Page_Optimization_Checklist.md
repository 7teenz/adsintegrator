# Audit Report Page Optimization Checklist

Source: founder review and live product audit  
Scope: `frontend/src/app/dashboard/audits/page.tsx`, `frontend/src/components/dashboard/findings-list.tsx`, `frontend/src/components/dashboard/ai-summary-block.tsx`, supporting backend summary/recommendation logic

## Goal

Turn the audit report page into a clear executive-grade Meta Ads audit experience that:

- explains account health immediately
- surfaces the biggest performance leak first
- ranks the next actions clearly
- ties recommendations to evidence
- handles weak datasets without looking broken

## 1. Above-The-Fold Executive Layer

- [x] Keep the top section focused on four answers only:
  - health of the account
  - spend at risk
  - biggest leak
  - what to fix first
- [x] Replace any generic top copy with a one-line executive verdict.
- [x] Keep only these four KPI cards above the fold:
  - Account Health
  - Spend At Risk
  - Potential Lift
  - Confidence
- [x] Add a compact scope and confidence bar below the verdict.
- [x] Include in the scope bar:
  - date range
  - campaigns / ad sets / ads analyzed
  - spend analyzed
  - data mode
  - confidence label

## 2. Biggest Leak And Decision Layer

- [x] Add or refine a dedicated “Biggest Leak” card.
- [x] Show in that card:
  - finding title
  - affected entity
  - actual vs threshold
  - plain-language why-it-matters text
  - estimated waste if available
- [x] Add a “Top 3 Actions” section directly under the KPI row.
- [x] Rank each action explicitly as 1, 2, 3.
- [x] Add a “Why this matters” line under each action.
- [x] Ensure each action ties to a specific finding, not generic severity guidance.

## 3. Findings And Recommendations

- [ ] Make every recommendation body dynamic from the triggering finding.
- [ ] Use these finding fields when available:
  - `metric_value`
  - `threshold_value`
  - `entity_name`
  - finding title
- [ ] Render recommendations directly under the finding that triggered them.
- [ ] Do not leave recommendations as a disconnected side section only.
- [ ] Show “Actual vs Threshold” on every finding when a metric exists.
- [ ] Keep category-aware metric formatting:
  - performance / CTR as percent
  - budget / spend as currency
  - frequency as `x`

## 4. Information Architecture

- [x] Keep the report in three layers:
  - Layer 1: verdict and money impact
  - Layer 2: top actions and biggest leak
  - Layer 3: evidence, grouped findings, charts, and history
- [x] Keep detailed evidence below the fold.
- [x] Group findings by tab:
  - Overview
  - Campaigns
  - Structure
  - Tracking
  - Trend
  - History
- [x] Hide non-decision-critical detail by default.
- [x] Keep the history sparkline only as supporting context, not the main focus.

## 5. AI Summary Block

- [x] Keep AI framed as interpretation, not source of truth.
- [x] Structure the block in this order:
  - Executive verdict
  - Top 3 actions
  - Why performance is slipping
  - What is working well
  - Supporting evidence
- [x] Remove all visible internal metadata:
  - provider
  - model
  - status
- [ ] Make the first visible AI content action-led, not a paragraph wall.
- [ ] Improve the action plan so it is specific to the current finding set.
- [ ] If AI omits a strong action plan, synthesize one from deterministic findings instead of generic fallback bullets.

## 6. Data Quality And Weak Dataset Handling

- [x] Show a “Data limitations” card only when needed.
- [x] Trigger that card for:
  - aggregate-only exports
  - short analysis windows
  - low spend / sparse data
  - missing conversion detail
- [x] Keep zero-dollar findings visible.
- [x] When waste and uplift are `$0`, explain qualitative importance instead of implying the account is fine.
- [ ] Add stronger wording for:
  - aggregate-only exports
  - low-signal uploads
  - missing conversion depth
- [ ] Make confidence visibly lower when the dataset is thin.

## 7. Wording And UX Clarity

- [ ] Use business language instead of engine language throughout the page.
- [ ] Prefer section titles like:
  - What needs attention now
  - Top performance leak
  - Supporting evidence
  - Data confidence
  - What to change first
- [ ] Remove any remaining corrupted characters or mojibake.
- [ ] Remove duplicate or redundant sections.
- [ ] Remove empty filler states that do not help the user decide anything.

## 8. Pre-Upload And Empty States

- [ ] Add a stronger empty state when no audit exists yet.
- [ ] Explain clearly:
  - what to upload
  - what file shape works best
  - what the user gets after upload
- [ ] Add or refine a pre-upload checklist in the dashboard flow:
  - 30+ days
  - daily rows
  - spend
  - clicks
  - conversions
  - campaign and ad set fields

## 9. Export / Share Readiness

- [ ] Add a clean bottom section suitable for sharing or exporting.
- [ ] Include:
  - key findings
  - top actions
  - supporting evidence
  - AI interpretation
  - audit date

## 10. Validation Pass

- [ ] Validate the page on an aggregate-only export.
- [ ] Validate the page on a strong daily export.
- [ ] Validate the page on a low-spend account.
- [ ] Validate the page on a multi-campaign account.
- [ ] Validate the page on a broken conversion-funnel case.
- [ ] Do a final mobile and desktop polish pass for spacing, emphasis, and CTA clarity.

## Recommended Implementation Order

- [ ] Step 1: tighten the top section and KPI hierarchy.
- [ ] Step 2: improve biggest-leak and top-actions blocks.
- [ ] Step 3: connect findings to recommendations.
- [ ] Step 4: improve AI action-plan quality.
- [ ] Step 5: refine weak-dataset handling and confidence messaging.
- [ ] Step 6: polish wording, exportability, and visual hierarchy.
