---
created: 2026-04-03T18:15:10.000Z
title: Add lead capture contact form at bottom of audit report
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

No lead capture mechanism on the audit report. Users who want help have no path to contact — lost conversion opportunity.

## Solution

Add a "Want us to fix this?" section at the bottom of the Audit Report page:
- Fields: Name, Email, Message
- Primary CTA: Calendly booking link (placeholder: `YOUR_CALENDLY_URL`)
- Form submission: send email notification via existing SMTP config (`backend/app/services/email.py`)
- New component + wire into audit report page

Keep it simple — not a full CRM, just name/email/message + Calendly.
