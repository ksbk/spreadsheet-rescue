# spreadsheet-rescue

**Fix messy CSV/XLSX -> clean report + audit trail.**

[![CI](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml/badge.svg)](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml)

`spreadsheet-rescue` turns recurring messy spreadsheet exports into a deterministic, client-ready Excel pack with QC artifacts.

What it handles well:
- EU/US numeric formats in the same file (`1.200,50`, `1,234.56`) with explicit warnings.
- Ambiguous dates (`01/02/2024`) with deterministic parse mode and warning output.
- Duplicate or conflicting headers after normalization/mapping with hard failure instead of silent corruption.

## Quickstart (One Command)

```bash
./scripts/demo.sh
```

Outputs:
- `demo/output/Final_Report.xlsx`
- `demo/output/qc.json`
- `demo/output/manifest.json`
- `demo/dashboard.png`

![Dashboard preview](demo/dashboard.png)

## What You Get

- `Final_Report.xlsx`: `Dashboard`, `Weekly`, `Top_Products`, `Top_Regions`, and `Clean_Data` sheets.
- `qc.json`: row-level quality summary and warnings.
- `manifest.json`: run status, error code, row counts, and reproducibility metadata.

## Trust Guarantees

- Always emits QC + manifest artifacts even on contracted failures.
- Formula-injection safe Excel output (formula-like text is escaped to literals).
- Deterministic demo PNG renderer for consistent visual previews (`scripts/render_dashboard_preview.py`).

See also:
- Trust contract: `docs/TRUST.md`
- Use-case pack: `docs/USE_CASES.md`
- Demo walkthrough: `docs/demo/DEMO.md`

## Not For

- Huge enterprise ETL workloads (distributed orchestration / petabyte pipelines).
- Deep business-rule engines (custom tax/FX/accounting logic per client).
- Interactive BI dashboards or hosted multi-tenant analytics platforms.

## Core CLI

- `srescue run`: clean + report generation.
- `srescue validate`: preflight checks + artifact emission without report generation.

Both commands accept CSV/XLSX/XLS and support `--map target=source` for header mapping.
