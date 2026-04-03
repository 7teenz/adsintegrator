---
created: 2026-04-03T18:15:10.000Z
title: Replace generic recommendation paragraph with structured AI hint bullets
area: ui
files:
  - frontend/src/components/dashboard/findings-list.tsx
---

## Problem

Each finding currently shows a generic "Recommended action" paragraph. It's a wall of text — not actionable. Users don't know what to do first.

## Solution

When a finding is expanded, show 3–5 concrete action step bullets sourced from the **already-generated AI summary run** (no new API call needed). The AI summary already exists in the DB — parse/extract the per-finding hints from it.

This is a display change: instead of a prose paragraph, render a bullet list of steps. Coordinate with the expandable findings todo.
