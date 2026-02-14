#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_FILE="$ROOT_DIR/examples/input/sample_messy_sales.csv"
OUT_DIR="$ROOT_DIR/output/demo_run"
PREVIEW_PNG="$ROOT_DIR/demo/dashboard.png"

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

# Render deterministic dashboard preview PNG (no platform screenshot tools).
if command -v uv >/dev/null 2>&1; then
  uv run --with pillow python "$ROOT_DIR/scripts/render_dashboard_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --output "$PREVIEW_PNG"
else
  python "$ROOT_DIR/scripts/render_dashboard_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --output "$PREVIEW_PNG"
fi

echo ""
echo "Demo artifacts:"
echo "  $OUT_DIR/Final_Report.xlsx"
echo "  $OUT_DIR/qc_report.json"
echo "  $OUT_DIR/run_manifest.json"
echo "  $PREVIEW_PNG"
