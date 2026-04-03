---
created: 2026-04-03T18:15:10.000Z
title: Build real branded PDF export (replace window.print)
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
---

## Problem

Current PDF export uses `window.print()` — no branding, no layout control, looks unprofessional. Users get a raw browser print dialog that doesn't match the UI.

## Solution

Replace with a proper branded PDF:
- **Header**: "Zafar Tilabov" in brand blue `#2563eb`, audit date, account name (text-only — no logo yet)
- **Layout**: health score, findings list, recommendations — mirrors the UI report
- **Brand colors**: blue `#2563eb`, slate backgrounds
- **Tech**: likely a React-to-PDF library (e.g., `react-pdf`, `@react-pdf/renderer`) or server-side generation

New PDF component needed. Wire into the "Export PDF" button in the hero section.
