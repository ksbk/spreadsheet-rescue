"""Excel report writer — produces Final_Report.xlsx."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.table import Table, TableStyleInfo

from spreadsheet_rescue.models import QCReport

# ── Style constants ──────────────────────────────────────────────

HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

TITLE_FONT = Font(name="Calibri", bold=True, size=14, color="2F5496")
SUBTITLE_FONT = Font(name="Calibri", bold=False, size=10, color="808080")
LABEL_FONT = Font(name="Calibri", bold=True, size=11)
VALUE_FONT = Font(name="Calibri", size=11)
WARN_FONT = Font(name="Calibri", italic=True, size=10, color="CC6600")

NOTE_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
KPI_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

CURRENCY_FMT = '#,##0.00'
INT_FMT = '#,##0'
PCT_FMT = '0.0"%"'

# Column-name → format mapping for data sheets
_COL_FORMATS: dict[str, str] = {
    "revenue": CURRENCY_FMT,
    "cost": CURRENCY_FMT,
    "profit": CURRENCY_FMT,
    "units": INT_FMT,
}


# ── Helpers ──────────────────────────────────────────────────────


def _style_header(ws, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN


def _auto_width(ws) -> None:
    for col_cells in ws.columns:
        letter = col_cells[0].column_letter
        width = max(len(str(c.value or "")) for c in col_cells) + 4
        ws.column_dimensions[letter].width = min(width, 30)


def _apply_number_formats(ws, col_names: list[str]) -> None:
    """Apply number formats to data columns (rows 2+) by column name."""
    for c_idx, name in enumerate(col_names, 1):
        fmt = _COL_FORMATS.get(name.lower())
        if fmt:
            for row in ws.iter_rows(min_row=2, min_col=c_idx, max_col=c_idx):
                for cell in row:
                    cell.number_format = fmt


def _add_excel_table(ws, name: str, ncols: int, nrows: int) -> None:
    """Turn the data range into a proper Excel Table object."""
    if nrows < 1:
        return
    end_col = get_column_letter(ncols)
    ref = f"A1:{end_col}{nrows + 1}"  # +1 for header
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9", showFirstColumn=False,
        showLastColumn=False, showRowStripes=True, showColumnStripes=False,
    )
    ws.add_table(table)


def _df_to_sheet(
    wb: Workbook, name: str, df: pd.DataFrame, *, as_table: bool = False,
) -> None:
    ws = wb.create_sheet(title=name)
    col_names = list(df.columns)
    for r, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c, val in enumerate(row, 1):
            ws.cell(row=r, column=c, value=val)
    _style_header(ws, len(col_names))
    _apply_number_formats(ws, col_names)
    ws.freeze_panes = "A2"
    _auto_width(ws)
    if as_table and len(df) > 0:
        safe_name = name.replace(" ", "_").replace("-", "_")
        _add_excel_table(ws, safe_name, len(col_names), len(df))


def _write_dashboard(wb: Workbook, kpis: dict, qc: QCReport) -> None:
    ws = wb.create_sheet(title="Dashboard")

    # ── Title ────────────────────────────────────────────────────
    ws.cell(row=1, column=1, value="spreadsheet-rescue — Dashboard").font = TITLE_FONT
    ws.merge_cells("A1:D1")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ws.cell(row=2, column=1, value=f"Generated {generated}").font = SUBTITLE_FONT
    ws.merge_cells("A2:D2")

    # ── Notes block (from QC) ────────────────────────────────────
    row = 4
    ws.cell(row=row, column=1, value="Notes").font = LABEL_FONT
    ws.cell(row=row, column=1).fill = NOTE_FILL
    ws.merge_cells(f"A{row}:D{row}")
    row += 1
    ws.cell(row=row, column=1, value=f"Rows in: {qc.rows_in}").fill = NOTE_FILL
    ws.cell(row=row, column=2, value=f"Rows out: {qc.rows_out}").fill = NOTE_FILL
    ws.cell(row=row, column=3, value=f"Dropped: {qc.dropped_rows}").fill = NOTE_FILL
    for c in range(1, 5):
        ws.cell(row=row, column=c).fill = NOTE_FILL
    row += 1
    if qc.warnings:
        for warn in qc.warnings:
            ws.cell(row=row, column=1, value=f"⚠ {warn}").font = WARN_FONT
            for c in range(1, 5):
                ws.cell(row=row, column=c).fill = NOTE_FILL
            row += 1
    else:
        ws.cell(row=row, column=1, value="No warnings").font = WARN_FONT
        for c in range(1, 5):
            ws.cell(row=row, column=c).fill = NOTE_FILL
        row += 1

    # ── KPI cards ────────────────────────────────────────────────
    row += 1
    ws.cell(row=row, column=1, value="Key Metrics").font = LABEL_FONT
    ws.cell(row=row, column=1).fill = KPI_FILL
    ws.cell(row=row, column=2).fill = KPI_FILL
    row += 1

    kpi_formats: dict[str, str | None] = {
        "Total Revenue": CURRENCY_FMT,
        "Total Profit": CURRENCY_FMT,
        "Profit Margin %": PCT_FMT,
        "Total Units": INT_FMT,
        "Top Product": None,
        "Top Region": None,
    }

    for label, value in kpis.items():
        lbl_cell = ws.cell(row=row, column=1, value=label)
        lbl_cell.font = LABEL_FONT
        lbl_cell.fill = KPI_FILL
        val_cell = ws.cell(row=row, column=2, value=value)
        val_cell.font = VALUE_FONT
        val_cell.fill = KPI_FILL
        fmt = kpi_formats.get(label)
        if fmt:
            val_cell.number_format = fmt
        row += 1

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18


# ── Public API ───────────────────────────────────────────────────


def write_report(
    out_dir: Path,
    clean_df: pd.DataFrame,
    kpis: dict[str, Any],
    weekly: pd.DataFrame,
    top_products: pd.DataFrame,
    top_regions: pd.DataFrame,
    qc: QCReport | None = None,
) -> Path:
    """Write ``Final_Report.xlsx`` and return the path."""
    if qc is None:
        qc = QCReport()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "Final_Report.xlsx"

    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    # Dashboard (with QC notes)
    _write_dashboard(wb, kpis, qc)

    # Weekly
    w = weekly.copy()
    if "week" in w.columns:
        w["week"] = pd.to_datetime(w["week"]).dt.strftime("%Y-%m-%d")
    _df_to_sheet(wb, "Weekly", w)

    # Top_Products
    _df_to_sheet(wb, "Top_Products", top_products)

    # Top_Regions
    _df_to_sheet(wb, "Top_Regions", top_regions)

    # Clean_Data (as Excel Table)
    cd = clean_df.copy()
    if "date" in cd.columns:
        cd["date"] = cd["date"].dt.strftime("%Y-%m-%d")
    if "week" in cd.columns:
        cd["week"] = pd.to_datetime(cd["week"]).dt.strftime("%Y-%m-%d")
    _df_to_sheet(wb, "Clean_Data", cd, as_table=True)

    wb.save(report_path)
    return report_path
