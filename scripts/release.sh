#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release.sh <tag> [--dry-run]

Examples:
  ./scripts/release.sh v0.1.2
  ./scripts/release.sh v0.1.2-rc1 --dry-run
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

TAG="$1"
DRY_RUN=false

if [[ $# -ge 2 ]]; then
  if [[ "$2" == "--dry-run" ]]; then
    DRY_RUN=true
  else
    usage
    exit 1
  fi
fi

if [[ "$TAG" != v* ]]; then
  echo "Error: tag must start with 'v' (for example: v0.1.2)." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is not clean. Commit/stash changes first." >&2
  exit 1
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "Error: local tag '$TAG' already exists." >&2
  exit 1
fi

TEMPLATE_FILE="docs/releases/TEMPLATE.md"
NOTES_FILE="docs/releases/${TAG}.md"
RELEASE_DATE="$(date +%Y-%m-%d)"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "Error: template file missing: $TEMPLATE_FILE" >&2
  exit 1
fi

if [[ -f "$NOTES_FILE" ]]; then
  echo "Error: release notes already exist: $NOTES_FILE" >&2
  exit 1
fi

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[dry-run] Would create: $NOTES_FILE"
  echo "[dry-run] Would commit: release: $TAG"
  echo "[dry-run] Would tag: $TAG"
  echo "[dry-run] Would push branch and tag to origin"
  exit 0
fi

if git ls-remote --tags --refs origin "refs/tags/$TAG" | grep -q "refs/tags/$TAG$"; then
  echo "Error: remote tag '$TAG' already exists on origin." >&2
  exit 1
fi

awk -v tag="$TAG" -v release_date="$RELEASE_DATE" '
  {
    gsub(/\{\{TAG\}\}/, tag)
    gsub(/\{\{DATE\}\}/, release_date)
    print
  }
' "$TEMPLATE_FILE" > "$NOTES_FILE"

git add "$NOTES_FILE"
git commit -m "release: $TAG"
git tag -a "$TAG" -m "$TAG"
git push
git push origin "$TAG"

echo "Release prepared and pushed:"
echo "  notes: $NOTES_FILE"
echo "  tag:   $TAG"
echo "GitHub release workflow will publish from docs/releases/${TAG}.md."
