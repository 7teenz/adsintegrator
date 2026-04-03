---
created: 2026-04-03T18:15:10.000Z
title: Restructure audit report tabs — remove Structure and Tracking tabs
area: ui
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Current tabs: Overview, Campaigns, Trend, History, Structure, Tracking.
Structure and Tracking tabs fragment findings that belong in Overview. Users rarely navigate to them — they create confusion and dilute the main message.

## Solution

- **Keep**: Overview, Campaigns, Trend, History
- **Remove**: Structure tab — merge findings into Overview's expandable findings list
- **Remove**: Tracking tab — merge findings into Overview's expandable findings list

Ensure any findings with `category: structure` or `category: placement` still appear in the Overview findings list after removal.
