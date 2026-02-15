# Fix messy CSV/XLSX -> clean Excel report + audit trail

[FORM_URL]: https://forms.gle/REPLACE_WITH_YOUR_FORM_ID

Fix messy CSV/XLSX -> clean Excel report + QC + manifest.

[Download customer demo pack](https://github.com/ksbk/spreadsheet-rescue/releases/download/v0.1.5/customer-demo-pack.zip) | [Send me your file][FORM_URL] | [See sample output](demo/DEMO.md)

## Intake requirements

- Upload your CSV/XLSX file.
- Tell us date style: `day-first`, `month-first`, or `unknown`.
- Provide currency/locale (`EUR`, `USD`, decimal style).
- List desired output columns if you have specific requirements.

## What you receive

- `Final_Report.xlsx`
- `qc.json`
- `manifest.json`
- `dashboard.png`
- `clean_data.png`
- `weekly.png`

## Proof

![Dashboard proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/dashboard.png)

![Clean_Data proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/clean_data.png)

![Weekly proof](https://raw.githubusercontent.com/ksbk/spreadsheet-rescue/main/demo/weekly.png)

## Trust

- No silent EU number corruption: locale collisions are flagged with deterministic behavior.
- Ambiguous dates are flagged before they can silently corrupt metrics.
- QC + manifest artifacts are always emitted, including contracted failures.

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
- `demo/clean_data.png`
- `demo/weekly.png`

## Learn more

- [Services](SERVICES.md)
- [Outreach pack](OUTREACH.md)
- [Delivery checklist](DELIVERY_CHECKLIST.md)
- [Trust contract](TRUST.md)
- [Use cases](USE_CASES.md)
- [Onboarding](ONBOARDING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Demo walkthrough](demo/DEMO.md)
