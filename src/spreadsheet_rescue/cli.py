"""CLI entry point for spreadsheet-rescue."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Optional

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

if TYPE_CHECKING:
    import pandas as pd

app = typer.Typer(
    name="srescue",
    help="spreadsheet-rescue — Clean messy spreadsheets into client-ready reports.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _printer(quiet: bool) -> Callable[..., None]:
    return console.print if not quiet else (lambda *args, **kwargs: None)


def _err(msg: str) -> None:
    console.print(f"[red]x[/red] {msg}")


# ── Helpers ──────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"spreadsheet-rescue v{__version__}")
        raise typer.Exit()


def _parse_column_map(raw: list[str] | None, *, quiet: bool = False) -> dict[str, str]:
    """Parse ``--map target=source`` pairs into ``{source: target}``."""
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(f"Invalid --map value: {item!r}  (expected target=source)")
        target, source = item.split("=", 1)
        target_norm = target.strip().lower()
        source_norm = source.strip().lower()
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
    lines: list[str] = []
    for line in profile.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _apply_column_map(df: "pd.DataFrame", mapping: dict[str, str]) -> "pd.DataFrame":
    """Rename columns in *df* according to *mapping* (``{source: target}``)."""
    if not mapping:
        return df
    df = df.copy()
    import pandas as pd

    df.columns = pd.Index([c.strip().lower() for c in df.columns])
    rename = {src: tgt for src, tgt in mapping.items() if src in df.columns}
    if rename:
        df = df.rename(columns=rename)
    return df


def _write_manifest(out_dir: Path, input_file: Path, created_at: str, qc: QCReport) -> Path:
    manifest = RunManifest(
        version=__version__,
        input_path=str(input_file.resolve()),
        output_dir=str(out_dir.resolve()),
        created_at_utc=created_at,
        rows_in=qc.rows_in,
        rows_out=qc.rows_out,
        sha256=sha256_file(input_file),
    )
    return write_json(out_dir / "run_manifest.json", manifest.to_dict())


# ── Callbacks ────────────────────────────────────────────────────


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
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
    col_map: Optional[list[str]] = typer.Option(
        None, "--map", "-m",
        help=(
            "Column mapping: target=source (rename source->target). "
            "E.g. --map revenue=Sales --map date=OrderDate"
        ),
    ),
    profile: Optional[Path] = typer.Option(
        None, "--profile",
        help="Profile file containing column mappings (target=source lines).",
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
        if mapping:
            console.print(f"  Column map: {mapping}")

    # ── Load ─────────────────────────────────────────────────────
    echo("[blue]>[/blue] Loading input file …")
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    if raw_df.empty:
        qc = QCReport(rows_in=0, rows_out=0, warnings=["Input file has 0 rows."])
        qc_path = write_qc_report(out_dir, qc)
        manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
        _err("Input file has 0 rows.")
        if not quiet:
            echo(f"  QC report -> {qc_path}")
            echo(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

    # ── Map columns (if requested) ───────────────────────────────
    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    # ── Clean ────────────────────────────────────────────────────
    echo("[blue]>[/blue] Cleaning …")
    clean_df, qc = clean_dataframe(raw_df)

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
    col_map: Optional[list[str]] = typer.Option(
        None, "--map", "-m",
        help="Column mapping: target=source (rename source->target).",
    ),
    profile: Optional[Path] = typer.Option(
        None, "--profile",
        help="Profile file containing column mappings (target=source lines).",
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

    # ── Load ─────────────────────────────────────────────────────
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    if raw_df.empty:
        qc = QCReport(rows_in=0, rows_out=0, warnings=["Input file has 0 rows."])
        qc_path = write_qc_report(out_dir, qc)
        manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
        _err("Input file has 0 rows.")
        if not quiet:
            echo(f"  QC       -> {qc_path}")
            echo(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    # ── Clean (dry) ──────────────────────────────────────────────
    _, qc = clean_dataframe(raw_df)

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
        echo(f"  QC       -> {qc_path}")
        echo(f"  Manifest -> {manifest_path}")

    if qc.missing_columns:
        if quiet:
            _err(f"Missing columns: {', '.join(qc.missing_columns)}")
            console.print(f"  Expected: {', '.join(REQUIRED_COLUMNS)}")
            console.print("  Hint: use --map target=source to rename headers")
        raise typer.Exit(code=2)
