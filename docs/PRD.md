# spreadsheet-rescue — Product Requirements Document

> Internal living doc. README is client-facing.

## Vision

A CLI-first Python tool that turns messy CSV/XLSX exports into polished Excel KPI reports — with QC reports and run manifests for trust and repeatability. Designed for freelancers, analysts, and SMEs who waste hours cleaning spreadsheets every week.

## Principles

1. **Local-first** — no data leaves the machine
2. **Repeatable** — same input → same output, every time
3. **Auditable** — QC report + run manifest on every run
4. **Client-ready** — output is handoff-ready without manual formatting
5. **CLI-first** — scriptable, composable, automatable

## Architecture

```
src/spreadsheet_rescue/
  __init__.py      # version + REQUIRED_COLUMNS
  models.py        # QCReport, RunManifest dataclasses
  io.py            # load CSV/XLSX (dtype=str), write JSON
  pipeline.py      # clean_dataframe, compute_* functions
  report.py        # write Final_Report.xlsx (openpyxl)
  qc.py            # write qc_report.json
  utils.py         # sha256_file, utcnow_iso
  cli.py           # typer app: run + validate commands
  __main__.py      # python -m support
```

## Required Columns (v0.1.1)

`date`, `product`, `region`, `revenue`, `cost`, `units`

Remappable via `--map target=source`.

## Output Contract

Every successful run produces:

```
<out_dir>/
  Final_Report.xlsx    # Dashboard + Weekly + Top Products + Top Regions + Clean_Data
  qc_report.json       # rows in/out, dropped count, warnings
  run_manifest.json    # tool version, input SHA-256, timestamps
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| 2    | Validation/input failure (missing/duplicate columns, unreadable input) |

## Pipeline Steps

1. Load table as `dtype=str` (safe coercion)
2. Normalize headers (lowercase, strip, collapse spaces to `_`)
3. Apply column map if `--map` provided
4. Check required columns → hard fail if missing
5. Coerce types: dates (`--dayfirst/--monthfirst`), numerics (`--number-locale`)
6. Drop rows with invalid/missing required fields
7. Add derived fields: `profit = revenue - cost`, `week`
8. Sort by date
9. Compute KPIs: total revenue, total cost, total profit, margin %, row count
10. Compute weekly aggregation, top products, top regions
11. Write Excel report with professional formatting
12. Write QC report + run manifest

## Excel Report Formatting (v0.1.1)

- Number formats: `#,##0.00` (currency), `#,##0` (integers), `0.00"%"` (percent labels)
- Freeze panes on all sheets (row 2)
- Auto-fit column widths
- Clean_Data as Excel Table (TableStyleMedium9)
- Dashboard: QC Notes block (yellow fill) + KPI cards (blue fill)
- Formula-like text values are escaped before writing to Excel cells

## Roadmap

### v0.2

- Multi-file batch processing (`--input-dir`)
- Rules YAML profiles (reusable cleaning configs)
- PDF executive summary export
- Stronger QC: outlier detection, duplicate rate, negative total warnings

### v0.3

- Template library (sales, invoices, leads, inventory)
- "Handover pack" generator (README + usage + maintenance docs)
- Optional Streamlit upload UI (local-first)

## Tech Stack

- Python 3.10+
- pandas ≥ 2.0 (tested on 3.0)
- openpyxl ≥ 3.1
- typer ≥ 0.9 + rich ≥ 13.0
- Dev: ruff, mypy, pytest

## Known pandas 3.0 Gotchas

- `infer_datetime_format` removed → use `format="mixed"`
- `StringDtype` ≠ `"object"` → use `pd.api.types.is_numeric_dtype()`
- `PeriodDtype` → use `.dt.start_time` not `.apply(lambda)`
