---
created: 2026-04-03T18:15:10.000Z
title: Add dual CTA path in audit report (fix-yourself vs book-a-call)
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Users land on the audit report with no clear next action and no conversion path.

## Solution

Full-width banner placed after the verdict line, before the findings list.

**Left button — "Fix it yourself"**:
- On click: expand all findings in the findings list (set all to open state)
- Label: "Fix it yourself" with a chevron-down icon

**Right button — "Book a strategy call"**:
- `href="https://calendly.com/tilabov17"` target `_blank`
- Label: "Book a strategy call" with a calendar icon
- Style: brand blue `#2563eb` background, white text (primary CTA)

Both buttons equal width, side by side. On mobile: stack vertically with "Book a call" on top.

**Coordinate with**: expandable findings todo — the "Fix it yourself" button needs access to the expand-all trigger.
