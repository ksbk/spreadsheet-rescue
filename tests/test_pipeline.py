"""Targeted tests for pipeline edge cases and KPI contracts."""

from __future__ import annotations

import pandas as pd

from spreadsheet_rescue.pipeline import (
    clean_dataframe,
    compute_dashboard_kpis,
    compute_top_products,
    compute_top_regions,
    compute_weekly,
)


def test_missing_required_columns_sets_consistent_qc_counts() -> None:
    df = pd.DataFrame({"foo": [1], "bar": [2]})

    clean_df, qc = clean_dataframe(df)

    assert clean_df.empty
    assert qc.rows_in == 1
    assert qc.rows_out == 0
    assert qc.dropped_rows == 1
    assert qc.missing_columns


def test_invalid_dates_and_numbers_generate_warnings_and_drop_rows() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "not-a-date"],
            "product": ["Widget", "Gadget"],
            "region": ["US", "EU"],
            "revenue": ["100", "bad"],
            "cost": ["40", "20"],
            "units": ["10", "5"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert qc.rows_in == 2
    assert qc.rows_out == 1
    assert qc.dropped_rows == 1
    assert any("unparseable dates" in warning for warning in qc.warnings)
    assert any("Dropped 1 rows" in warning for warning in qc.warnings)


def test_missing_product_or_region_stays_na_and_row_is_dropped() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "product": ["Widget", None, ""],
            "region": ["US", "EU", "APAC"],
            "revenue": ["100", "200", "300"],
            "cost": ["40", "80", "100"],
            "units": ["10", "20", "30"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert clean_df.iloc[0]["product"] == "Widget"
    assert qc.dropped_rows == 2


def test_kpi_helpers_return_empty_contract_outputs() -> None:
    empty = pd.DataFrame()

    weekly = compute_weekly(empty)
    products = compute_top_products(empty)
    regions = compute_top_regions(empty)
    kpis = compute_dashboard_kpis(empty)

    assert list(weekly.columns) == ["week", "revenue", "cost", "profit", "units"]
    assert list(products.columns) == ["product", "revenue", "profit"]
    assert list(regions.columns) == ["region", "revenue", "profit"]
    assert kpis == {
        "Total Revenue": 0,
        "Total Profit": 0,
        "Profit Margin %": 0,
        "Total Units": 0,
        "Top Product": "N/A",
        "Top Region": "N/A",
    }


def test_parentheses_negative_values_are_coerced_correctly() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["US"],
            "revenue": ["(123.45)"],
            "cost": ["(23.45)"],
            "units": ["1"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert clean_df.iloc[0]["revenue"] == -123.45
    assert clean_df.iloc[0]["cost"] == -23.45
    assert clean_df.iloc[0]["profit"] == -100.0
    assert qc.rows_out == 1


def test_numeric_dtype_branch_and_zero_revenue_warning() -> None:
    """Numeric dtypes should be handled and zero-revenue warning emitted."""
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "product": ["Widget", "Gadget"],
            "region": ["US", "EU"],
            "revenue": [0.0, 0.0],
            "cost": [0.0, 0.0],
            "units": [1.0, 2.0],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 2
    assert clean_df["revenue"].sum() == 0
    assert any("Total revenue is 0 after cleaning" in warning for warning in qc.warnings)


def test_all_rows_invalid_adds_empty_dataset_warning() -> None:
    """When all rows are invalid, cleaner emits empty dataset warning."""
    df = pd.DataFrame(
        {
            "date": ["not-a-date", "also-bad"],
            "product": ["Widget", "Gadget"],
            "region": ["US", "EU"],
            "revenue": ["10", "20"],
            "cost": ["1", "2"],
            "units": ["1", "2"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert clean_df.empty
    assert qc.rows_out == 0
    assert any("Cleaned dataset is empty" in warning for warning in qc.warnings)


def test_non_empty_aggregations_and_dashboard_kpis() -> None:
    """Weekly, top lists, and dashboard KPIs should compute on non-empty data."""
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-08", "2024-01-09"],
            "product": ["Widget", "Widget", "Gadget"],
            "region": ["US", "US", "EU"],
            "revenue": [100, 50, 200],
            "cost": [40, 20, 80],
            "units": [10, 5, 20],
        }
    )

    clean_df, _qc = clean_dataframe(df)
    weekly = compute_weekly(clean_df)
    products = compute_top_products(clean_df, n=2)
    regions = compute_top_regions(clean_df, n=2)
    kpis = compute_dashboard_kpis(clean_df)

    assert not weekly.empty
    assert set(weekly.columns) == {"week", "revenue", "cost", "profit", "units"}
    assert not products.empty
    assert products.iloc[0]["product"] in {"Widget", "Gadget"}
    assert not regions.empty
    assert regions.iloc[0]["region"] in {"US", "EU"}
    assert kpis["Total Revenue"] == 350.0
    assert kpis["Total Profit"] == 210.0
    assert kpis["Profit Margin %"] == 60.0
    assert kpis["Top Product"] == "Gadget"
    assert kpis["Top Region"] == "EU"


def test_percent_values_emit_qc_warning_and_are_coerced() -> None:
    """Percent-marked numeric values should warn and still coerce safely."""
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["US"],
            "revenue": ["10%"],
            "cost": ["1%"],
            "units": ["2%"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert float(clean_df.iloc[0]["revenue"]) == 10.0
    assert float(clean_df.iloc[0]["cost"]) == 1.0
    assert float(clean_df.iloc[0]["units"]) == 2.0
    assert any("values with '%' in revenue" in warning for warning in qc.warnings)
    assert any("values with '%' in cost" in warning for warning in qc.warnings)
    assert any("values with '%' in units" in warning for warning in qc.warnings)
