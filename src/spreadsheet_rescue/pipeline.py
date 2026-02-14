"""Cleaning + KPI pipeline — pure functions, no side effects."""

from __future__ import annotations

import re
from typing import Any, Literal, cast

import pandas as pd

from spreadsheet_rescue import REQUIRED_COLUMNS
from spreadsheet_rescue.models import QCReport

# ── Header normalisation ────────────────────────────────────────


_THOUSANDS_COMMA_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})+$")
_THOUSANDS_DOT_RE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+$")
_AMBIGUOUS_DAY_MONTH_RE = re.compile(r"^\s*(\d{1,2})[/-](\d{1,2})[/-]\d{2,4}\s*$")
NumberLocale = Literal["auto", "us", "eu"]


def _normalize_header_name(name: object) -> str:
    return re.sub(r"\s+", "_", str(name).strip().lower())


def _find_duplicate_columns(columns: pd.Index) -> list[str]:
    return sorted({str(name) for name in columns[columns.duplicated(keep=False)]})


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = pd.Index([_normalize_header_name(c) for c in df.columns])
    return df


# ── Type coercion helpers ────────────────────────────────────────


def _coerce_date(s: pd.Series, *, dayfirst: bool) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=dayfirst, format="mixed")


def _count_ambiguous_day_month_dates(s: pd.Series) -> int:
    parts = s.astype("string").str.extract(_AMBIGUOUS_DAY_MONTH_RE)
    if parts.empty:
        return 0

    first = pd.to_numeric(parts[0], errors="coerce")
    second = pd.to_numeric(parts[1], errors="coerce")
    mask = first.between(1, 12) & second.between(1, 12)
    return int(mask.fillna(False).sum())


def _normalize_numeric_token_with_flags(
    token: str, *, locale: NumberLocale
) -> tuple[str, bool, bool]:
    token = token.strip()
    token = re.sub(r"^\((.*)\)$", r"-\1", token)
    token = token.replace("—", "")
    token = token.replace("–", "")
    token = token.replace("%", "")
    token = re.sub(r"[\$€£]", "", token)
    token = re.sub(r"(?<=\d)[\s\u00a0]+(?=\d)", "", token)
    token = token.replace("'", "")
    token = token.replace("_", "")

    if token in {"", "-", "+"}:
        return "", False, False
    if token.startswith("+"):
        token = token[1:]

    has_comma = "," in token
    has_dot = "." in token
    saw_eu_decimal_comma = False
    saw_ambiguous_separator = False

    if locale == "us":
        if has_comma and has_dot:
            return token.replace(",", ""), saw_eu_decimal_comma, saw_ambiguous_separator
        if has_comma and _THOUSANDS_COMMA_RE.fullmatch(token):
            return token.replace(",", ""), saw_eu_decimal_comma, saw_ambiguous_separator
        return token, saw_eu_decimal_comma, saw_ambiguous_separator

    if locale == "eu":
        if has_comma and has_dot:
            token = token.replace(".", "")
            token = token.replace(",", ".")
            saw_eu_decimal_comma = True
            return token, saw_eu_decimal_comma, saw_ambiguous_separator
        if has_comma:
            if token.count(",") == 1:
                whole, frac = token.split(",", 1)
                if len(frac) in (1, 2, 3):
                    saw_eu_decimal_comma = True
                    return f"{whole}.{frac}", saw_eu_decimal_comma, saw_ambiguous_separator
            return token, saw_eu_decimal_comma, saw_ambiguous_separator
        if has_dot and _THOUSANDS_DOT_RE.fullmatch(token):
            return token.replace(".", ""), saw_eu_decimal_comma, saw_ambiguous_separator
        return token, saw_eu_decimal_comma, saw_ambiguous_separator

    if has_comma and has_dot:
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "")
            token = token.replace(",", ".")
            saw_eu_decimal_comma = True
        else:
            token = token.replace(",", "")
        return token, saw_eu_decimal_comma, saw_ambiguous_separator

    if has_comma:
        if _THOUSANDS_COMMA_RE.fullmatch(token):
            if token.count(",") == 1:
                saw_ambiguous_separator = True
            return token.replace(",", ""), saw_eu_decimal_comma, saw_ambiguous_separator
        if token.count(",") == 1:
            whole, frac = token.split(",", 1)
            if len(frac) in (1, 2):
                saw_eu_decimal_comma = True
                return f"{whole}.{frac}", saw_eu_decimal_comma, saw_ambiguous_separator
            if len(frac) == 3:
                saw_ambiguous_separator = True
                return f"{whole}{frac}", saw_eu_decimal_comma, saw_ambiguous_separator
        parts = token.split(",")
        if len(parts) > 1 and len(parts[-1]) in (1, 2) and all(len(p) == 3 for p in parts[1:-1]):
            saw_eu_decimal_comma = True
            normalized = f"{''.join(parts[:-1])}.{parts[-1]}"
            return normalized, saw_eu_decimal_comma, saw_ambiguous_separator
        return token, saw_eu_decimal_comma, saw_ambiguous_separator

    if has_dot and _THOUSANDS_DOT_RE.fullmatch(token):
        if token.count(".") == 1:
            saw_ambiguous_separator = True
        return token.replace(".", ""), saw_eu_decimal_comma, saw_ambiguous_separator

    return token, saw_eu_decimal_comma, saw_ambiguous_separator


