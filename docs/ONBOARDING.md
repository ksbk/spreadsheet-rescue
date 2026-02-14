# Onboarding

This guide helps non-technical buyers run a first evaluation in under 60 seconds.

## Flow 1: I have messy CSV (default)

1. Place your file anywhere locally (for example `data/my_export.csv`).
2. Run:

```bash
srescue run -i data/my_export.csv -o output
```

3. Open outputs:
- `output/Final_Report.xlsx`
- `output/qc_report.json`
- `output/run_manifest.json`

Use `qc_report.json` to review warnings and dropped-row reasons before sharing the report.

## Flow 2: I have messy Excel

Supports `.xlsx`, `.xlsm`, `.xltx`, `.xltm`, and `.xls`.

```bash
srescue run -i data/my_export.xlsx -o output
```

For quick preflight without creating the report:

```bash
srescue validate -i data/my_export.xlsx -o output
```

`validate` still writes QC + manifest artifacts so you can inspect schema/typing issues.

## Flow 3: I need column mapping

If your headers do not match required fields (`date`, `product`, `region`, `revenue`, `cost`, `units`), use `--map target=source`.

Example:

```bash
srescue run -i data/client.csv -o output \
  --map date="Order Date" \
  --map product="Product Name" \
  --map region="Sales Region" \
  --map revenue="Gross Revenue" \
  --map cost="Cost (€)" \
  --map units="Units Sold"
```

### Mapping failure examples

Invalid format (missing `=`):

```bash
srescue run -i data.csv -o output --map revenue
```

Result: validation-style failure (`exit 2`) and QC/manifest artifacts explaining the issue.

Duplicate mapped targets (two sources to same target):

```bash
srescue run -i data.csv -o output \
  --map revenue=Revenue \
  --map revenue="Gross Revenue"
```

Result: hard failure (`exit 2`) because duplicate target columns can corrupt KPIs.

## Fast buyer demo

```bash
./scripts/demo.sh
```

Artifacts for review:
- `demo/output/Final_Report.xlsx`
- `demo/output/qc.json`
- `demo/output/manifest.json`
- `demo/dashboard.png`
- `demo/clean_data.png`
- `demo/weekly.png`
