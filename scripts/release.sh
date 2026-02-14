#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
RAW_VERSION=""
VERSION=""
TAG=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release.sh <VERSION|vVERSION> [--dry-run]

Examples:
  ./scripts/release.sh 0.1.4
  ./scripts/release.sh v0.1.4 --dry-run
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

RAW_VERSION="$1"
VERSION="${RAW_VERSION#v}"
TAG="v${VERSION}"

if [[ -z "$VERSION" ]]; then
  echo "Error: version must be non-empty." >&2
  usage
  exit 2
fi

if [[ $# -eq 2 ]]; then
  if [[ "$2" == "--dry-run" ]]; then
    DRY_RUN=true
  else
    usage
    exit 2
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

if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  echo "Error: local tag '${TAG}' already exists." >&2
  exit 1
fi

if git ls-remote --tags --refs origin "refs/tags/${TAG}" | grep -q "refs/tags/${TAG}$"; then
  echo "Error: remote tag '${TAG}' already exists on origin." >&2
  exit 1
fi

NOTES_FILE="docs/releases/${TAG}.md"
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
  echo "[dry-run] Would bump version to ${VERSION}"
  echo "[dry-run] Would commit: release: ${TAG}"
  echo "[dry-run] Would create tag: ${TAG}"
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

echo "[release] Bumping version to ${VERSION}"
VERSION="${VERSION}" python - <<'PY'
import os
from pathlib import Path
import re

version = os.environ["VERSION"]

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
  git commit -m "release: ${TAG}"
else
  echo "[release] Version files already at ${VERSION}; tagging current HEAD."
fi

# Re-check tag collisions immediately before tagging to avoid race conditions.
if git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  echo "Error: local tag '${TAG}' already exists before tagging step." >&2
  exit 1
fi

if git ls-remote --tags --refs origin "refs/tags/${TAG}" | grep -q "refs/tags/${TAG}$"; then
  echo "Error: remote tag '${TAG}' appeared before tagging step." >&2
  exit 1
fi

git tag -a "${TAG}" -m "${TAG}"

echo "Release prepared:"
echo "  commit: release: ${TAG}"
echo "  tag:    ${TAG}"
echo "Next: git push && git push origin ${TAG}"
