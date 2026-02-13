"""Cleaning + KPI pipeline — pure functions, no side effects."""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_rescue import REQUIRED_COLUMNS
from spreadsheet_rescue.models import QCReport

# ── Header normalisation ────────────────────────────────────────


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = pd.Index([c.strip().lower() for c in df.columns])
    return df


# ── Type coercion helpers ────────────────────────────────────────


def _coerce_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=False, format="mixed")


def _coerce_numeric(s: pd.Series) -> pd.Series:
    if not pd.api.types.is_numeric_dtype(s):
        cleaned = (
            s.astype(str)
            .str.replace(r"[\$€£,]", "", regex=True)
            .str.replace("—", "", regex=False)
            .str.replace("–", "", regex=False)
            .str.strip()
        )
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(s, errors="coerce")


# ── Main cleaning function ──────────────────────────────────────


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, QCReport]:
    """Clean *df* according to the v0.1 data contract.

    Returns ``(cleaned_df, qc_report)``.  If required columns are missing
    the returned DataFrame is empty but the QC report is populated.
    """
    qc = QCReport(rows_in=len(df))

    # 1. Normalise headers
    df = _normalize_headers(df)

    # 2. Check required columns
    present = set(df.columns)
    missing = sorted(set(REQUIRED_COLUMNS) - present)
    if missing:
        qc.missing_columns = missing
        qc.warnings.append(f"Missing required columns: {', '.join(missing)}")
        return pd.DataFrame(), qc

    # 3. Type coercion
    df["date"] = _coerce_date(df["date"])
    for col in ("revenue", "cost", "units"):
        df[col] = _coerce_numeric(df[col])

    # 4. Trim text fields
    for col in ("product", "region"):
        df[col] = df[col].astype(str).str.strip()

    # 5. Drop rows missing any required field
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).copy()
    dropped = before - len(df)
    if dropped:
        qc.warnings.append(f"Dropped {dropped} rows with invalid/missing values")

    # 6. Derived fields
    df["profit"] = df["revenue"] - df["cost"]
    df["week"] = df["date"].dt.to_period("W").dt.start_time

    # 7. Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    qc.rows_out = len(df)
    qc.dropped_rows = qc.rows_in - qc.rows_out

    if len(df) == 0:
        qc.warnings.append("Cleaned dataset is empty — no valid rows remain")

    return df, qc


# ── Summary / KPI helpers ───────────────────────────────────────


def compute_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate by week: revenue, cost, profit, units."""
    if df.empty:
        return pd.DataFrame(columns=["week", "revenue", "cost", "profit", "units"])
    weekly = (
        df.groupby("week", as_index=False)
        .agg(revenue=("revenue", "sum"), cost=("cost", "sum"),
             profit=("profit", "sum"), units=("units", "sum"))
        .sort_values("week")
    )
    return weekly


def compute_top_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["product", "revenue", "profit"])
    return (
        df.groupby("product", as_index=False)
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"))
        .sort_values("revenue", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def compute_top_regions(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["region", "revenue", "profit"])
    return (
        df.groupby("region", as_index=False)
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"))
        .sort_values("revenue", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def compute_dashboard_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Return a dict of top-level KPIs for the Dashboard sheet."""
    if df.empty:
        return {
            "Total Revenue": 0,
            "Total Profit": 0,
            "Profit Margin %": 0,
            "Total Units": 0,
            "Top Product": "N/A",
            "Top Region": "N/A",
        }

    total_rev = float(df["revenue"].sum())
    total_profit = float(df["profit"].sum())
    margin = round(total_profit / total_rev * 100, 1) if total_rev else 0

    top_product = (
        df.groupby("product")["revenue"].sum().sort_values(ascending=False).index[0]
    )
    top_region = (
        df.groupby("region")["revenue"].sum().sort_values(ascending=False).index[0]
    )

    return {
        "Total Revenue": round(total_rev, 2),
        "Total Profit": round(total_profit, 2),
        "Profit Margin %": margin,
        "Total Units": int(df["units"].sum()),
        "Top Product": top_product,
        "Top Region": top_region,
    }
