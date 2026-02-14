#!/usr/bin/env bash
set -euo pipefail

TARGET_VERSION="0.1.4"
TARGET_TAG="v${TARGET_VERSION}"
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release.sh [--dry-run]

This script runs full release checks, bumps version to 0.1.4,
and creates git tag v0.1.4.
EOF
}

if [[ $# -gt 1 ]]; then
  usage
  exit 1
fi

if [[ $# -eq 1 ]]; then
  if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
  else
    usage
    exit 1
  fi
fi

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

if git rev-parse -q --verify "refs/tags/${TARGET_TAG}" >/dev/null; then
  echo "Error: local tag '${TARGET_TAG}' already exists." >&2
  exit 1
fi

if git ls-remote --tags --refs origin "refs/tags/${TARGET_TAG}" | grep -q "refs/tags/${TARGET_TAG}$"; then
  echo "Error: remote tag '${TARGET_TAG}' already exists on origin." >&2
  exit 1
fi

NOTES_FILE="docs/releases/${TARGET_TAG}.md"
if [[ ! -f "$NOTES_FILE" ]]; then
  echo "Error: missing release notes file: ${NOTES_FILE}" >&2
  exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[dry-run] Would run: uv run ruff check src tests scripts"
  echo "[dry-run] Would run: uv run mypy src/spreadsheet_rescue"
  echo "[dry-run] Would run: uv run pytest -q"
  echo "[dry-run] Would run: uv run ./scripts/smoke_install.sh"
  echo "[dry-run] Would run: make customer-pack"
  echo "[dry-run] Would bump version to ${TARGET_VERSION}"
  echo "[dry-run] Would commit: release: ${TARGET_TAG}"
  echo "[dry-run] Would create tag: ${TARGET_TAG}"
  exit 0
fi

echo "[release] Running quality checks"
uv run ruff check src tests scripts
uv run mypy src/spreadsheet_rescue
uv run pytest -q

echo "[release] Running smoke install"
uv run ./scripts/smoke_install.sh

echo "[release] Building customer pack"
make customer-pack

echo "[release] Restoring tracked demo artifacts changed by smoke/demo steps"
git checkout -- \
  demo/dashboard.png \
  demo/clean_data.png \
  demo/weekly.png \
  demo/output/Final_Report.xlsx \
  demo/output/qc.json \
  demo/output/manifest.json

echo "[release] Bumping version to ${TARGET_VERSION}"
python - <<'PY'
from pathlib import Path
import re

version = "0.1.4"

pyproject = Path("pyproject.toml")
text = pyproject.read_text(encoding="utf-8")
text = re.sub(r'(?m)^version = "[^"]+"$', f'version = "{version}"', text, count=1)
pyproject.write_text(text, encoding="utf-8")

init_py = Path("src/spreadsheet_rescue/__init__.py")
text = init_py.read_text(encoding="utf-8")
text = re.sub(r'(?m)^__version__ = "[^"]+"$', f'__version__ = "{version}"', text, count=1)
init_py.write_text(text, encoding="utf-8")

cli_test = Path("tests/test_cli.py")
text = cli_test.read_text(encoding="utf-8")
text = re.sub(r'assert "v[0-9]+\.[0-9]+\.[0-9]+" in result\.stdout',
              f'assert "v{version}" in result.stdout',
              text,
              count=1)
cli_test.write_text(text, encoding="utf-8")
PY

uv lock

git add pyproject.toml src/spreadsheet_rescue/__init__.py tests/test_cli.py uv.lock "$NOTES_FILE"

if ! git diff --cached --quiet; then
  git commit -m "release: ${TARGET_TAG}"
else
  echo "[release] Version files already at ${TARGET_VERSION}; tagging current HEAD."
fi

# Re-check tag collisions immediately before tagging to avoid race conditions.
if git rev-parse -q --verify "refs/tags/${TARGET_TAG}" >/dev/null; then
  echo "Error: local tag '${TARGET_TAG}' already exists before tagging step." >&2
  exit 1
fi

if git ls-remote --tags --refs origin "refs/tags/${TARGET_TAG}" | grep -q "refs/tags/${TARGET_TAG}$"; then
  echo "Error: remote tag '${TARGET_TAG}' appeared before tagging step." >&2
  exit 1
fi

git tag -a "${TARGET_TAG}" -m "${TARGET_TAG}"

echo "Release prepared:"
echo "  commit: release: ${TARGET_TAG}"
echo "  tag:    ${TARGET_TAG}"
echo "Next: git push && git push origin ${TARGET_TAG}"
