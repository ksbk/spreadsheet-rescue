#!/usr/bin/env python3
"""Build a deterministic customer demo zip for buyer evaluation."""

from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from pathlib import Path

FIXED_ZIP_DT = (2020, 1, 1, 0, 0, 0)

DEMO_FILE_ORDER = [
    Path("demo/input/messy_sales.csv"),
    Path("demo/output/Final_Report.xlsx"),
    Path("demo/output/qc.json"),
    Path("demo/output/manifest.json"),
    Path("demo/output/summary.txt"),
    Path("demo/dashboard.png"),
    Path("demo/clean_data.png"),
    Path("demo/weekly.png"),
]
README_ENTRY = Path("dist/README.txt")
RUN_DEMO_MAC_ENTRY = Path("dist/RUN_DEMO.command")
RUN_DEMO_WIN_ENTRY = Path("dist/run_demo.bat")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _readme_text() -> str:
    return (
        "Customer Demo Pack - spreadsheet-rescue\n"
        "========================================\n\n"
        "This pack is designed for a 60-second buyer evaluation.\n\n"
        "Included files and what they prove:\n"
        "- demo/input/messy_sales.csv\n"
        "  Realistic messy input (ambiguous dates, locale numerics, mapped headers).\n"
        "- demo/output/Final_Report.xlsx\n"
        "  Final client-ready workbook with Dashboard, Weekly, Top tables, Clean_Data.\n"
        "- demo/output/qc.json\n"
        "  Data quality warnings and rows in/out for trust and transparency.\n"
        "- demo/output/manifest.json\n"
        "  Run status, error code, row counts, and reproducibility metadata.\n"
        "- demo/output/summary.txt\n"
        "  Human-readable run summary (rows, warnings, date range, and KPIs).\n"
        "- demo/dashboard.png\n"
        "  KPI dashboard preview generated deterministically from workbook values.\n"
        "- demo/clean_data.png\n"
        "  Clean_Data sheet preview showing normalized row-level output.\n"
        "- demo/weekly.png\n"
        "  Weekly summary preview proving grouped reporting output.\n\n"
        "- dist/RUN_DEMO.command\n"
        "  macOS one-click launcher that opens workbook and proof images.\n"
        "- dist/run_demo.bat\n"
        "  Windows one-click launcher that opens workbook and proof images.\n\n"
        "How to regenerate:\n"
        "1) Run ./scripts/demo.sh\n"
        "2) Run python scripts/build_customer_demo_pack.py\n"
    )


def _run_demo_mac_text() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"\n\n'
        "open_file() {\n"
        '  local target="$1"\n'
        '  if [[ -f "$target" ]]; then\n'
        "    if command -v open >/dev/null 2>&1; then\n"
        '      open "$target"\n'
        "    elif command -v xdg-open >/dev/null 2>&1; then\n"
        '      xdg-open "$target" >/dev/null 2>&1 || true\n'
        "    fi\n"
        '    echo "Opened: $target"\n'
        "  else\n"
        '    echo "Missing: $target"\n'
        "  fi\n"
        "}\n\n"
        'echo "Spreadsheet Rescue demo pack"\n'
        'open_file "$ROOT_DIR/demo/output/Final_Report.xlsx"\n'
        'open_file "$ROOT_DIR/demo/dashboard.png"\n'
        'open_file "$ROOT_DIR/demo/clean_data.png"\n'
        'open_file "$ROOT_DIR/demo/weekly.png"\n\n'
        'echo "QC JSON: $ROOT_DIR/demo/output/qc.json"\n'
        'echo "Manifest: $ROOT_DIR/demo/output/manifest.json"\n'
    )


