# Demo Script (2 minutes)

## 1) Input used by the demo

The demo reads:
- `demo/input/messy_sales.csv`

It includes realistic issues:
- ambiguous dates (`01/02/2024`, `02/01/2024`)
- mixed locale numerics (`1.200,50`, `1,234.56`)
- non-standard headers mapped via `--map`
- formula-like text values (escaped in Excel output)

## 2) Run one command

```bash
./scripts/demo.sh
```

## 3) Demo artifacts

- `demo/output/Final_Report.xlsx`
- `demo/output/qc.json`
- `demo/output/manifest.json`
- `demo/dashboard.png`

Manual PNG render (optional):

```bash
uv run --with pillow python scripts/render_dashboard_preview.py \
  --workbook demo/output/Final_Report.xlsx \
  --output demo/dashboard.png
```

## 4) What to show live

- `Dashboard`: rows in/out, dropped rows, warnings, KPI cards
- `Clean_Data`: cleaned values + formula-safe string output
- `Weekly`, `Top_Products`, `Top_Regions`: summarized reporting tables
