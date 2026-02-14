#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[smoke] Building wheel"
python -m build --wheel

WHEEL_PATH="$(ls -1 dist/*.whl | tail -n 1)"
if [[ -z "${WHEEL_PATH:-}" ]]; then
  echo "[smoke] No wheel found in dist/" >&2
  exit 1
fi

echo "[smoke] Installing wheel into clean virtualenv"
SMOKE_VENV="$(mktemp -d "${TMPDIR:-/tmp}/srescue-smoke-XXXXXX")"
cleanup() {
  rm -rf "$SMOKE_VENV"
}
trap cleanup EXIT

python3 -m venv "$SMOKE_VENV"
# shellcheck disable=SC1091
source "$SMOKE_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install "$WHEEL_PATH"

echo "[smoke] Checking installed CLI"
spreadsheet-rescue --help >/dev/null

echo "[smoke] Running demo pipeline"
rm -f demo/output/Final_Report.xlsx demo/output/qc.json demo/output/manifest.json demo/dashboard.png
./scripts/demo.sh

echo "[smoke] Verifying demo outputs"
test -f demo/output/Final_Report.xlsx
test -f demo/output/qc.json
test -f demo/output/manifest.json
test -f demo/dashboard.png

echo "[smoke] Smoke install passed"
