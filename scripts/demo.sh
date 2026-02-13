#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_FILE="$ROOT_DIR/examples/input/sample_messy_sales.csv"
OUT_DIR="$ROOT_DIR/output/demo_run"

mkdir -p "$OUT_DIR"

echo "Running spreadsheet-rescue demo..."
echo "  input:  $INPUT_FILE"
echo "  output: $OUT_DIR"

if command -v srescue >/dev/null 2>&1; then
  srescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR"
  srescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR"
elif command -v uv >/dev/null 2>&1; then
  uv run srescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR"
  uv run srescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR"
else
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m spreadsheet_rescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR"
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m spreadsheet_rescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR"
fi

echo ""
echo "Demo artifacts:"
echo "  $OUT_DIR/Final_Report.xlsx"
echo "  $OUT_DIR/qc_report.json"
echo "  $OUT_DIR/run_manifest.json"
