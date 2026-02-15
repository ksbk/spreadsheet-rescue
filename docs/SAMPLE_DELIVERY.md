# Sample Delivery

This is what a customer receives after a standard cleanup delivery.

## Dashboard preview

![Dashboard proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/dashboard.png)

## `qc.json` snippet

```json
{
  "rows_in": 7,
  "rows_out": 6,
  "dropped_rows": 1,
  "warnings": [
    "Found 2 ambiguous day/month dates; interpreted as month/day (MM/DD)",
    "Dropped 1 rows with invalid/missing values"
  ]
}
```

## `manifest.json` snippet

```json
{
  "status": "success",
  "error_code": null,
  "rows_in": 7,
  "rows_out": 6,
  "tool": "spreadsheet-rescue",
  "version": "0.1.5"
}
```

## What `Final_Report.xlsx` contains

- `Dashboard`: KPI summary and warning context.
- `Clean_Data`: normalized row-level data.
- `Weekly`: grouped weekly totals.
- `Top_Products` and `Top_Regions`: ranked performance slices.

## Delivery in 3 lines

- What I need from you: source file, column meaning, date style, and locale preference.
- What you get: `Final_Report.xlsx`, `qc.json`, `manifest.json`, `summary.txt`, and proof PNGs.
- When you get it: typical quick-rescue turnaround is 24-48h (faster lanes available by agreement).
