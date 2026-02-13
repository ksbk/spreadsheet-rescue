"""CLI entry point for spreadsheet-rescue."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable

from spreadsheet_rescue import REQUIRED_COLUMNS, __version__
from spreadsheet_rescue.io import load_table, write_json
from spreadsheet_rescue.models import RunManifest
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


# ── Helpers ──────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"spreadsheet-rescue v{__version__}")
        raise typer.Exit()


def _parse_column_map(raw: list[str] | None) -> dict[str, str]:
    """Parse ``--map key=value`` pairs into ``{source: target}``."""
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            console.print(f"[red]x[/red] Invalid --map value: {item!r}  (expected target=source)")
            raise typer.Exit(code=2)
        target, source = item.split("=", 1)
        mapping[source.strip().lower()] = target.strip().lower()
    return mapping


def _apply_column_map(df, mapping: dict[str, str]):
    """Rename columns in *df* according to *mapping*."""
    if not mapping:
        return df
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {src: tgt for src, tgt in mapping.items() if src in df.columns}
    if rename:
        df = df.rename(columns=rename)
    return df


def _write_manifest(out_dir: Path, input_file: Path, created_at: str, qc) -> Path:
    manifest = RunManifest(
        version=__version__,
        input_path=str(input_file.resolve()),
        output_dir=str(Path(out_dir).resolve()),
        created_at_utc=created_at,
        rows_in=qc.rows_in,
        rows_out=qc.rows_out,
        sha256=sha256_file(input_file),
    )
    return write_json(Path(out_dir) / "run_manifest.json", manifest.to_dict())


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
            "Column mapping: target=source. "
            "E.g. --map revenue=Sales --map date=OrderDate"
        ),
    ),
) -> None:
    """Run the cleaning + reporting pipeline on a spreadsheet."""
    created_at = utcnow_iso()
    mapping = _parse_column_map(col_map)

    console.print(Panel(
        f"[bold]spreadsheet-rescue[/bold] v{__version__}\n"
        f"Input:  {input_file}\nOutput: {out_dir}",
        title="Pipeline Start", border_style="blue",
    ))
    if mapping:
        console.print(f"  Column map: {mapping}")

    # ── Load ─────────────────────────────────────────────────────
    console.print("[blue]>[/blue] Loading input file …")
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]x[/red] {exc}")
        raise typer.Exit(code=2)

    console.print(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    # ── Map columns (if requested) ───────────────────────────────
    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    # ── Clean ────────────────────────────────────────────────────
    console.print("[blue]>[/blue] Cleaning …")
    clean_df, qc = clean_dataframe(raw_df)

    # Always write QC
    qc_path = write_qc_report(out_dir, qc)
    console.print(f"  QC report -> {qc_path}")

    if qc.missing_columns:
        console.print(f"[red]x[/red] Missing columns: {qc.missing_columns}")
        _write_manifest(out_dir, input_file, created_at, qc)
        raise typer.Exit(code=2)

    for w in qc.warnings:
        console.print(f"  [yellow]![/yellow] {w}")
    console.print(f"  {qc.rows_out} clean rows retained")

    # ── Compute KPIs ─────────────────────────────────────────────
    console.print("[blue]>[/blue] Computing KPIs …")
    kpis = compute_dashboard_kpis(clean_df)
    weekly = compute_weekly(clean_df)
    top_products = compute_top_products(clean_df)
    top_regions = compute_top_regions(clean_df)

    # ── Write report ─────────────────────────────────────────────
    console.print("[blue]>[/blue] Writing Final_Report.xlsx …")
    report_path = write_report(
        out_dir, clean_df, kpis, weekly, top_products, top_regions, qc=qc,
    )
    console.print(f"  Report -> {report_path}")

    # ── Manifest ─────────────────────────────────────────────────
    manifest_path = _write_manifest(out_dir, input_file, created_at, qc)
    console.print(f"  Manifest -> {manifest_path}")

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
        help="Column mapping: target=source.",
    ),
) -> None:
    """Validate a file without producing the full report.

    Writes qc_report.json + run_manifest.json only.
    Exit 0 = OK, exit 2 = schema failure.
    """
    created_at = utcnow_iso()
    mapping = _parse_column_map(col_map)

    console.print(Panel(
        f"[bold]spreadsheet-rescue[/bold] v{__version__}  [dim]validate mode[/dim]\n"
        f"Input: {input_file}",
        title="Validate", border_style="cyan",
    ))

    # ── Load ─────────────────────────────────────────────────────
    try:
        raw_df = load_table(input_file)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]x[/red] {exc}")
        raise typer.Exit(code=2)

    console.print(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    if mapping:
        raw_df = _apply_column_map(raw_df, mapping)

    # ── Clean (dry) ──────────────────────────────────────────────
    clean_df, qc = clean_dataframe(raw_df)

    qc_path = write_qc_report(out_dir, qc)
    manifest_path = _write_manifest(out_dir, input_file, created_at, qc)

    # ── Summary table ────────────────────────────────────────────
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

    if qc.missing_columns:
        raise typer.Exit(code=2)
