---
created: 2026-04-03T18:15:10.000Z
title: Rebuild Audit Report page layout
area: ui
priority: 3
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Current audit report page has structural problems:
- "Top 3 Actions" appears 3× on the page (duplication)
- "Biggest Leak" sidebar card competes with findings list
- No clear hero section or single verdict line
- No CTA path for converting users to booked calls

## Solution

**Priority: implement AFTER expandable findings + AI hint bullets are done.**

Redesign `page.tsx` layout:

1. **Hero section**: health score gauge + 3 KPI pills (spend, waste, uplift) + "Run Audit" button + "Export PDF" button
2. **Verdict line**: 1 auto-generated sentence from `ai_summary.short_executive_summary` (first sentence)
3. **Dual CTA banner**: "Fix it yourself" (expands all findings inline) / "Book a strategy call" → `https://calendly.com/tilabov17`
4. **Single expandable findings list** (from expandable findings todo) — this replaces: Top 3 Actions, Biggest Leak card, Supporting Evidence
5. **Remove**: "Biggest Leak" sidebar card
6. **Remove**: duplicate "Top 3 Actions" sections (currently rendered 3×)

Keep: tabs (Overview, Campaigns, Trend, History) — tab restructure is a separate todo.
