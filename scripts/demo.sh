#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_FILE="$ROOT_DIR/demo/input/messy_sales.csv"
OUT_DIR="$ROOT_DIR/demo/output"
PREVIEW_PNG="$ROOT_DIR/demo/dashboard.png"
CLEAN_DATA_PNG="$ROOT_DIR/demo/clean_data.png"
WEEKLY_PNG="$ROOT_DIR/demo/weekly.png"
QC_CANONICAL="$OUT_DIR/qc_report.json"
MANIFEST_CANONICAL="$OUT_DIR/run_manifest.json"
QC_FRIENDLY="$OUT_DIR/qc.json"
MANIFEST_FRIENDLY="$OUT_DIR/manifest.json"

MAP_ARGS=(
  --map "date=Order Date"
  --map "product=Product Name"
  --map "region=Sales Region"
  --map "revenue=Gross Revenue"
  --map "cost=Cost (€)"
  --map "units=Units Sold"
)

mkdir -p "$OUT_DIR"

echo "Running spreadsheet-rescue demo..."
echo "  input:  $INPUT_FILE"
echo "  output: $OUT_DIR"

if command -v srescue >/dev/null 2>&1; then
  srescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
  srescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
elif command -v uv >/dev/null 2>&1; then
  uv run srescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
  uv run srescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
else
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m spreadsheet_rescue validate --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python -m spreadsheet_rescue run --input "$INPUT_FILE" --out-dir "$OUT_DIR" "${MAP_ARGS[@]}"
fi

# Render deterministic dashboard preview PNG (no platform screenshot tools).
if command -v uv >/dev/null 2>&1; then
  uv run --with pillow python "$ROOT_DIR/scripts/render_dashboard_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --output "$PREVIEW_PNG"
  uv run --with pillow python "$ROOT_DIR/scripts/render_sheet_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --sheet "Clean_Data" \
    --output "$CLEAN_DATA_PNG" \
    --title "Clean_Data Preview"
  uv run --with pillow python "$ROOT_DIR/scripts/render_sheet_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --sheet "Weekly" \
    --output "$WEEKLY_PNG" \
    --title "Weekly Preview"
else
  python "$ROOT_DIR/scripts/render_dashboard_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --output "$PREVIEW_PNG"
  python "$ROOT_DIR/scripts/render_sheet_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --sheet "Clean_Data" \
    --output "$CLEAN_DATA_PNG" \
    --title "Clean_Data Preview"
  python "$ROOT_DIR/scripts/render_sheet_preview.py" \
    --workbook "$OUT_DIR/Final_Report.xlsx" \
    --sheet "Weekly" \
    --output "$WEEKLY_PNG" \
    --title "Weekly Preview"
fi

# Customer-friendly JSON aliases for quick browsing.
cp "$QC_CANONICAL" "$QC_FRIENDLY"
cp "$MANIFEST_CANONICAL" "$MANIFEST_FRIENDLY"
rm -f "$QC_CANONICAL" "$MANIFEST_CANONICAL"

echo ""
echo "Demo artifacts:"
echo "  $OUT_DIR/Final_Report.xlsx"
echo "  $QC_FRIENDLY"
echo "  $MANIFEST_FRIENDLY"
echo "  $PREVIEW_PNG"
echo "  $CLEAN_DATA_PNG"
echo "  $WEEKLY_PNG"
