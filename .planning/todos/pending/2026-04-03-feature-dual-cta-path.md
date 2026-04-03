---
created: 2026-04-03T18:15:10.000Z
title: Add dual CTA path in audit report (fix-yourself vs book-a-call)
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Users land on the audit report with no clear next action. There's no conversion path — no way to differentiate between DIY users and users who want professional help.

## Solution

After the verdict line, before the findings list, show a prominent dual CTA banner:
- **"Fix it yourself"** → expands AI hints inline per finding (triggers expand-all on findings list)
- **"Book a strategy call"** → opens Calendly link (placeholder: `YOUR_CALENDLY_URL` until set)

This is the main monetization entry point. Keep it visually prominent — full-width banner, two equal-weight buttons.
