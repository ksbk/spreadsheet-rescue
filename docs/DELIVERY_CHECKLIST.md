# Delivery Checklist

## Intake questions

- Name and email
- File upload or Drive link
- What one row represents (sales transaction, inventory movement, etc.)
- Date format (`day-first`, `month-first`, or `unknown`)
- Currency and locale (`EUR`, `USD`, decimal style)
- Required column mapping (optional)
- Output deadline
- Whether invalid rows may be dropped (`yes/no`)
- Extra notes or business rules

## Acceptance criteria

- Required columns are present or mapped.
- `Final_Report.xlsx` opens and contains expected sheets.
- `qc.json` includes warnings, `rows_in`, and `rows_out`.
- `manifest.json` includes `status`, `error_code`, `rows_in`, and `rows_out`.
- Any dropped/ambiguous rows are explicitly documented in QC warnings.

## Turnaround and review

- Target turnaround: 24-48 hours for single-file jobs.
- Customer review steps:
  - confirm totals and date ranges on dashboard
  - inspect `Clean_Data` for row-level correctness
  - review `qc.json` warnings and dropped-row rationale
  - confirm `manifest.json` status and row counts
- Done means customer confirms the delivered artifacts meet required output scope.

## Service handoff bundle

- `Final_Report.xlsx`
- `qc.json`
- `manifest.json`
- `dashboard.png`
- `clean_data.png`
- `weekly.png`
