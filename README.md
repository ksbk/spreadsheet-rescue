# spreadsheet-rescue

**Fix messy CSV/XLSX -> clean Excel report + audit trail.**

[![CI](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml/badge.svg)](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml)

## 15-second comprehension

- Handles mixed locale numerics (`1.200,50`, `1,234.56`) with explicit warnings.
- Flags ambiguous dates (`01/02/2024`) with deterministic parsing behavior.
- Hard-fails on duplicate/conflicting normalized headers to prevent silent KPI corruption.

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

## Quick Try (One-Link Trial)

```bash
pipx install spreadsheet-rescue
make customer-pack
open demo/output/Final_Report.xlsx
```

Notes:
- `make customer-pack` generates `dist/customer-demo-pack.zip` for email-ready buyer evaluation.
- The zip includes `dist/RUN_DEMO.command` (macOS) and `dist/run_demo.bat` (Windows) for one-click proof review.
- `open` is macOS; on Linux/Windows open the workbook manually from `demo/output/`.

Maintainer preflight:
- `make preflight` runs lint/type/tests + smoke/demo/customer-pack + strict docs build without bumping/tagging.

## 90-second walkthrough

1. Run `./scripts/demo.sh`.
2. Open `demo/output/Final_Report.xlsx` and inspect `Dashboard`, `Clean_Data`, and `Weekly`.
3. Review `demo/output/qc.json` for parsing/dropped-row warnings.
4. Review `demo/output/manifest.json` for run status and reproducibility metadata.
5. Use `demo/dashboard.png`, `demo/clean_data.png`, and `demo/weekly.png` as quick-share proof assets.

## See demo outputs

![Dashboard proof](demo/dashboard.png)

![Clean Data proof](demo/clean_data.png)

![Weekly proof](demo/weekly.png)

## Trust Guarantees

- Always emits QC + manifest artifacts even on contracted failures.
- Formula-injection safe Excel output for formula-like input strings.
- Deterministic proof image renderers for dashboard and table previews.

See:
- `docs/TRUST.md`
- `docs/USE_CASES.md`
- `docs/landing/index.md`

## Not For

- Large enterprise ETL/orchestration platforms.
- Deep custom finance rule engines (tax/FX/policy stacks).
- Hosted BI/analytics products.

## Core CLI

- `srescue run`: clean + report generation.
- `srescue validate`: preflight checks + artifact emission without report generation.

Both commands accept CSV/XLSX/XLS and support `--map target=source` for header mapping.
