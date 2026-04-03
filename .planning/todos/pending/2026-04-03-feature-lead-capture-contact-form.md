---
created: 2026-04-03T18:15:10.000Z
title: Add lead capture contact form at bottom of audit report
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
  - frontend/src/components/dashboard/lead-capture-form.tsx
  - backend/app/routes/audit.py
---

## Problem

No lead capture on the audit report. Users who want help have no path to contact — missed conversion opportunity.

## Solution

New component `frontend/src/components/dashboard/lead-capture-form.tsx`:
- Section heading: "Want us to fix this for you?"
- Fields: Name, Email, Message (textarea)
- Primary CTA button: "Book a Free Strategy Call" → links to `https://calendly.com/tilabov17`
- Secondary: form submission sends email via backend

**Backend**: add `POST /api/audit/contact` endpoint in `audit.py`:
- Accepts `{name, email, message}`
- Sends email via existing `backend/app/services/email.py` (SMTP already configured)
- No DB storage needed — just fire-and-forget email to the account owner

**Placement**: bottom of Overview tab in audit report, below findings list.
