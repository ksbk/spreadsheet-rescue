"""CLI entry point for spreadsheet-rescue."""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum
from pathlib import Path

import pandas as pd
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable

from spreadsheet_rescue import REQUIRED_COLUMNS, __version__
from spreadsheet_rescue.io import load_table, write_json
from spreadsheet_rescue.models import QCReport, RunManifest
from spreadsheet_rescue.pipeline import (
    clean_dataframe,
    compute_dashboard_kpis,
    compute_top_products,
    compute_top_regions,
    compute_weekly,
)
from spreadsheet_rescue.qc import write_qc_report
from spreadsheet_rescue.report import write_report
from spreadsheet_rescue.utils import sha256_file, utcnow_iso

app = typer.Typer(
    name="srescue",
    help="spreadsheet-rescue — Clean messy spreadsheets into client-ready reports.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


class NumberLocaleOption(str, Enum):
    auto = "auto"
    us = "us"
    eu = "eu"


def _noop(*_args: object, **_kwargs: object) -> None:
    return None


def _printer(quiet: bool) -> Callable[..., None]:
    return _noop if quiet else console.print


def _err(msg: str) -> None:
    console.print(f"[red]x[/red] {msg}")


# ── Helpers ──────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"spreadsheet-rescue v{__version__}")
        raise typer.Exit()


def _normalize_column_name(name: object) -> str:
    return re.sub(r"\s+", "_", str(name).strip().lower())


def _find_duplicate_columns(columns: pd.Index) -> list[str]:
    return sorted({str(col) for col in columns[columns.duplicated(keep=False)]})


def _parse_column_map(raw: list[str] | None, *, quiet: bool = False) -> dict[str, str]:
    """Parse ``--map target=source`` pairs into ``{source: target}``."""
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"Invalid --map value: {item!r}  (expected target=source)")
        target, source = item.split("=", 1)
        target_norm = _normalize_column_name(target)
        source_norm = _normalize_column_name(source)
        if not target_norm or not source_norm:
            raise ValueError("--map entries must have non-empty target and source (target=source)")
        if source_norm in mapping and not quiet:
            console.print(f"[yellow]![/yellow] Overriding mapping for source {source_norm!r}")
        mapping[source_norm] = target_norm
    return mapping


