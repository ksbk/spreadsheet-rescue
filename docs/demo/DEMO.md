# Demo Script (2 minutes)

## 1) Before: messy input

`examples/input/sample_messy_sales.csv` contains realistic issues:

```csv
date,product,region,revenue,cost,units
01/02/2024,Widget A,North,"1.200,50","200,25","2,0"
2024-01-03,Gadget B,South,"1,234.56",700.10,3
not-a-date,Widget C,West,100,80,1
2024-01-05,"=HYPERLINK(""https://example.com"",""Click"")",East,450,200,2
```

## 2) One command

```bash
./scripts/demo.sh
```

This writes:

* `output/demo_run/Final_Report.xlsx`
* `output/demo_run/qc_report.json`
* `output/demo_run/run_manifest.json`

## 3) After: what to show in a live demo

Screenshot checklist:
* `Dashboard` sheet: rows in/out, warnings, KPI cards
* `Clean_Data` sheet: cleaned typed values and escaped formula-like text
* `Weekly` sheet: week-level totals
* `Top_Products` sheet: ranked product revenue/profit
* `Top_Regions` sheet: ranked region revenue/profit

Narration points:
* Mixed locale numbers are parsed deterministically.
* Ambiguous date/numeric values are warned, not hidden.
* Output includes audit artifacts (`qc_report.json`, `run_manifest.json`) every run.
