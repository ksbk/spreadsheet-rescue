# 📊 spreadsheet-rescue — Clean Messy Spreadsheets into Client-Ready Reports

**Turn dirty CSV/XLSX exports into a polished Excel KPI report in one command — with QC + run manifests for trust and repeatability.**

> **Local-first. No data leaves your machine.**
> Built for freelancers, analysts, and SMEs who waste hours cleaning spreadsheets every week.

---

## Contents

- [📊 spreadsheet-rescue — Clean Messy Spreadsheets into Client-Ready Reports](#-spreadsheet-rescue--clean-messy-spreadsheets-into-client-ready-reports)
  - [Contents](#contents)
  - [The Problem](#the-problem)
  - [The Solution](#the-solution)
  - [What You Get](#what-you-get)
  - [Quick Start](#quick-start)
    - [Install (editable)](#install-editable)
    - [Run the example](#run-the-example)
  - [How It Works](#how-it-works)
  - [Output Contract](#output-contract)
  - [QC \& Reliability](#qc--reliability)
    - [v0.1 QC rules](#v01-qc-rules)
    - [Exit codes](#exit-codes)
  - [Configuration](#configuration)
    - [v0.1 (opinionated)](#v01-opinionated)
    - [v0.2 (planned)](#v02-planned)
  - [Roadmap](#roadmap)
    - [v0.1 — MVP (now)](#v01--mvp-now)
    - [v0.2 — High-leverage upgrades](#v02--high-leverage-upgrades)
    - [v0.3 — "Client-ready packs"](#v03--client-ready-packs)
  - [Services](#services)
  - [Changelog](#changelog)
    - [2026-02-13 — v0.1.0](#2026-02-13--v010)
  - [Hire / Contact](#hire--contact)

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

1. **Loads** a CSV/XLSX export
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
git clone https://github.com/kusseba/spreadsheet-rescue.git
cd spreadsheet-rescue
pip install -e .
```

### Run the example

```bash
srescue run -i examples/raw_sales.csv --out-dir output/demo_run
```

You'll find:

* `output/demo_run/Final_Report.xlsx`
* `output/demo_run/qc_report.json`
* `output/demo_run/run_manifest.json`

---

## How It Works

**Tech stack:** Python • pandas • openpyxl • typer • rich

Pipeline (v0.1):

```
Load table (CSV/XLSX)
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

---

## QC & Reliability

### v0.1 QC rules

* Missing required columns → **hard fail** (exit code `2`) but still write `qc_report.json`
* Invalid dates/numbers → dropped rows + warnings (recorded in QC report)
* Empty cleaned dataset → warning (report still emitted if possible)

### Exit codes

* `0` success
* `2` schema failure (missing required columns / unusable input)

---

## Configuration

### v0.1 (opinionated)

The example profile expects these columns:

* `date, product, region, revenue, cost, units`

Derived fields:

* `profit = revenue - cost`
* `week = start date of week`

### v0.2 (planned)

* Column mapping (e.g. `--map revenue=Sales amount=Total`)
* Batch mode for folders (`--input-dir`)
* Rules YAML for reuse (filters, dedupe, categories)

---

## Roadmap

### v0.1 — MVP (now)

* [x] CLI `srescue run`
* [x] CSV/XLSX input
* [x] Cleaning + derived fields
* [x] Excel report output
* [x] QC report + run manifest
* [ ] Minimal styling polish (column formats, freeze header row)
* [ ] Add 2–3 more example datasets

### v0.2 — High-leverage upgrades

* [ ] Multi-file batch processing (`--input-dir`)
* [ ] Column mapping (flags + YAML)
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

**Deliverables always include:**

* before/after notes
* QC report (what was dropped and why)
* repeatable workflow (no "magic manual steps")

> Contact: **kusseba@gmail.com** • Upwork: **<!-- your-upwork-link -->** • LinkedIn: **<!-- your-linkedin -->**

---

## Changelog

### 2026-02-13 — v0.1.0

* Initial release: CLI run + report workbook + QC + manifest

---

## Hire / Contact

I'm **Kusse Sukuta Bersha (KSB)** — Python developer specializing in **data automation, reproducible pipelines, and AI-enabled tooling**.

* Email: kusseba@gmail.com
* Upwork: <!-- your-upwork-link -->
* LinkedIn: <!-- your-linkedin-link -->

If you have "that spreadsheet," I can make it clean, repeatable, and report-ready.
