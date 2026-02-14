# USE CASES

Six concrete scenarios where `spreadsheet-rescue` is useful.

## 1) Weekly Sales Export Cleanup

Input: messy CSV from ecommerce admin panel.

User gets:
- cleaned row-level dataset
- KPI dashboard workbook
- QC warnings explaining dropped rows and parse decisions

## 2) Mixed-Locale Finance Sheet

Input: one file with both `1.200,50` and `1,234.56`.

User gets:
- deterministic numeric coercion
- warning counters for EU decimal-comma detections
- report totals that are reproducible across reruns

## 3) Recurring Client Reporting

Input: same weekly export schema with occasional header drift.

User gets:
- stable `--map` based normalization
- immediate failure on duplicate mapped targets
- a repeatable, low-touch reporting workflow

## 4) Preflight QA Before Delivery

Input: spreadsheet from a teammate before client handoff.

User gets:
- `validate` mode to check schema/typing without generating report
- QC artifact for review comments
- manifest artifact for run traceability

## 5) Security-Conscious Spreadsheet Handling

Input: external file containing formula-like text payloads.

User gets:
- escaped Excel output to prevent formula execution
- preserved text visibility for manual review
- safer workbook sharing downstream

## 6) Demo-Ready Product Proof

Input: bundled `demo/input/messy_sales.csv`.

User gets:
- one-command demo output in `demo/output/`
- committed artifacts for instant repository browsing
- deterministic `demo/dashboard.png` for docs and social proof
