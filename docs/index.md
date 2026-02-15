# Fix messy CSV/XLSX -> clean Excel report + audit trail

[FORM_URL]: https://forms.gle/REPLACE_WITH_YOUR_FORM_ID
[DEMO_PACK_URL]: https://github.com/ksbk/spreadsheet-rescue/releases/latest/download/customer-demo-pack.zip
[RELEASES_URL]: https://github.com/ksbk/spreadsheet-rescue/releases/latest

Fix messy CSV/XLSX -> clean Excel report + QC + manifest.

[Send me your file][FORM_URL] | [Download customer demo pack][DEMO_PACK_URL] | [See sample output](demo/DEMO.md)

Trust badges: **EU/US numeric safety** | **Ambiguous date warnings** | **Always emits QC+manifest** | **Formula-injection safe**

Starting at **EUR 150** for Quick Rescue. See [Services](SERVICES.md).
Need immediate delivery? [How to pay](SERVICES.md#how-to-pay) | [Sample delivery](SAMPLE_DELIVERY.md)

## How it works

1. Upload your messy CSV/XLSX and deadline in the intake form.
2. I clean and normalize the file with explicit QC warnings and manifest metadata.
3. You receive a report pack you can review, share, and rerun.

## Intake requirements

- Upload your CSV/XLSX file.
- Tell us date style: `day-first`, `month-first`, or `unknown`.
- Provide currency/locale (`EUR`, `USD`, decimal style).
- List desired output columns if you have specific requirements.

## What you receive

- `Final_Report.xlsx`
- `qc.json`
- `manifest.json`
- `summary.txt`
- `dashboard.png`
- `clean_data.png`
- `weekly.png`

Latest pack note: this link follows the latest GitHub release. You can also browse [Releases][RELEASES_URL].

## What you get in 60 minutes

- `Final_Report.xlsx`
- `qc.json`
- `manifest.json`
- `dashboard.png`

## Proof

![Dashboard proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/dashboard.png)

![Clean_Data proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/clean_data.png)

![Weekly proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/weekly.png)

## Designed to prevent silent corruption

- EU/US numeric collisions are detected and normalized with explicit warnings.
- Ambiguous day/month dates are flagged before they can silently skew KPIs.
- Formula-like strings are escaped in Excel output to prevent formula injection.

## Audit trail every run

- `manifest.json` records `status`, `error_code`, and row in/out counters.
- `qc.json` records warnings, dropped-row behavior, and schema issues.
- QC + manifest artifacts are emitted even on contracted failure paths.

## Deterministic demo outputs

- Dashboard/table preview PNGs are rendered from workbook data with deterministic scripts.
- Buyer-facing proof assets are reproducible across reruns.

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
- `demo/output/summary.txt`
- `demo/dashboard.png`
- `demo/clean_data.png`
- `demo/weekly.png`

## Learn more

- [Services](SERVICES.md)
- [Sample delivery](SAMPLE_DELIVERY.md)
- [Outreach pack](OUTREACH.md)
- [Delivery checklist](DELIVERY_CHECKLIST.md)
- [Trust contract](TRUST.md)
- [Use cases](USE_CASES.md)
- [Onboarding](ONBOARDING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Demo walkthrough](demo/DEMO.md)
