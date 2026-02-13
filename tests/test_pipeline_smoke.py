"""Smoke tests for the spreadsheet-rescue pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spreadsheet_rescue.pipeline import clean_dataframe

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def raw_sales() -> pd.DataFrame:
    return pd.read_csv(EXAMPLES_DIR / "raw_sales.csv", dtype=str)


class TestCleanDataframe:
    """Smoke tests for clean_dataframe."""

    def test_drops_invalid_rows(self, raw_sales: pd.DataFrame) -> None:
        """At least 1 invalid row is dropped (bad date or '—' revenue)."""
        clean_df, qc = clean_dataframe(raw_sales)
        assert qc.dropped_rows >= 1, "Expected at least 1 dropped row"
        assert qc.rows_out < qc.rows_in

    def test_profit_column_exists(self, raw_sales: pd.DataFrame) -> None:
        """Derived 'profit' column must be present after cleaning."""
        clean_df, _qc = clean_dataframe(raw_sales)
        assert "profit" in clean_df.columns

    def test_week_column_exists(self, raw_sales: pd.DataFrame) -> None:
        """Derived 'week' column must be present after cleaning."""
        clean_df, _qc = clean_dataframe(raw_sales)
        assert "week" in clean_df.columns

    def test_no_missing_columns(self, raw_sales: pd.DataFrame) -> None:
        """Example CSV has all required columns."""
        _clean_df, qc = clean_dataframe(raw_sales)
        assert qc.missing_columns == []

    def test_qc_warnings_not_empty(self, raw_sales: pd.DataFrame) -> None:
        """Example CSV has dirty rows → warnings should be generated."""
        _clean_df, qc = clean_dataframe(raw_sales)
        assert len(qc.warnings) > 0

    def test_sorted_by_date(self, raw_sales: pd.DataFrame) -> None:
        """Clean data must be sorted by date."""
        clean_df, _qc = clean_dataframe(raw_sales)
        dates = clean_df["date"].tolist()
        assert dates == sorted(dates)


class TestMissingColumns:
    """Verify schema-failure path."""

    def test_missing_columns_returns_empty_df(self) -> None:
        df = pd.DataFrame({"foo": [1], "bar": [2]})
        clean_df, qc = clean_dataframe(df)
        assert clean_df.empty
        assert len(qc.missing_columns) > 0
        assert "Missing required columns" in qc.warnings[0]
