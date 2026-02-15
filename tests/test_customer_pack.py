"""Customer demo pack builder tests."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01"
    b"\x0b\x0e-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

REQUIRED_NAMES = {
    "demo/input/messy_sales.csv",
    "demo/output/Final_Report.xlsx",
    "demo/output/qc.json",
    "demo/output/manifest.json",
    "demo/output/summary.txt",
    "demo/dashboard.png",
    "demo/clean_data.png",
    "demo/weekly.png",
    "dist/RUN_DEMO.command",
    "dist/run_demo.bat",
    "dist/README.txt",
}


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_build_customer_pack_contains_required_files_and_keys(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    script = Path(__file__).resolve().parent.parent / "scripts" / "build_customer_demo_pack.py"
    out_zip = tmp_path / "dist" / "customer-demo-pack.zip"

    _write_file(repo_root / "demo/input/messy_sales.csv", b"a,b\n1,2\n")
    _write_file(repo_root / "demo/output/Final_Report.xlsx", b"PK\x03\x04fake-xlsx")
    _write_file(
        repo_root / "demo/output/qc.json",
        json.dumps(
            {
                "rows_in": 10,
                "rows_out": 9,
                "warnings": ["sample warning"],
            }
        ).encode("utf-8"),
    )
    _write_file(
        repo_root / "demo/output/manifest.json",
        json.dumps(
            {
                "status": "success",
                "error_code": None,
                "rows_in": 10,
                "rows_out": 9,
            }
        ).encode("utf-8"),
    )
    _write_file(
        repo_root / "demo/output/summary.txt",
        (
            "spreadsheet-rescue summary\n"
            "rows_in: 10\n"
            "rows_out: 9\n"
            "warning_count: 1\n"
        ).encode("utf-8"),
    )
    _write_file(repo_root / "demo/dashboard.png", PNG_1X1)
    _write_file(repo_root / "demo/clean_data.png", PNG_1X1)
    _write_file(repo_root / "demo/weekly.png", PNG_1X1)

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo_root),
            "--output",
            str(out_zip),
            "--skip-demo",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert out_zip.exists()

    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        assert REQUIRED_NAMES.issubset(names)

        qc = json.loads(zf.read("demo/output/qc.json").decode("utf-8"))
        manifest = json.loads(zf.read("demo/output/manifest.json").decode("utf-8"))
        summary = zf.read("demo/output/summary.txt").decode("utf-8")
        run_demo_mac = zf.read("dist/RUN_DEMO.command").decode("utf-8")
        run_demo_win = zf.read("dist/run_demo.bat").decode("utf-8")

    assert {"rows_in", "rows_out", "warnings"}.issubset(qc.keys())
    assert {"status", "error_code", "rows_in", "rows_out"}.issubset(manifest.keys())
    assert run_demo_mac.startswith("#!/usr/bin/env bash")
    assert "Final_Report.xlsx" in run_demo_mac
    assert run_demo_win.startswith("@echo off")
    assert "Final_Report.xlsx" in run_demo_win
    assert summary.startswith("spreadsheet-rescue summary")
    assert "rows_in:" in summary


def test_customer_pack_is_deterministic(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    script = Path(__file__).resolve().parent.parent / "scripts" / "build_customer_demo_pack.py"
    out_a = tmp_path / "dist" / "a.zip"
    out_b = tmp_path / "dist" / "b.zip"

    _write_file(repo_root / "demo/input/messy_sales.csv", b"a,b\n1,2\n")
    _write_file(repo_root / "demo/output/Final_Report.xlsx", b"PK\x03\x04fixed-xlsx")
    _write_file(
        repo_root / "demo/output/qc.json",
        b'{"rows_in": 2, "rows_out": 2, "warnings": []}',
    )
    _write_file(
        repo_root / "demo/output/manifest.json",
        b'{"status": "success", "error_code": null, "rows_in": 2, "rows_out": 2}',
    )
    _write_file(
        repo_root / "demo/output/summary.txt",
        b"spreadsheet-rescue summary\nrows_in: 2\nrows_out: 2\nwarning_count: 0\n",
    )
    _write_file(repo_root / "demo/dashboard.png", PNG_1X1)
    _write_file(repo_root / "demo/clean_data.png", PNG_1X1)
    _write_file(repo_root / "demo/weekly.png", PNG_1X1)

    for out in (out_a, out_b):
        subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo-root",
                str(repo_root),
                "--output",
                str(out),
                "--skip-demo",
            ],
            check=True,
            text=True,
            capture_output=True,
        )

    assert out_a.read_bytes() == out_b.read_bytes()
