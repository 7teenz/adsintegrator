---
created: 2026-04-03T18:15:10.000Z
title: Replace generic recommendation paragraph with structured AI hint bullets
area: ui
files:
  - frontend/src/components/dashboard/findings-list.tsx
  - backend/app/services/ai_summary.py
  - backend/app/models/audit.py
  - backend/app/schemas/audit.py
  - backend/app/routes/audit.py
---

## Problem

Each finding currently shows a generic "Recommended action" paragraph (`recommendation.body`). It's a wall of text — not actionable. Users don't know what to do first.

## Solution

**Approach:** Feed each finding's existing `recommendation_body` (rule-engine generated) into Gemini and ask it to reformat into 3-5 tight action bullets. No new knowledge generation — just restructuring of existing content.

**4 steps:**

1. **Backend — extend Gemini call**: add `finding_hints` as a 5th output key in the response schema.
   Input per finding: `title + recommendation_body` → output: `{rule_id: [bullet1, bullet2, bullet3]}`.
   No extra API call — part of existing audit-time Gemini request.

2. **Backend — new DB column**: `finding_hints_json TEXT` on `audit_ai_summaries` + alembic migration.

3. **Backend — expose via API**: add `finding_hints` to the audit response schema and route.

4. **Frontend**: in `findings-list.tsx`, look up `finding_hints[rule_id]` and render as `<ul>` bullets.
   Fallback to `recommendation.body` if hints not available.
