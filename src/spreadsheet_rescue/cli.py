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


def _find_duplicate_target_sources(
    columns: pd.Index, mapping: dict[str, str]
) -> dict[str, list[str]]:
    sources_by_target: dict[str, list[str]] = {}
    for raw_col in columns:
        raw_name = str(raw_col)
        source_norm = _normalize_column_name(raw_col)
        target = mapping.get(source_norm, source_norm)
        sources_by_target.setdefault(target, []).append(raw_name)
    return {
        target: sources
        for target, sources in sources_by_target.items()
        if len(sources) > 1
    }


def _format_duplicate_columns_message(
    duplicates: dict[str, list[str]], *, mapping_applied: bool
) -> str:
    prefix = (
        "Mapping produced duplicate columns"
        if mapping_applied
        else "Duplicate columns after normalization"
    )
    details = []
    for target in sorted(duplicates):
        sources = " + ".join(duplicates[target])
        details.append(f"{target} (source: {sources})")
    return f"{prefix}: {'; '.join(details)}. Rename or remove one."


def _write_manifest(
    out_dir: Path,
    input_file: Path,
    run_id: str,
    created_at: str,
    qc: QCReport,
    *,
    status: str = "success",
    error_code: int | None = None,
    error_message: str = "",
) -> Path:
    sha256 = ""
    try:
        sha256 = sha256_file(input_file)
    except OSError:
        pass

    manifest = RunManifest(
        run_id=run_id,
        version=__version__,
        input_path=str(input_file.resolve()),
        output_dir=str(out_dir.resolve()),
        created_at_utc=created_at,
        rows_in=qc.rows_in,
        rows_out=qc.rows_out,
        sha256=sha256,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )
    return write_json(out_dir / "run_manifest.json", manifest.to_dict())


def _write_failure_artifacts(
    out_dir: Path,
    input_file: Path,
    run_id: str,
    created_at: str,
    *,
    message: str,
    rows_in: int = 0,
    error_code: int = 2,
) -> tuple[Path, Path]:
    qc = QCReport(rows_in=rows_in, rows_out=0, dropped_rows=rows_in, warnings=[message])
    qc_path = write_qc_report(out_dir, qc)
    manifest_path = _write_manifest(
        out_dir,
        input_file,
        run_id,
        created_at,
        qc,
        status="failed",
        error_code=error_code,
        error_message=message,
    )
    return qc_path, manifest_path


def _write_text_artifact(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)
    return path


def _summary_date_range(clean_df: pd.DataFrame) -> str:
    if clean_df.empty or "date" not in clean_df.columns:
        return "N/A"
    parsed = pd.to_datetime(clean_df["date"], errors="coerce")
    parsed = parsed.dropna()
    if parsed.empty:
        return "N/A"
    return f"{parsed.min().date().isoformat()} to {parsed.max().date().isoformat()}"


def _summary_command(
    *,
    input_file: Path,
    out_dir: Path,
    mapping: dict[str, str],
    profile: Path | None,
    dayfirst: bool,
    number_locale: NumberLocaleOption,
) -> str:
    parts: list[str] = [
        "srescue run",
        f"--input {input_file.name}",
        f"--out-dir {out_dir.name or str(out_dir)}",
        "--dayfirst" if dayfirst else "--monthfirst",
        f"--number-locale {number_locale.value}",
    ]
    if profile:
        parts.append(f"--profile {profile.name}")
    for source, target in sorted(mapping.items()):
        parts.append(f"--map {target}={source}")
    return " ".join(parts)


