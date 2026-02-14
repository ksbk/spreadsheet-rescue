#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree is not clean. Commit/stash changes first." >&2
  exit 1
fi

TRACKED_DEMO_ARTIFACTS=(
  demo/dashboard.png
  demo/clean_data.png
  demo/weekly.png
  demo/output/Final_Report.xlsx
  demo/output/qc.json
  demo/output/manifest.json
)

restore_demo_artifacts() {
  git restore --worktree -- "${TRACKED_DEMO_ARTIFACTS[@]}" >/dev/null 2>&1 || true
}

trap restore_demo_artifacts EXIT

echo "[preflight] Running quality checks"
uv run ruff check src tests scripts
uv run mypy src/spreadsheet_rescue
uv run pytest -q

echo "[preflight] Running smoke install"
uv run ./scripts/smoke_install.sh

echo "[preflight] Running demo"
./scripts/demo.sh

echo "[preflight] Building customer pack"
make customer-pack

echo "[preflight] Building docs"
uv run --with mkdocs mkdocs build --strict

echo "[preflight] Restoring tracked demo artifacts"
restore_demo_artifacts
trap - EXIT

if [[ -n "$(git status --porcelain -- "${TRACKED_DEMO_ARTIFACTS[@]}")" ]]; then
  echo "Error: tracked demo artifacts still dirty after preflight." >&2
  exit 1
fi

echo "[preflight] Passed"
