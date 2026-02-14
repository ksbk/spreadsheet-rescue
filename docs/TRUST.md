# TRUST

This document defines the reliability contract for `spreadsheet-rescue`.

## Artifact Contract

`run` success must produce:
- `Final_Report.xlsx`
- `qc_report.json` (CLI canonical)
- `run_manifest.json` (CLI canonical)

`validate` success must produce:
- `qc_report.json`
- `run_manifest.json`

Demo aliases (`./scripts/demo.sh`):
- `demo/output/qc.json` is copied from `qc_report.json`
- `demo/output/manifest.json` is copied from `run_manifest.json`

## Exit Codes

- `0`: success
- `2`: input/contract violation (missing columns, duplicate normalized/mapped columns, unreadable input)
- `1`: unexpected/internal failure

## Failure Behavior

After startup, both expected and unexpected failures are required to emit QC + manifest artifacts. This preserves diagnosability and auditability.

## Warning Semantics

Warnings are explicit, not silent. Typical warning categories:
- ambiguous date interpretation (`MM/DD` vs `DD/MM`)
- ambiguous numeric separators (`1,234`)
- EU decimal comma detection counters
- dropped rows from unparseable required fields

Warnings are informational unless tied to a hard contract violation (for example, missing required columns).

## Formula Injection Safety

String values beginning with `=`, `+`, `-`, or `@` are escaped before writing to Excel cells. Untrusted inputs are rendered as literal text, not formulas.

## Deterministic Preview Rendering

`demo/dashboard.png` is rendered from workbook values via `scripts/render_dashboard_preview.py`.

Determinism guarantees:
- fixed canvas dimensions
- bundled font files under `assets/fonts/`
- no OS screenshot dependencies

This keeps previews stable across local runs and CI.
