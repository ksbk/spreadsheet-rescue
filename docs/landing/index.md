# Fix messy CSV/XLSX -> clean Excel report + audit trail

`spreadsheet-rescue` turns messy spreadsheet exports into a client-ready Excel report with QC and manifest artifacts.

## Common pain it solves

- EU/US numeric collisions in one file (`1.200,50`, `1,234.56`).
- Ambiguous dates (`01/02/2024`) that silently break KPIs in manual workflows.
- Duplicate/conflicting headers after normalization or mapping.

## One-command quickstart

```bash
./scripts/demo.sh
```

Outputs:
- `demo/output/Final_Report.xlsx`
- `demo/output/qc.json`
- `demo/output/manifest.json`
- `demo/dashboard.png`

## Trust Guarantees

- Always emits QC + manifest artifacts, including contracted failures.
- Formula-injection safe Excel output (formula-like inputs are escaped).
- Deterministic demo proof renders (`dashboard`, `clean_data`, `weekly`) from workbook data.

## Not For

- Large enterprise ETL platforms and distributed data orchestration.
- Fully custom finance rule engines (tax/FX/accounting policy stacks).

## Learn more

- Trust contract: `docs/TRUST.md`
- Use cases: `docs/USE_CASES.md`
- Demo walkthrough: `docs/demo/DEMO.md`
