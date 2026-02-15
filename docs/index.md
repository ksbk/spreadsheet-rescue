# Fix messy CSV/XLSX -> clean Excel report + audit trail

Fix messy CSV/XLSX -> clean Excel report + QC + manifest.

[Download customer demo pack](https://github.com/ksbk/spreadsheet-rescue/releases/download/v0.1.5/customer-demo-pack.zip) | [Send me your file](mailto:kbersha@gmail.com?subject=Spreadsheet%20Rescue%20Intake&body=Hi%2C%20I%20want%20a%20spreadsheet%20cleanup.%20Here%20is%20my%20file%20or%20Drive%20link%3A%0A%0ADeadline%3A%0A)

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
