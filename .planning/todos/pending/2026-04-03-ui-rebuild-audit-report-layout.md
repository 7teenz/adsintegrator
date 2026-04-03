---
created: 2026-04-03T18:15:10.000Z
title: Rebuild Audit Report page layout
area: ui
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Current audit report page has structural problems:
- "Top 3 Actions" appears 3× on the page (duplication)
- "Biggest Leak" sidebar card competes with findings list
- No clear hero section or verdict line
- No CTA path for converting users to booked calls

## Solution

Redesign the page layout:
- Hero: health score gauge + 3 KPI pills + "Run Audit" button + "Export PDF" button
- Verdict line (1 sentence auto-generated from score) + dual CTA banner: "Fix it yourself" / "Book a strategy call"
- Expandable findings list (single source of truth — replaces current Top 3 + Biggest Leak + Supporting Evidence structure)
- Remove "Biggest Leak" sidebar card
- Remove duplicate "Top 3 Actions" sections