def _run_demo_win_text() -> str:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"ROOT=%~dp0..\"\r\n"
        "echo Spreadsheet Rescue demo pack\r\n"
        "call :open \"%ROOT%\\demo\\output\\Final_Report.xlsx\"\r\n"
        "call :open \"%ROOT%\\demo\\dashboard.png\"\r\n"
        "call :open \"%ROOT%\\demo\\clean_data.png\"\r\n"
        "call :open \"%ROOT%\\demo\\weekly.png\"\r\n"
        "echo QC JSON: %ROOT%\\demo\\output\\qc.json\r\n"
        "echo Manifest: %ROOT%\\demo\\output\\manifest.json\r\n"
        "echo.\r\n"
        "echo Press any key to close...\r\n"
        "pause >nul\r\n"
        "exit /b 0\r\n"
        "\r\n"
        ":open\r\n"
        "if exist \"%~1\" (\r\n"
        "  start \"\" \"%~1\"\r\n"
        "  echo Opened: %~1\r\n"
        ") else (\r\n"
        "  echo Missing: %~1\r\n"
        ")\r\n"
        "exit /b 0\r\n"
    )


def _run_demo(repo_root: Path) -> None:
    demo_script = repo_root / "scripts" / "demo.sh"
    if not demo_script.exists():
        raise FileNotFoundError(f"Demo script not found: {demo_script}")
    subprocess.run([str(demo_script)], cwd=repo_root, check=True, text=True)


def _require_file(repo_root: Path, rel_path: Path) -> Path:
    path = repo_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Missing required demo file: {path}")
    if not path.is_file():
        raise ValueError(f"Expected file but found non-file path: {path}")
    return path


def _validate_json_payloads(repo_root: Path) -> None:
    qc = json.loads((repo_root / "demo/output/qc.json").read_text(encoding="utf-8"))
    manifest = json.loads((repo_root / "demo/output/manifest.json").read_text(encoding="utf-8"))

    qc_required = {"rows_in", "rows_out", "warnings"}
    manifest_required = {"status", "error_code", "rows_in", "rows_out"}

    missing_qc = qc_required - set(qc)
    if missing_qc:
        missing = ", ".join(sorted(missing_qc))
        raise ValueError(f"demo/output/qc.json missing required keys: {missing}")

    missing_manifest = manifest_required - set(manifest)
    if missing_manifest:
        missing = ", ".join(sorted(missing_manifest))
        raise ValueError(f"demo/output/manifest.json missing required keys: {missing}")


def _write_zip_entry(
    zf: zipfile.ZipFile,
    arcname: str,
    data: bytes,
    *,
    mode: int = 0o644,
) -> None:
    info = zipfile.ZipInfo(filename=arcname, date_time=FIXED_ZIP_DT)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100000 | mode) << 16
    info.create_system = 3
    zf.writestr(info, data)


def build_customer_demo_pack(
    repo_root: Path,
    output_zip: Path,
    *,
    run_demo: bool = True,
) -> Path:
    repo_root = repo_root.resolve()
    output_zip = output_zip.resolve()

    if run_demo:
        _run_demo(repo_root)

    for rel_path in DEMO_FILE_ORDER:
        _require_file(repo_root, rel_path)

    _validate_json_payloads(repo_root)

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, mode="w") as zf:
        for rel_path in DEMO_FILE_ORDER:
            src = repo_root / rel_path
            _write_zip_entry(zf, rel_path.as_posix(), src.read_bytes())
        _write_zip_entry(
            zf,
            RUN_DEMO_MAC_ENTRY.as_posix(),
            _run_demo_mac_text().encode("utf-8"),
            mode=0o755,
        )
        _write_zip_entry(
            zf,
            RUN_DEMO_WIN_ENTRY.as_posix(),
            _run_demo_win_text().encode("utf-8"),
        )
        _write_zip_entry(zf, README_ENTRY.as_posix(), _readme_text().encode("utf-8"))

    return output_zip


def main() -> None:
    parser = argparse.ArgumentParser(description="Build customer-demo-pack.zip")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root(),
        help="Repository root path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root() / "dist" / "customer-demo-pack.zip",
        help="Output zip path.",
    )
    parser.add_argument(
        "--skip-demo",
        action="store_true",
        help="Skip running ./scripts/demo.sh before packaging.",
    )
    args = parser.parse_args()

    out = build_customer_demo_pack(
        args.repo_root,
        args.output,
        run_demo=not args.skip_demo,
    )
    print(f"Customer demo pack -> {out}")


if __name__ == "__main__":
    main()
