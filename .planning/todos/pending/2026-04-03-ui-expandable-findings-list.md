---
created: 2026-04-03T18:15:10.000Z
title: Make findings list expandable/collapsible
area: ui
priority: 1
files:
  - frontend/src/components/dashboard/findings-list.tsx
---

## Problem

Findings are currently always-expanded flat cards. With many findings the page becomes overwhelming. Users can't quickly scan for what matters then drill in.

## Solution

**Priority: implement this FIRST before layout rebuild or tab restructure.**

Accordion-style findings list in `findings-list.tsx`:

- **Collapsed state** (default): severity badge + category chip + title + metric pill (Actual vs Threshold)
- **Expanded state**: full description + AI hint bullets (from todo: replace-recommendation-paragraph) + "Need help? Book a call" link → `https://calendly.com/tilabov17`

Use React `useState` per-card (or a single `expandedId` state). No animation library needed — a simple `hidden`/`block` toggle is fine.

**Coordinate with:** `2026-04-03-ui-ai-hint-bullets-per-finding.md` — the expanded state should render AI hint bullets, not the current `recommendation.body` paragraph.
