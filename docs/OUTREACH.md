# Customer Outreach Pack

## 90-second demo narrative

1. "You send me a messy CSV/XLSX export."
2. "I run one command and produce a clean Excel report plus QC + manifest."
3. "You review three proof assets: dashboard, clean row-level table, weekly summary."
4. "You get a deliverable pack you can trust and rerun."
5. "If useful, send me one file and deadline; I will return your cleaned report in 24-48h."

## Outreach templates

### Email template

Subject: I can clean your spreadsheet export and return a trusted report

Hi {{Name}},

If you are spending time fixing CSV/XLSX exports before reporting, I can help. I turn messy files into a clean `Final_Report.xlsx` and always include `qc.json` + `manifest.json` so you can trust what changed.

If you send one sample file, I can return a cleaned deliverable pack in 24-48h.

Best,
{{Your Name}}

### LinkedIn DM template

Hi {{Name}} - I help teams turn messy CSV/XLSX exports into clean Excel reports with an audit trail (`qc.json` + `manifest.json`). If you send one sample file, I can return a cleaned report pack in 24-48h.

### Upwork proposal template

I can clean your CSV/XLSX export and return a reliable report pack:
- `Final_Report.xlsx`
- `qc.json` (warnings, rows in/out)
- `manifest.json` (status + reproducibility metadata)

I specifically handle EU decimals, ambiguous dates, and duplicate headers with deterministic rules and explicit warnings. Share one sample file and your deadline, and I will return a first delivery in 24-48h.

## Objection handling and trust points

- "Our data has EU decimals and mixed locales."
  - Locale collisions are detected and warned; values are normalized deterministically.
- "Our dates are inconsistent."
  - Ambiguous dates are flagged and parsed with explicit, repeatable rules.
- "How do we trust output quality?"
  - Every run emits QC + manifest artifacts, including failure paths, so auditability is preserved.
