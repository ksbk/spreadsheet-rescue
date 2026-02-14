# 📊 spreadsheet-rescue — Clean Messy Spreadsheets into Client-Ready Reports
[![CI](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml/badge.svg)](https://github.com/ksbk/spreadsheet-rescue/actions/workflows/ci.yml)

**Turn messy CSV/XLSX exports into a clean dataset and a client-ready Excel KPI pack in one command.**

You get:
* `Clean_Data` + deterministic type coercion (dates, numerics, text)
* `Weekly`, `Top_Products`, `Top_Regions`, and `Dashboard` sheets in `Final_Report.xlsx`
* `qc_report.json` + `run_manifest.json` for trust, replay, and audit trail

### 30-second quickstart

```bash
pip install -e .
./scripts/demo.sh
```

Output:

```
output/demo_run/
  Final_Report.xlsx
  qc_report.json
  run_manifest.json
demo/
  dashboard.png
```

![Dashboard](demo/dashboard.png)

### Watch 90-second demo

[Watch the product walkthrough (replace URL)](https://youtu.be/REPLACE_WITH_YOUR_DEMO_ID)

### What We Don't Do

* We do not guess silently on ambiguous date/numeric values; warnings are emitted.
* We do not infer missing business logic (tax rules, currency conversion, custom KPI formulas).
* We do not sanitize free-form spreadsheet models outside exported tabular input.

> **Local-first.** No data leaves your machine.

---

## Contents

* [The Problem](#the-problem)
* [The Solution](#the-solution)
* [What You Get](#what-you-get)
* [Quick Start](#quick-start)
* [How It Works](#how-it-works)
* [Output Contract](#output-contract)
* [QC & Reliability](#qc--reliability)
* [Configuration](#configuration)
* [Roadmap](#roadmap)
* [Services](#services)
* [Changelog](#changelog)
* [Hire / Contact](#hire--contact)

---

## The Problem

Every organization has "that spreadsheet":

* Dates in mixed formats
* Numbers stored as text (`$1,200`, `1.200,50`, `—`)
* Inconsistent headers and categories
* Duplicates, missing values, broken totals
* Weekly/monthly reporting that becomes **copy-paste labor**

This creates a real **time + error tax**. The work is repetitive, deadline-driven, and easy to mess up.

---

## The Solution

`spreadsheet-rescue` is a **CLI-first Python tool** that:

1. **Loads** a CSV/XLSX/XLS export
2. **Normalizes + cleans** core fields (dates, numerics, text)
3. **Computes KPIs** and summary tables (weekly totals, top categories)
4. **Writes** a professional Excel report
5. **Emits** a QC report + run manifest (audit trail)

**One command. Repeatable forever.**

---

## What You Get

After a successful run, you get a client-ready output bundle:

* ✅ `Final_Report.xlsx` (Dashboard + Weekly + Top tables + Clean_Data)
* ✅ `qc_report.json` (rows dropped, warnings, missing columns)
* ✅ `run_manifest.json` (tool version, input hash, timestamps)

This is designed to be easy to hand off to clients and easy to rerun on next week's data.

---

## Quick Start

### Install (editable)

```bash
git clone https://github.com/ksbk/spreadsheet-rescue.git
cd spreadsheet-rescue
pip install -e .
```

### Run the example

```bash
./scripts/demo.sh
```

You'll find:

* `output/demo_run/Final_Report.xlsx`
* `output/demo_run/qc_report.json`
* `output/demo_run/run_manifest.json`
* `demo/dashboard.png` (deterministic preview)
* walkthrough: `docs/demo/DEMO.md`

---

## How It Works

**Tech stack:** Python • pandas • openpyxl • typer • rich

Pipeline (v0.1.2):

```
Load table (CSV/XLSX/XLS)
  → Normalize headers
  → Type coercion (date + numerics)
  → Drop invalid rows (with warnings)
  → Add derived fields (profit, week)
  → Build summary tables + KPIs
  → Write Excel report
  → Emit qc_report + run_manifest
```

---

## Output Contract

Every successful run MUST produce:

```
<out_dir>/
  Final_Report.xlsx
  qc_report.json
  run_manifest.json
```

This contract is intentionally stable so you can build workflows (or a future web UI) on top without refactoring downstream usage.

### Failure contract

* Validation/input failures (`exit 2`) write `qc_report.json` + `run_manifest.json` and do not write `Final_Report.xlsx`.
* Unexpected/internal failures (`exit 1`) also write `qc_report.json` + `run_manifest.json`.
* QC warnings explain what to fix next (for example, missing columns, duplicate mappings, ambiguous date/numeric inputs).

---

## QC & Reliability

### v0.1.2 QC rules

* Missing required columns → **hard fail** (exit code `2`) but still write `qc_report.json`
* Duplicate columns after header normalization / `--map` → **hard fail** (exit code `2`)
* Invalid dates/numbers → dropped rows + warnings (recorded in QC report)
* Ambiguous dates like `01/02/2024` → warning with parse mode (`MM/DD` or `DD/MM`)
* EU decimal commas (for example `1.200,50`, `200,25`) are detected and counted per numeric column
* Ambiguous numeric tokens (for example `1,234`) emit warnings and use deterministic parsing rules
* Empty cleaned dataset → warning (report still emitted if possible)
* Formula-like text values in Excel output are escaped for safety

### Exit codes

* `0` success
* `2` validation/input failure (missing/duplicate columns, unreadable input)
* `1` unexpected/internal failure (still writes QC + manifest)

---

## Configuration

### v0.1.2 defaults

Required columns (case-insensitive):

* `date, product, region, revenue, cost, units`

Derived fields:

* `profit = revenue - cost`
* `week = start date of week`

### Column mapping (`--map`)

If your file uses different column names, remap them:

```bash
srescue run -i data.csv --out-dir output \
  --map revenue=Sales \
  --map date=OrderDate
```

Format: `--map target=source` (repeatable).

If mapping would create duplicate target columns, validation fails with exit `2`
and writes QC + manifest explaining the duplicate names.

### Date parse mode (`--dayfirst / --monthfirst`)

Control how ambiguous dates are interpreted:

```bash
srescue validate -i data.csv --out-dir output --dayfirst
```

Default is `--monthfirst` (`MM/DD`).

### Numeric parse mode (`--number-locale`)

Control numeric parsing behavior:

```bash
srescue run -i data.csv --out-dir output --number-locale eu
```

Supported values:
* `auto` (default) — heuristic parsing
* `us` — comma thousands, dot decimals (e.g., `1,200.50`)
* `eu` — dot thousands, comma decimals (e.g., `1.200,50`)

`auto` policy:
* `1.234,56` → `1234.56`
* `1,234.56` → `1234.56`
* `1234,56` → `1234.56`
* `1,234` is treated as ambiguous and reported in QC warnings; parsing stays deterministic.

### Validate-only mode

Preflight check — writes QC + manifest without producing the Excel report:

```bash
srescue validate -i data.csv --out-dir output
```

Exit `0` = OK, `2` = validation/input failure, `1` = unexpected/internal failure.

### Reproducible dev environment (uv)

This repo tracks `uv.lock` for reproducible lint/type/test environments:

```bash
uv sync --extra dev
uv run pytest -q
```

### v0.2 (planned)

* Batch mode for folders (`--input-dir`)
* Rules YAML for reuse (filters, dedupe, categories)

---

## Roadmap

### v0.1.2 — MVP (current)

* [x] CLI `srescue run`
* [x] CLI `srescue validate` (preflight)
* [x] CSV/XLSX input
* [x] Cleaning + derived fields
* [x] Professional Excel report (number formats, freeze panes, Excel Tables)
* [x] Dashboard with QC notes block
* [x] QC report + run manifest
* [x] `--map` column remapping
* [x] Exit-code contract (0 success, 2 schema failure)
* [x] Demo pack (`docs/demo/` + `examples/input/` + `scripts/demo.sh`)
* [x] Deterministic `demo/dashboard.png` preview renderer + checks
* [ ] Add 2–3 more example datasets

### v0.2 — High-leverage upgrades

* [ ] Multi-file batch processing (`--input-dir`)
* [ ] Rules YAML profiles
* [ ] PDF executive summary export
* [ ] Stronger QC checks (outliers, duplicate rate, negative totals)

### v0.3 — "Client-ready packs"

* [ ] Template library (sales, invoices, leads, inventory)
* [ ] "Handover pack" generator (README + usage + maintenance)
* [ ] Optional Streamlit upload UI (still local-first)

---

## Services

If you want this done for your specific spreadsheets, I offer:

| Tier              | What you get                                              | Typical turnaround |
| ----------------- | --------------------------------------------------------- | ------------------ |
| **Rescue**        | Clean + merge + deliver `Final_Report.xlsx`               | 24–48h             |
| **Automate**      | Rescue + reusable script profile (run it yourself weekly) | 2–4 days           |
| **Ops Reporting** | Automate + monthly support + custom KPIs                  | ongoing            |

**How it works:** Send me a sample export (you can redact sensitive data). I'll run `srescue validate` first and share the QC report before generating the final dashboard — so you see exactly what was cleaned and why before paying.

**Deliverables always include:**

* before/after notes
* QC report (what was dropped and why)
* repeatable workflow (no "magic manual steps")

> Contact: **kusseba@gmail.com** • Upwork: **<!-- your-upwork-link -->** • LinkedIn: **<!-- your-linkedin -->**

---

## Changelog

### 2026-02-14 — v0.1.2

* Added deterministic dashboard preview renderer: `scripts/render_dashboard_preview.py`
* `./scripts/demo.sh` now generates `demo/dashboard.png` after the run
* Added demo-asset guardrail tests in `tests/test_demo_assets.py`
* Added CI demo smoke check for `demo/dashboard.png`
* Updated package version to `0.1.2`

### 2026-02-13 — v0.1.1

* Added parse controls: `--dayfirst/--monthfirst` and `--number-locale auto|us|eu`
* Fixed numeric corruption risk for locale-formatted values like `1.200,50`
* Added duplicate-column protection after normalization/mapping (exit `2` + QC/manifest)
* Hardened load failures to return exit `2` and write QC/manifest consistently
* Escaped formula-like text when writing Excel report values
* Added CI-ready quality checks for `src/` + `tests/`
* Updated dependency metadata (`typer>=0.9`) and bumped version to `0.1.1`

### 2026-02-13 — v0.1.0

* `srescue run` — full cleaning + reporting pipeline
* `srescue validate` — preflight schema check
* `--map` flag for column remapping
* Professional Excel formatting (number formats, freeze panes, Excel Tables, Dashboard QC notes)
* QC report + run manifest with SHA-256 audit trail
* Exit-code contract: `0` success, `2` schema failure
* Demo pack introduced (now standardized as `docs/demo/` + `examples/input/` + `scripts/demo.sh`)
* 7 smoke tests passing

---

## Hire / Contact

I'm **Kusse Sukuta Bersha (KSB)** — Python developer specializing in **data automation, reproducible pipelines, and AI-enabled tooling**.

* Email: kusseba@gmail.com
* Upwork: <!-- your-upwork-link -->
* LinkedIn: <!-- your-linkedin-link -->

If you have "that spreadsheet," I can make it clean, repeatable, and report-ready.