def _load_profile_map(profile: Path | None) -> list[str]:
    """Return list of ``target=source`` strings from a profile file."""
    if not profile:
        return []
    if not profile.exists():
        raise ValueError(f"Profile not found: {profile} (expected lines like revenue=Sales)")
    if profile.is_dir():
        raise ValueError(f"Profile is a directory, not a file: {profile}")
    try:
        text = profile.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Cannot read profile {profile}: {exc}") from exc

    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _apply_column_map(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Rename columns in *df* according to *mapping* (``{source: target}``)."""
    if not mapping:
        return df
    df = df.copy()
    df.columns = pd.Index([_normalize_column_name(c) for c in df.columns])
    rename = {src: tgt for src, tgt in mapping.items() if src in df.columns}
    if rename:
        df = df.rename(columns=rename)
    return df


def _write_manifest(out_dir: Path, input_file: Path, created_at: str, qc: QCReport) -> Path:
    sha256 = ""
    try:
        sha256 = sha256_file(input_file)
    except OSError:
        pass

    manifest = RunManifest(
        version=__version__,
        input_path=str(input_file.resolve()),
        output_dir=str(out_dir.resolve()),
        created_at_utc=created_at,
        rows_in=qc.rows_in,
        rows_out=qc.rows_out,
        sha256=sha256,
    )
    return write_json(out_dir / "run_manifest.json", manifest.to_dict())


def _write_failure_artifacts(
    out_dir: Path,
    input_file: Path,
    created_at: str,
    *,
    message: str,
    rows_in: int = 0,
) -> tuple[Path, Path]:
    qc = QCReport(rows_in=rows_in, rows_out=0, dropped_rows=rows_in, warnings=[message])
    qc_path = write_qc_report(out_dir, qc)
    manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
    return qc_path, manifest_path


# ── Callbacks ────────────────────────────────────────────────────


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """spreadsheet-rescue CLI."""


# ── run command ──────────────────────────────────────────────────


@app.command()
def run(
    input_file: Path = typer.Option(
        ..., "--input", "-i",
        help="Path to CSV or XLSX input file.",
        exists=True, readable=True,
    ),
    out_dir: Path = typer.Option(
        Path("output"), "--out-dir", "-o",
        help="Output directory for report + QC + manifest.",
    ),
    col_map: list[str] | None = typer.Option(
        None, "--map", "-m",
        help=(
            "Column mapping: target=source (rename source->target). "
            "E.g. --map revenue=Sales --map date=OrderDate"
        ),
    ),
    profile: Path | None = typer.Option(
        None, "--profile",
        help="Profile file containing column mappings (target=source lines).",
    ),
    dayfirst: bool = typer.Option(
        False,
        "--dayfirst/--monthfirst",
        help="Date parsing mode for ambiguous values like 01/02/2024.",
    ),
    number_locale: NumberLocaleOption = typer.Option(
        NumberLocaleOption.auto,
        "--number-locale",
        help="Numeric parsing mode: auto, us, or eu.",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Suppress informational output; still writes all artifacts.",
    ),
) -> None:
    """Run the cleaning + reporting pipeline on a spreadsheet."""
    echo = _printer(quiet)
    created_at = utcnow_iso()
    try:
        mapping = _parse_column_map(_load_profile_map(profile) + (col_map or []), quiet=quiet)
    except ValueError as exc:
        _err(str(exc))
        raise typer.Exit(code=2)

    out_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        console.print(Panel(
            f"[bold]spreadsheet-rescue[/bold] v{__version__}\n"
            f"Input:  {input_file}\nOutput: {out_dir}",
            title="Pipeline Start", border_style="blue",
        ))
        if profile:
            console.print(f"  Using profile: {profile}")
        if mapping:
            console.print(f"  Column map: {mapping}")
        console.print(
            "  Parse mode: "
            f"date={'DD/MM' if dayfirst else 'MM/DD'}, "
            f"number_locale={number_locale.value}"
        )

    # ── Load ─────────────────────────────────────────────────────
    echo("[blue]>[/blue] Loading input file …")
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError, OSError) as exc:
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir, input_file, created_at, message=str(exc)
        )
        _err(str(exc))
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    if raw_df.empty:
        qc = QCReport(rows_in=0, rows_out=0, warnings=["Input file has 0 rows."])
        qc_path = write_qc_report(out_dir, qc)
        manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
        _err("Input file has 0 rows.")
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

    # ── Map columns (if requested) ───────────────────────────────
    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    duplicate_columns = _find_duplicate_columns(raw_df.columns)
    if duplicate_columns:
        message = (
            "Duplicate columns after normalization/mapping: "
            f"{', '.join(duplicate_columns)}"
        )
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir, input_file, created_at, message=message, rows_in=len(raw_df)
        )
        _err(message)
        console.print("  Hint: avoid mapping multiple source columns into one target")
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

    # ── Clean ────────────────────────────────────────────────────
    echo("[blue]>[/blue] Cleaning …")
    clean_df, qc = clean_dataframe(
        raw_df, dayfirst=dayfirst, number_locale=number_locale.value
    )

    # Always write QC
    qc_path = write_qc_report(out_dir, qc)
    echo(f"  QC report -> {qc_path}")

    if qc.missing_columns:
        _err(f"Missing columns: {', '.join(qc.missing_columns)}")
        console.print(f"  Expected: {', '.join(REQUIRED_COLUMNS)}")
        console.print("  Hint: use --map target=source to rename headers")
        _write_manifest(out_dir, input_file, created_at, qc)
        raise typer.Exit(code=2)

    if not quiet:
        for w in qc.warnings:
            console.print(f"  [yellow]![/yellow] {w}")
        console.print(f"  {qc.rows_out} clean rows retained")

    # ── Compute KPIs ─────────────────────────────────────────────
    echo("[blue]>[/blue] Computing KPIs …")
    kpis = compute_dashboard_kpis(clean_df)
    weekly = compute_weekly(clean_df)
    top_products = compute_top_products(clean_df)
    top_regions = compute_top_regions(clean_df)

    # ── Write report ─────────────────────────────────────────────
    echo("[blue]>[/blue] Writing Final_Report.xlsx …")
    report_path = write_report(
        out_dir, clean_df, kpis, weekly, top_products, top_regions, qc=qc,
    )
    echo(f"  Report -> {report_path}")

    # ── Manifest ─────────────────────────────────────────────────
    manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
    echo(f"  Manifest -> {manifest_path}")

    if not quiet:
        console.print(Panel(
            f"[green]Done[/green] — {qc.rows_out} rows -> {report_path}",
            title="Pipeline Complete", border_style="green",
        ))


# ── validate command ─────────────────────────────────────────────


@app.command()
def validate(
    input_file: Path = typer.Option(
        ..., "--input", "-i",
        help="Path to CSV or XLSX input file.",
        exists=True, readable=True,
    ),
    out_dir: Path = typer.Option(
        Path("output"), "--out-dir", "-o",
        help="Output directory for QC + manifest.",
    ),
    col_map: list[str] | None = typer.Option(
        None, "--map", "-m",
        help="Column mapping: target=source (rename source->target).",
    ),
    profile: Path | None = typer.Option(
        None, "--profile",
        help="Profile file containing column mappings (target=source lines).",
    ),
    dayfirst: bool = typer.Option(
        False,
        "--dayfirst/--monthfirst",
        help="Date parsing mode for ambiguous values like 01/02/2024.",
    ),
    number_locale: NumberLocaleOption = typer.Option(
        NumberLocaleOption.auto,
        "--number-locale",
        help="Numeric parsing mode: auto, us, or eu.",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Suppress informational output; still writes QC + manifest.",
    ),
) -> None:
    """Validate a file without producing the full report.

    Writes qc_report.json + run_manifest.json only.
    Exit 0 = OK, exit 2 = schema failure.
    """
    echo = _printer(quiet)
    created_at = utcnow_iso()
    try:
        mapping = _parse_column_map(_load_profile_map(profile) + (col_map or []), quiet=quiet)
    except ValueError as exc:
        _err(str(exc))
        raise typer.Exit(code=2)

    out_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        console.print(Panel(
            f"[bold]spreadsheet-rescue[/bold] v{__version__}  [dim]validate mode[/dim]\n"
            f"Input: {input_file}",
            title="Validate", border_style="cyan",
        ))
        if profile:
            console.print(f"  Using profile: {profile}")
        console.print(
            "  Parse mode: "
            f"date={'DD/MM' if dayfirst else 'MM/DD'}, "
            f"number_locale={number_locale.value}"
        )

    # ── Load ─────────────────────────────────────────────────────
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError, OSError) as exc:
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir, input_file, created_at, message=str(exc)
        )
        _err(str(exc))
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    if raw_df.empty:
        qc = QCReport(rows_in=0, rows_out=0, warnings=["Input file has 0 rows."])
        qc_path = write_qc_report(out_dir, qc)
        manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
        _err("Input file has 0 rows.")
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    duplicate_columns = _find_duplicate_columns(raw_df.columns)
    if duplicate_columns:
        message = (
            "Duplicate columns after normalization/mapping: "
            f"{', '.join(duplicate_columns)}"
        )
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir, input_file, created_at, message=message, rows_in=len(raw_df)
        )
        _err(message)
        console.print("  Hint: avoid mapping multiple source columns into one target")
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

    # ── Clean (dry) ──────────────────────────────────────────────
    _, qc = clean_dataframe(raw_df, dayfirst=dayfirst, number_locale=number_locale.value)

    # Warn if all rows dropped
    if (qc.rows_out == 0 and qc.rows_in > 0) and (not quiet):
        console.print(
            "[yellow]![/yellow] Validation warning: "
            "cleaned dataset is empty (all rows invalid)."
        )

    qc_path = write_qc_report(out_dir, qc)
    manifest_path = _write_manifest(out_dir, input_file, created_at, qc)

    # ── Summary table ────────────────────────────────────────────
    if not quiet:
        tbl = RichTable(title="Validation Summary", show_lines=True)
        tbl.add_column("Check", style="bold")
        tbl.add_column("Result")

        tbl.add_row("Rows in", str(qc.rows_in))
        tbl.add_row("Rows out", str(qc.rows_out))
        tbl.add_row("Dropped", str(qc.dropped_rows))

        if qc.missing_columns:
            tbl.add_row("Missing columns", ", ".join(qc.missing_columns))
            status = "[red]FAIL[/red]"
        else:
            tbl.add_row("Missing columns", "[green]none[/green]")
            status = "[green]PASS[/green]"

        for w in qc.warnings:
            tbl.add_row("Warning", f"[yellow]{w}[/yellow]")

        tbl.add_row("Status", status)
        console.print(tbl)
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
    else:
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")

    if qc.missing_columns:
        _err(f"Missing columns: {', '.join(qc.missing_columns)}")
        console.print(f"  Expected: {', '.join(REQUIRED_COLUMNS)}")
        console.print("  Hint: use --map target=source to rename headers")
        raise typer.Exit(code=2)
