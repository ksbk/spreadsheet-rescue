# spreadsheet-rescue One Pager

## Problem

Messy spreadsheet exports cause wrong KPIs and repeated manual cleanup:
* mixed date formats
* locale-formatted numbers stored as text
* inconsistent headers and categories
* hours lost every week in copy/paste cleanup

## Outcome

In minutes, you get:
* a cleaned dataset
* a polished Excel dashboard/report pack
* QC + manifest artifacts for trust and repeatability

## Deliverables

Every run delivers:
* `Final_Report.xlsx` (Dashboard, Weekly, Top tables, Clean_Data)
* `qc_report.json` (warnings, rows dropped, missing/duplicate schema issues)
* `run_manifest.json` (version, input hash, timestamp, row counts)

## Trust and risk controls

* Deterministic parsing for dates and numerics
* Explicit warnings for ambiguous values (no silent guessing)
* Safe Excel export (formula-like strings escaped)
* Contracted failure behavior with exit codes and QC artifacts

## Pricing tiers (example)

### 1) One-off cleanup
* Best for ad-hoc deliverables or urgent reporting fixes
* Deliverable: cleaned workbook + QC artifacts + brief handoff notes

### 2) Monthly spreadsheet hygiene
* Best for recurring weekly/monthly exports
* Deliverable: repeat runbook, mapping profile, monthly maintenance pass

### 3) Team/internal tool license
* Best for teams that want in-house repeatable runs
* Deliverable: packaged CLI workflow, onboarding session, support option

## Ideal buyers

Finance, admin, and operations teams in small businesses, ecommerce shops, clinics, and NGOs that rely on Excel-heavy workflows.
