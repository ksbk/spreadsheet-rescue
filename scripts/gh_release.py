#!/usr/bin/env python3
"""Create/update a GitHub release and upload the customer demo pack asset."""

import argparse
import shutil
import subprocess
from pathlib import Path

DEFAULT_TAG = "v0.1.4"
DEMO_ARTIFACTS = [
    "demo/dashboard.png",
    "demo/clean_data.png",
    "demo/weekly.png",
    "demo/output/Final_Report.xlsx",
    "demo/output/qc.json",
    "demo/output/manifest.json",
]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _status_paths(repo_root: Path, paths: list[str]) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    dirty_paths: set[str] = set()
    for line in result.stdout.splitlines():
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        dirty_paths.add(entry)
    return dirty_paths


def _restore_paths(repo_root: Path, paths: list[str]) -> None:
    if not paths:
        return
    subprocess.run(
        ["git", "restore", "--worktree", "--", *paths],
        cwd=repo_root,
        check=True,
        text=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish GitHub release with customer-demo-pack.zip"
    )
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Release tag (default: v0.1.4)")
    parser.add_argument(
        "--notes",
        type=Path,
        default=None,
        help="Release notes markdown file. Default: docs/releases/<tag>.md",
    )
    parser.add_argument(
        "--asset",
        type=Path,
        default=Path("dist/customer-demo-pack.zip"),
        help="Release asset path.",
    )
    parser.add_argument(
        "--build-pack",
        action="store_true",
        help="Run `make customer-pack` before publishing release.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running with a dirty working tree.",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    notes_path = args.notes or Path(f"docs/releases/{args.tag}.md")
    notes = (repo_root / notes_path).resolve()
    asset = (repo_root / args.asset).resolve()

    if shutil.which("gh") is None:
        raise SystemExit("Error: GitHub CLI `gh` is required.")

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    if status.stdout.strip() and not args.force:
        raise SystemExit(
            "Error: working tree is dirty. Commit/stash changes first or pass --force."
        )

    remote_tag = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", "origin", f"refs/tags/{args.tag}"],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    if not remote_tag.stdout.strip():
        raise SystemExit(
            f"Error: tag {args.tag} is not on origin. Push tag before creating the release."
        )

    if not notes.exists():
        raise SystemExit(f"Error: release notes file not found: {notes}")

    if args.build_pack:
        preexisting_demo_dirty = _status_paths(repo_root, DEMO_ARTIFACTS)
        restore_candidates = [
            path for path in DEMO_ARTIFACTS if path not in preexisting_demo_dirty
        ]
        try:
            _run(["make", "customer-pack"], cwd=repo_root)
        finally:
            _restore_paths(repo_root, restore_candidates)

    if not asset.exists():
        raise SystemExit(
            f"Error: release asset not found: {asset}\n"
            "Run `make customer-pack` or pass --build-pack."
        )

    view = subprocess.run(
        ["gh", "release", "view", args.tag],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if view.returncode == 0:
        _run(
            [
                "gh",
                "release",
                "edit",
                args.tag,
                "--title",
                args.tag,
                "--notes-file",
                str(notes),
            ],
            cwd=repo_root,
        )
        _run(
            [
                "gh",
                "release",
                "upload",
                args.tag,
                str(asset),
                "--clobber",
            ],
            cwd=repo_root,
        )
    else:
        _run(
            [
                "gh",
                "release",
                "create",
                args.tag,
                str(asset),
                "--title",
                args.tag,
                "--notes-file",
                str(notes),
            ],
            cwd=repo_root,
        )

    print(f"GitHub release ready: {args.tag}")
    print(f"Notes: {notes}")
    print(f"Asset: {asset}")


if __name__ == "__main__":
    main()
