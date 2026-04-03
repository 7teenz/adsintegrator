---
created: 2026-04-03T18:15:10.000Z
title: Make findings list expandable/collapsible
area: ui
files:
  - frontend/src/components/dashboard/findings-list.tsx
---

## Problem

Findings are currently shown as flat cards with no expand/collapse. All content is always visible, making the page overwhelming with many findings. Users can't quickly scan and dive into what matters.

## Solution

Implement accordion-style findings list:
- **Collapsed state**: severity badge + title + metric pill (Actual vs Threshold)
- **Expanded state**: full description + AI hint bullet list (3–5 action steps) + "Need help? Book a call" link

Component: `frontend/src/components/dashboard/findings-list.tsx` (create if doesn't exist yet — currently findings may be rendered inline in the page).