def _normalize_numeric_token(token: str, *, locale: NumberLocale) -> str:
    normalized, _eu_decimal, _ambiguous = _normalize_numeric_token_with_flags(
        token, locale=locale
    )
    return normalized


def _coerce_numeric_value_with_flags(
    value: object, *, locale: NumberLocale
) -> tuple[str | None, bool, bool]:
    try:
        if pd.isna(cast(Any, value)):
            return None, False, False
    except Exception:
        pass
    return _normalize_numeric_token_with_flags(str(value), locale=locale)


def _coerce_numeric_value(value: object, *, locale: NumberLocale) -> str | None:
    normalized, _eu_decimal, _ambiguous = _coerce_numeric_value_with_flags(
        value, locale=locale
    )
    return normalized


def _coerce_numeric(s: pd.Series, *, locale: NumberLocale) -> tuple[pd.Series, int, int]:
    eu_decimal_count = 0
    ambiguous_count = 0

    if not pd.api.types.is_numeric_dtype(s):
        cleaned_values: list[str | None] = []
        for val in s.astype("string"):
            normalized, saw_eu_decimal, saw_ambiguous = _coerce_numeric_value_with_flags(
                val, locale=locale
            )
            if saw_eu_decimal:
                eu_decimal_count += 1
            if saw_ambiguous:
                ambiguous_count += 1
            cleaned_values.append(normalized)
        cleaned = pd.Series(cleaned_values, index=s.index, dtype="string")
        return pd.to_numeric(cleaned, errors="coerce"), eu_decimal_count, ambiguous_count
    return pd.to_numeric(s, errors="coerce"), eu_decimal_count, ambiguous_count


# ── Main cleaning function ──────────────────────────────────────


def clean_dataframe(
    df: pd.DataFrame,
    *,
    dayfirst: bool = False,
    number_locale: NumberLocale = "auto",
) -> tuple[pd.DataFrame, QCReport]:
    """Clean *df* according to the v0.1.4 data contract.

    Returns ``(cleaned_df, qc_report)``.  If required columns are missing
    the returned DataFrame is empty but the QC report is populated.
    """
    if number_locale not in {"auto", "us", "eu"}:
        raise ValueError(f"Invalid number locale: {number_locale!r}. Use auto/us/eu.")

    qc = QCReport(rows_in=len(df), rows_out=len(df), dropped_rows=0)

    # 1. Normalise headers
    df = _normalize_headers(df)
    duplicate_cols = _find_duplicate_columns(df.columns)
    if duplicate_cols:
        qc.rows_out = 0
        qc.dropped_rows = qc.rows_in
        qc.warnings.append(
            f"Duplicate columns after normalization: {', '.join(duplicate_cols)}"
        )
        return pd.DataFrame(), qc

    # 2. Check required columns
    present = set(df.columns)
    missing = sorted(set(REQUIRED_COLUMNS) - present)
    if missing:
        qc.missing_columns = missing
        qc.warnings.append(f"Missing required columns: {', '.join(missing)}")
        qc.rows_out = 0
        qc.dropped_rows = qc.rows_in
        return pd.DataFrame(), qc

    # 3. Type coercion
    ambiguous_dates = _count_ambiguous_day_month_dates(df["date"])
    if ambiguous_dates:
        parsed_mode = "day/month (DD/MM)" if dayfirst else "month/day (MM/DD)"
        qc.warnings.append(
            "Found "
            f"{ambiguous_dates} ambiguous day/month dates; interpreted as {parsed_mode}"
        )

    df["date"] = _coerce_date(df["date"], dayfirst=dayfirst)
    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        qc.warnings.append(f"Found {bad_dates} rows with unparseable dates")

    for col in ("revenue", "cost", "units"):
        pct_count = int(df[col].astype("string").str.contains("%", na=False).sum())
        if pct_count:
            qc.warnings.append(
                f"Found {pct_count} values with '%' in {col}; treated as plain numbers"
            )
        parsed_col, eu_decimal_count, ambiguous_count = _coerce_numeric(
            df[col], locale=number_locale
        )
        df[col] = parsed_col
        if eu_decimal_count:
            suffix = "" if eu_decimal_count == 1 else "s"
            qc.warnings.append(
                f"Detected EU decimal commas in {col}: {eu_decimal_count} value{suffix}"
            )
        if ambiguous_count:
            suffix = "" if ambiguous_count == 1 else "s"
            qc.warnings.append(
                "Detected "
                f"{ambiguous_count} ambiguous numeric value{suffix} in {col} "
                "(example: 1,234); interpreted as thousands separators"
            )

    # 4. Trim text fields
    for col in ("product", "region"):
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    # 5. Drop rows missing any required field
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).copy()
    dropped = before - len(df)
    if dropped:
        qc.warnings.append(f"Dropped {dropped} rows with invalid/missing values")

    # 6. Derived fields
    df["profit"] = df["revenue"] - df["cost"]
    # pandas "W" = weeks ending Sunday; start_time is Monday.
    df["week"] = df["date"].dt.to_period("W").dt.start_time

    # 7. Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    qc.rows_out = len(df)
    qc.dropped_rows = qc.rows_in - qc.rows_out

    if qc.rows_out > 0 and float(df["revenue"].sum()) == 0:
        qc.warnings.append("Total revenue is 0 after cleaning")

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
    """Return top N products by revenue (and profit)."""
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
    """Return top N regions by revenue (and profit)."""
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
    margin = round((total_profit / total_rev) * 100, 2) if total_rev else 0.0

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
