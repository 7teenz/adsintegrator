---
created: 2026-04-03T18:15:10.000Z
title: Enhance AI summary with per-campaign performance context
area: backend
files:
  - backend/app/services/ai_summary.py
---

## Problem

`_build_structured_input()` only passes rule-triggered findings to the AI model. The AI summary has no awareness of which campaigns are best/worst performers — so the output is generic and misses naming the most impactful campaigns by name.

## Solution

In `ai_summary.py`, update `_build_structured_input()` to include:
- Top 3 worst performers ranked by ROAS, CTR, and CPA (with actual values)
- Top 3 best performers (same metrics)

This data is already available in the audit snapshot/findings — extract from the `CampaignAuditMetrics` list passed to the orchestrator. The AI summary will then reference specific campaigns by name, making it more actionable.