def _write_summary_artifact(
    *,
    out_dir: Path,
    input_file: Path,
    qc: QCReport,
    kpis: dict[str, object],
    clean_df: pd.DataFrame,
    mapping: dict[str, str],
    profile: Path | None,
    dayfirst: bool,
    number_locale: NumberLocaleOption,
    max_warnings: int = 5,
) -> Path:
    def _as_float(value: object, default: float = 0.0) -> float:
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def _as_int(value: object, default: int = 0) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default

    warning_lines = qc.warnings[:max_warnings]
    lines: list[str] = [
        "spreadsheet-rescue summary",
        f"tool_version: spreadsheet-rescue v{__version__}",
        f"input_file: {input_file.name}",
        f"rows_in: {qc.rows_in}",
        f"rows_out: {qc.rows_out}",
        f"rows_dropped: {qc.dropped_rows}",
        f"warning_count: {len(qc.warnings)}",
    ]
    for idx, warning in enumerate(warning_lines, start=1):
        lines.append(f"warning_{idx}: {warning}")
    if len(qc.warnings) > max_warnings:
        lines.append(f"warning_more: {len(qc.warnings) - max_warnings}")

    total_revenue = _as_float(kpis.get("Total Revenue", 0.0))
    total_profit = _as_float(kpis.get("Total Profit", 0.0))
    margin = _as_float(kpis.get("Profit Margin %", 0.0))
    total_units = _as_int(kpis.get("Total Units", 0))
    top_product = str(kpis.get("Top Product", "N/A"))
    top_region = str(kpis.get("Top Region", "N/A"))

    lines.extend(
        [
            f"date_range: {_summary_date_range(clean_df)}",
            f"kpi_total_revenue: {total_revenue:.2f}",
            f"kpi_total_profit: {total_profit:.2f}",
            f"kpi_profit_margin_pct: {margin:.2f}",
            f"kpi_total_units: {total_units}",
            f"kpi_top_product: {top_product}",
            f"kpi_top_region: {top_region}",
            "command: "
            + _summary_command(
                input_file=input_file,
                out_dir=out_dir,
                mapping=mapping,
                profile=profile,
                dayfirst=dayfirst,
                number_locale=number_locale,
            ),
        ]
    )
    payload = "\n".join(lines) + "\n"
    return _write_text_artifact(out_dir / "summary.txt", payload)


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
    run_id = created_at
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mapping = _parse_column_map(_load_profile_map(profile) + (col_map or []), quiet=quiet)
    except ValueError as exc:
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir,
            input_file,
            run_id,
            created_at,
            message=str(exc),
            error_code=2,
        )
        _err(str(exc))
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

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
            out_dir,
            input_file,
            run_id,
            created_at,
            message=str(exc),
            error_code=2,
        )
        _err(str(exc))
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    try:
        if raw_df.empty:
            message = "Input file has 0 rows."
            qc_path, manifest_path = _write_failure_artifacts(
                out_dir,
                input_file,
                run_id,
                created_at,
                message=message,
                error_code=2,
            )
            _err(message)
            console.print(f"  QC report -> {qc_path}")
            console.print(f"  Manifest  -> {manifest_path}")
            raise typer.Exit(code=2)

        duplicate_targets = _find_duplicate_target_sources(raw_df.columns, mapping)
        if duplicate_targets:
            message = _format_duplicate_columns_message(
                duplicate_targets, mapping_applied=bool(mapping)
            )
            qc_path, manifest_path = _write_failure_artifacts(
                out_dir,
                input_file,
                run_id,
                created_at,
                message=message,
                rows_in=len(raw_df),
                error_code=2,
            )
            _err(message)
            console.print(f"  QC report -> {qc_path}")
            console.print(f"  Manifest  -> {manifest_path}")
            raise typer.Exit(code=2)

        # ── Map columns (if requested) ───────────────────────────
        if mapping:
            raw_df = _apply_column_map(raw_df, mapping)

        # ── Clean ────────────────────────────────────────────────
        echo("[blue]>[/blue] Cleaning …")
        clean_df, qc = clean_dataframe(
            raw_df, dayfirst=dayfirst, number_locale=number_locale.value
        )

        # Always write QC
        qc_path = write_qc_report(out_dir, qc)
        echo(f"  QC report -> {qc_path}")

        if qc.missing_columns:
            message = f"Missing columns: {', '.join(qc.missing_columns)}"
            _err(f"Missing columns: {', '.join(qc.missing_columns)}")
            console.print(f"  Expected: {', '.join(REQUIRED_COLUMNS)}")
            console.print("  Hint: use --map target=source to rename headers")
            _write_manifest(
                out_dir,
                input_file,
                run_id,
                created_at,
                qc,
                status="failed",
                error_code=2,
                error_message=message,
            )
            raise typer.Exit(code=2)

        if not quiet:
            for w in qc.warnings:
                console.print(f"  [yellow]![/yellow] {w}")
            console.print(f"  {qc.rows_out} clean rows retained")

        # ── Compute KPIs ─────────────────────────────────────────
        echo("[blue]>[/blue] Computing KPIs …")
        kpis = compute_dashboard_kpis(clean_df)
        weekly = compute_weekly(clean_df)
        top_products = compute_top_products(clean_df)
        top_regions = compute_top_regions(clean_df)

        # ── Write report ─────────────────────────────────────────
        echo("[blue]>[/blue] Writing Final_Report.xlsx …")
        report_path = write_report(
            out_dir, clean_df, kpis, weekly, top_products, top_regions, qc=qc,
        )
        echo(f"  Report -> {report_path}")

        # ── Manifest ─────────────────────────────────────────────
        manifest_path = _write_manifest(out_dir, input_file, run_id, created_at, qc)
        echo(f"  Manifest -> {manifest_path}")

        # ── Human-readable summary ──────────────────────────────
        summary_path = _write_summary_artifact(
            out_dir=out_dir,
            input_file=input_file,
            qc=qc,
            kpis=kpis,
            clean_df=clean_df,
            mapping=mapping,
            profile=profile,
            dayfirst=dayfirst,
            number_locale=number_locale,
        )
        echo(f"  Summary  -> {summary_path}")

        if not quiet:
            console.print(Panel(
                f"[green]Done[/green] — {qc.rows_out} rows -> {report_path}",
                title="Pipeline Complete", border_style="green",
            ))
    except typer.Exit:
        raise
    except Exception as exc:
        message = f"Unexpected internal error: {exc}"
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir,
            input_file,
            run_id,
            created_at,
            message=message,
            rows_in=len(raw_df),
            error_code=1,
        )
        _err(message)
        console.print(f"  QC report -> {qc_path}")
        console.print(f"  Manifest  -> {manifest_path}")
        raise typer.Exit(code=1)


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
    run_id = created_at
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mapping = _parse_column_map(_load_profile_map(profile) + (col_map or []), quiet=quiet)
    except ValueError as exc:
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir,
            input_file,
            run_id,
            created_at,
            message=str(exc),
            error_code=2,
        )
        _err(str(exc))
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

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
            out_dir,
            input_file,
            run_id,
            created_at,
            message=str(exc),
            error_code=2,
        )
        _err(str(exc))
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=2)

    echo(f"  {len(raw_df)} rows x {len(raw_df.columns)} columns")

    try:
        if raw_df.empty:
            message = "Input file has 0 rows."
            qc_path, manifest_path = _write_failure_artifacts(
                out_dir,
                input_file,
                run_id,
                created_at,
                message=message,
                error_code=2,
            )
            _err(message)
            console.print(f"  QC       -> {qc_path}")
            console.print(f"  Manifest -> {manifest_path}")
            raise typer.Exit(code=2)

        duplicate_targets = _find_duplicate_target_sources(raw_df.columns, mapping)
        if duplicate_targets:
            message = _format_duplicate_columns_message(
                duplicate_targets, mapping_applied=bool(mapping)
            )
            qc_path, manifest_path = _write_failure_artifacts(
                out_dir,
                input_file,
                run_id,
                created_at,
                message=message,
                rows_in=len(raw_df),
                error_code=2,
            )
            _err(message)
            console.print(f"  QC       -> {qc_path}")
            console.print(f"  Manifest -> {manifest_path}")
            raise typer.Exit(code=2)

        if mapping:
            raw_df = _apply_column_map(raw_df, mapping)

        # ── Clean (dry) ──────────────────────────────────────────
        _, qc = clean_dataframe(raw_df, dayfirst=dayfirst, number_locale=number_locale.value)

        # Warn if all rows dropped
        if (qc.rows_out == 0 and qc.rows_in > 0) and (not quiet):
            console.print(
                "[yellow]![/yellow] Validation warning: "
                "cleaned dataset is empty (all rows invalid)."
            )

        qc_path = write_qc_report(out_dir, qc)
        error_message = ""
        status = "success"
        error_code: int | None = None
        if qc.missing_columns:
            status = "failed"
            error_code = 2
            error_message = f"Missing columns: {', '.join(qc.missing_columns)}"
        manifest_path = _write_manifest(
            out_dir,
            input_file,
            run_id,
            created_at,
            qc,
            status=status,
            error_code=error_code,
            error_message=error_message,
        )

        # ── Summary table ────────────────────────────────────────
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
    except typer.Exit:
        raise
    except Exception as exc:
        message = f"Unexpected internal error: {exc}"
        qc_path, manifest_path = _write_failure_artifacts(
            out_dir,
            input_file,
            run_id,
            created_at,
            message=message,
            rows_in=len(raw_df),
            error_code=1,
        )
        _err(message)
        console.print(f"  QC       -> {qc_path}")
        console.print(f"  Manifest -> {manifest_path}")
        raise typer.Exit(code=1)
