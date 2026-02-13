# spreadsheet-rescue PRD (v0.1.1)

## Product promise

Convert messy spreadsheet exports into a deterministic, client-ready Excel report plus QC artifacts, without silent KPI corruption.

## Target users

Freelancers, finance/admin/ops users, and SMB analysts who receive recurring CSV/XLSX exports and need trustworthy weekly reporting.

## In-scope (v0.1.1)

* CLI commands: `srescue run`, `srescue validate`
* Input formats: `.csv`, `.xlsx`, `.xls`
* Output artifacts: `Final_Report.xlsx`, `qc_report.json`, `run_manifest.json`
* Deterministic cleaning for required fields and KPI summaries
* Safe Excel export (formula-like input escaped as text)

## Data contract

### Required columns

Normalized required headers:
* `date`
* `product`
* `region`
* `revenue`
* `cost`
* `units`

### Header normalization

Normalization rules are applied to input headers and mapping keys:
* `strip()` leading/trailing spaces
* lowercase
* collapse internal whitespace to `_`

Examples:
* `" Revenue "` -> `revenue`
* `"Order Date"` -> `order_date`

Duplicate normalized headers are a contract violation.

### Column mapping (`--map target=source`)

* Mapping is applied after source header normalization.
* If mapping produces duplicate required targets, fail with exit `2`.
* QC warning includes duplicate target and source provenance:
  `Mapping produced duplicate columns: revenue (source: revenue + Sales).`

## Parsing policy

### Date parsing

* Parsing uses mixed-format datetime coercion with `errors="coerce"`.
* Ambiguous day/month values (for example `01/02/2024`) are detected and warned.
* Parse mode:
  * default: `--monthfirst` (MM/DD)
  * optional: `--dayfirst` (DD/MM)
* Unparseable dates become null and affected rows are dropped.
* Week grouping: pandas weekly period (`W`) ending Sunday; stored `week` is period `start_time` (Monday).

### Numeric parsing

Supported parse modes:
* `--number-locale auto` (default)
* `--number-locale us`
* `--number-locale eu`

Deterministic conversions:
* `1.234,56` -> `1234.56`
* `1,234.56` -> `1234.56`
* `1234,56` -> `1234.56`

Ambiguity policy:
* Ambiguous tokens (for example `1,234`) are never silent:
  * QC warning emitted
  * deterministic fallback parse applies (thousands-separator interpretation)

QC counters:
* EU decimal comma detections are counted per numeric column (`revenue`, `cost`, `units`) and emitted as warnings.

Invalid numeric values:
* Coerced to null
* Row dropped if required field becomes null

## Derived fields and KPIs

* `profit = revenue - cost`
* `week = date.to_period("W").start_time`
* Dashboard KPIs include total revenue/profit, profit margin, total units, top product, top region.

Profit margin convention:
* Stored as percent-points (for example `25.53`)
* Excel format uses literal percent suffix: `0.00"%"` (no additional *100 scaling)

## Security requirements

Excel formula sanitization:
* Any string starting with `=`, `+`, `-`, or `@` is escaped before writing to workbook cells.
* Goal: untrusted input must render as literal text, not executable formulas.

## Output and failure contract

### Success (`srescue run`)

Must write:
* `Final_Report.xlsx`
* `qc_report.json`
* `run_manifest.json`

### Success (`srescue validate`)

Must write:
* `qc_report.json`
* `run_manifest.json`

### Failure behavior

For input/validation failures and unexpected internal failures after startup:
* always write `qc_report.json` and `run_manifest.json`
* never emit raw traceback to users for contracted failures

Exit codes:
* `0` success
* `2` input/contract violation (missing columns, duplicate columns, unreadable input, empty input)
* `1` unexpected/internal failure

## Non-goals (v0.1.1)

* Schema inference beyond required-column contract
* Business-specific rule engines (tax logic, FX conversions, account mappings)
* Fully automatic locale detection without user override
* Web UI / hosted processing
