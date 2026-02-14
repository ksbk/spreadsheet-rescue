# Troubleshooting

Use this guide to interpret warnings, exit codes, and debugging artifacts.

## Common warnings and what to do

### Ambiguous day/month dates
Warning example: `Found N ambiguous day/month dates; interpreted as month/day (MM/DD)`

What to do:
- Re-run with `--dayfirst` if your source uses `DD/MM`.
- Verify a few rows in `Clean_Data` to confirm parsed dates are correct.

### EU decimal commas detected
Warning example: `Detected EU decimal commas in revenue: N values`

What to do:
- If file is EU-formatted, run with `--number-locale eu`.
- If file is mixed, keep default `auto` and review totals in `Weekly`.

### Ambiguous numeric separators
Warning example: `Detected N ambiguous numeric values in revenue (example: 1,234)`

What to do:
- Standardize source values where possible.
- Re-run with explicit locale if your source system is consistent.

### Rows dropped for invalid required values
Warning example: `Dropped N rows with invalid/missing values`

What to do:
- Inspect input rows that failed parsing for required fields.
- Fix source values and rerun.

### Missing required columns
Warning example: `Missing required columns: ...`

What to do:
- Add `--map target=source` entries for renamed headers.
- Ensure normalized column names are unique.

## Exit codes

- `0`: Success
- `2`: Input/validation contract failure (missing/duplicate columns, invalid mapping, unreadable input)
- `1`: Unexpected/internal failure

## Debug with QC + manifest artifacts

`qc_report.json` (or demo alias `qc.json`) answers:
- How many rows came in/out?
- Which warnings were raised?
- Which required columns were missing?

`run_manifest.json` (or demo alias `manifest.json`) answers:
- Was run status `success` or `failed`?
- What was `error_code`?
- Which input file and output directory were used?
- What row counts were processed?

When sharing bugs, include both artifacts and the exact command used.
