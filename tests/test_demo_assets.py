"""Deterministic dashboard preview asset checks."""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from spreadsheet_rescue.models import QCReport
from spreadsheet_rescue.report import write_report

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_WIDTH = 1920
EXPECTED_HEIGHT = 1080
MIN_ASSET_SIZE_BYTES = 40 * 1024
MIN_PREVIEW_WIDTH = 1200
MIN_PREVIEW_HEIGHT = 700


def _assert_png_asset(path: Path, *, min_width: int, min_height: int, min_size: int) -> None:
    assert path.exists(), f"Missing asset: {path}"
    assert path.read_bytes().startswith(PNG_SIGNATURE), f"Invalid PNG signature: {path}"
    width, height = _read_png_dimensions(path)
    assert width >= min_width
    assert height >= min_height
    assert path.stat().st_size >= min_size


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"Invalid PNG signature: {path}")
    if len(data) < 24:
        raise ValueError(f"PNG too short: {path}")
    chunk_type = data[12:16]
    if chunk_type != b"IHDR":
        raise ValueError(f"PNG missing IHDR chunk: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _grayscale_variance(path: Path) -> float:
    code = (
        "from PIL import Image, ImageStat; "
        "import sys; "
        "img=Image.open(sys.argv[1]).convert('L'); "
        "print(ImageStat.Stat(img).var[0])"
    )
    result = subprocess.run(
        ["uv", "run", "--with", "pillow", "python", "-c", code, str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(result.stdout.strip())


def test_render_dashboard_preview_from_generated_report(tmp_path: Path) -> None:
    clean_df = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-08")],
            "product": ["Widget A", "=1+1"],
            "region": ["North", "South"],
            "revenue": [1200.5, 1234.56],
            "cost": [200.25, 700.1],
            "units": [2, 3],
            "profit": [1000.25, 534.46],
            "week": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-08")],
        }
    )
    kpis = {
        "Total Revenue": 2435.06,
        "Total Profit": 1534.71,
        "Profit Margin %": 63.03,
        "Total Units": 5,
        "Top Product": "=1+1",
        "Top Region": "South",
    }
    weekly = pd.DataFrame(
        {
            "week": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-08")],
            "revenue": [1200.5, 1234.56],
            "cost": [200.25, 700.1],
            "profit": [1000.25, 534.46],
            "units": [2, 3],
        }
    )
    top_products = pd.DataFrame(
        {"product": ["Widget A"], "revenue": [1200.5], "profit": [1000.25]}
    )
    top_regions = pd.DataFrame(
        {"region": ["South"], "revenue": [1234.56], "profit": [534.46]}
    )
    qc = QCReport(
        rows_in=3,
        rows_out=2,
        dropped_rows=1,
        warnings=[
            "Found 1 rows with unparseable dates",
            "Detected EU decimal commas in revenue: 1 value",
            "Detected EU decimal commas in cost: 1 value",
            "Detected EU decimal commas in units: 1 value",
            "Dropped 1 rows with invalid/missing values",
        ],
    )

    report_dir = tmp_path / "demo_run"
    report_path = write_report(
        report_dir, clean_df, kpis, weekly, top_products, top_regions, qc=qc
    )
    out_png = tmp_path / "dashboard.png"
    script = Path(__file__).resolve().parent.parent / "scripts" / "render_dashboard_preview.py"

    subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "pillow",
            "python",
            str(script),
            "--workbook",
            str(report_path),
            "--output",
            str(out_png),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert out_png.exists()
    assert out_png.read_bytes().startswith(PNG_SIGNATURE)
    width, height = _read_png_dimensions(out_png)
    assert (width, height) == (EXPECTED_WIDTH, EXPECTED_HEIGHT)
    assert _grayscale_variance(out_png) > 20.0


def test_dashboard_preview_asset_exists_and_is_valid() -> None:
    png_path = Path(__file__).resolve().parent.parent / "demo" / "dashboard.png"
    _assert_png_asset(
        png_path,
        min_width=1280,
        min_height=720,
        min_size=MIN_ASSET_SIZE_BYTES,
    )


def test_sheet_preview_assets_exist_and_are_valid() -> None:
    root = Path(__file__).resolve().parent.parent
    clean_data = root / "demo" / "clean_data.png"
    weekly = root / "demo" / "weekly.png"

    _assert_png_asset(
        clean_data,
        min_width=MIN_PREVIEW_WIDTH,
        min_height=MIN_PREVIEW_HEIGHT,
        min_size=20 * 1024,
    )
    _assert_png_asset(
        weekly,
        min_width=MIN_PREVIEW_WIDTH,
        min_height=MIN_PREVIEW_HEIGHT,
        min_size=20 * 1024,
    )


def test_demo_output_artifacts_exist_and_contain_expected_keys() -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "demo" / "output"

    report_path = out_dir / "Final_Report.xlsx"
    qc_path = out_dir / "qc.json"
    manifest_path = out_dir / "manifest.json"

    assert report_path.exists(), "Missing demo/output/Final_Report.xlsx"
    assert report_path.stat().st_size > 0, "Demo workbook is empty"
    assert qc_path.exists(), "Missing demo/output/qc.json"
    assert manifest_path.exists(), "Missing demo/output/manifest.json"

    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert {"rows_in", "rows_out", "warnings"}.issubset(qc.keys())
    assert isinstance(qc["rows_in"], int)
    assert isinstance(qc["rows_out"], int)
    assert isinstance(qc["warnings"], list)

    assert {"status", "error_code", "rows_in", "rows_out"}.issubset(manifest.keys())
    assert manifest["status"] in {"success", "failed"}
    assert isinstance(manifest["rows_in"], int)
    assert isinstance(manifest["rows_out"], int)


def test_renderer_errors_when_workbook_missing(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parent.parent / "scripts" / "render_dashboard_preview.py"
    missing_xlsx = tmp_path / "missing.xlsx"
    out_png = tmp_path / "dashboard.png"

    result = subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "pillow",
            "python",
            str(script),
            "--workbook",
            str(missing_xlsx),
            "--output",
            str(out_png),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "Workbook not found" in result.stderr or "Workbook not found" in result.stdout


def test_renderer_errors_when_dashboard_sheet_missing(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parent.parent / "scripts" / "render_dashboard_preview.py"
    workbook_path = tmp_path / "no_dashboard.xlsx"
    out_png = tmp_path / "dashboard.png"

    wb = Workbook()
    wb.save(workbook_path)

    result = subprocess.run(
        [
            "uv",
            "run",
            "--with",
            "pillow",
            "python",
            str(script),
            "--workbook",
            str(workbook_path),
            "--output",
            str(out_png),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "Dashboard' sheet" in result.stderr or "Dashboard' sheet" in result.stdout
