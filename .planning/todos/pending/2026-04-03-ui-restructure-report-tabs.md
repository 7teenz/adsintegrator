---
created: 2026-04-03T18:15:10.000Z
title: Restructure audit report tabs — remove Structure and Tracking tabs
area: ui
priority: 4
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Current tabs: Overview, Campaigns, Trend, History, Structure, Tracking.
Structure and Tracking fragment findings that belong in Overview. Users rarely navigate to them.

## Solution

**Priority: implement LAST after layout rebuild is done.**

- **Keep**: Overview, Campaigns, Trend, History
- **Remove**: Structure tab — findings with `category: structure` and `category: placement` move to Overview findings list
- **Remove**: Tracking tab — findings with `category: account` and conversion-related findings move to Overview findings list

No data is lost — just rendering location changes. The expandable findings list (already sorted by severity) handles all categories.
