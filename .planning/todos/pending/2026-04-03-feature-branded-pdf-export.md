---
created: 2026-04-03T18:15:10.000Z
title: Build real branded PDF export (replace window.print)
area: feature
files:
  - frontend/src/app/dashboard/audits/page.tsx
  - frontend/src/components/dashboard/audit-pdf-document.tsx
---

## Problem

Current PDF export uses `window.print()` — no branding, no layout control, unprofessional output.

## Solution

Use `@react-pdf/renderer` (pure React, no server dependency).

**New component**: `frontend/src/components/dashboard/audit-pdf-document.tsx`
- Renders a `<Document>` / `<Page>` PDF using @react-pdf/renderer
- **Header**: "Zafar Tilabov" in brand blue `#2563eb`, audit date, account name (text-only, no logo yet)
- **Sections**: health score, findings list (title + severity + metric pill per finding), prioritized action plan from AI summary
- **Brand colors**: blue `#2563eb`, slate backgrounds (`#f8fafc`)

**Wire up**: Replace the `window.print()` call in the "Export PDF" button with `pdf(<AuditPDFDocument ... />).toBlob()` → download via `URL.createObjectURL`.

**Install**: `npm install @react-pdf/renderer` in `frontend/`.
