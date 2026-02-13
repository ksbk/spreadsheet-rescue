"""Targeted tests for pipeline edge cases and KPI contracts."""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_rescue import pipeline as pipeline_mod
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


def test_european_numeric_formats_are_parsed_without_corruption() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["EU"],
            "revenue": ["1.200,50"],
            "cost": ["200,25"],
            "units": ["2"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert float(clean_df.iloc[0]["revenue"]) == 1200.5
    assert float(clean_df.iloc[0]["cost"]) == 200.25
    assert float(clean_df.iloc[0]["profit"]) == 1000.25
    assert qc.rows_out == 1


def test_eu_decimal_comma_warnings_include_column_counters() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["EU"],
            "revenue": ["1.200,50"],
            "cost": ["200,25"],
            "units": ["2,5"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 1
    assert float(clean_df.iloc[0]["revenue"]) == 1200.5
    assert float(clean_df.iloc[0]["cost"]) == 200.25
    assert float(clean_df.iloc[0]["units"]) == 2.5
    assert any("Detected EU decimal commas in revenue: 1 value" in w for w in qc.warnings)
    assert any("Detected EU decimal commas in cost: 1 value" in w for w in qc.warnings)
    assert any("Detected EU decimal commas in units: 1 value" in w for w in qc.warnings)


def test_ambiguous_day_month_dates_emit_warning() -> None:
    df = pd.DataFrame(
        {
            "date": ["01/02/2024", "02/01/2024"],
            "product": ["Widget", "Gadget"],
            "region": ["US", "US"],
            "revenue": ["10", "20"],
            "cost": ["5", "10"],
            "units": ["1", "2"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert len(clean_df) == 2
    assert any("ambiguous day/month dates" in warning for warning in qc.warnings)


def test_duplicate_columns_after_normalization_return_schema_failure_qc() -> None:
    df = pd.DataFrame(
        {
            "Revenue": ["100"],
            " revenue ": ["200"],
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["US"],
            "cost": ["50"],
            "units": ["1"],
        }
    )

    clean_df, qc = clean_dataframe(df)

    assert clean_df.empty
    assert qc.rows_out == 0
    assert qc.dropped_rows == qc.rows_in
    assert any("Duplicate columns after normalization" in warning for warning in qc.warnings)


def test_dayfirst_mode_changes_ambiguous_date_parsing() -> None:
    df = pd.DataFrame(
        {
            "date": ["01/02/2024"],
            "product": ["Widget"],
            "region": ["US"],
            "revenue": ["10"],
            "cost": ["2"],
            "units": ["1"],
        }
    )

    clean_monthfirst, _ = clean_dataframe(df, dayfirst=False)
    clean_dayfirst, qc = clean_dataframe(df, dayfirst=True)

    assert clean_monthfirst.iloc[0]["date"] == pd.Timestamp("2024-01-02")
    assert clean_dayfirst.iloc[0]["date"] == pd.Timestamp("2024-02-01")
    assert any("interpreted as day/month (DD/MM)" in warning for warning in qc.warnings)


def test_explicit_number_locale_modes_parse_differently() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "product": ["US", "EU"],
            "region": ["US", "EU"],
            "revenue": ["1,200.50", "1.200,50"],
            "cost": ["200.25", "200,25"],
            "units": ["1", "1"],
        }
    )

    clean_us, _ = clean_dataframe(df, number_locale="us")
    clean_eu, _ = clean_dataframe(df, number_locale="eu")

    us_row = clean_us[clean_us["product"] == "US"].iloc[0]
    eu_row = clean_eu[clean_eu["product"] == "EU"].iloc[0]
    assert float(us_row["revenue"]) == 1200.5
    assert float(eu_row["revenue"]) == 1200.5


def test_auto_locale_parses_us_grouped_decimal_value() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["US"],
            "region": ["US"],
            "revenue": ["1,234.56"],
            "cost": ["234.56"],
            "units": ["1"],
        }
    )

    clean_df, _qc = clean_dataframe(df, number_locale="auto")

    assert len(clean_df) == 1
    assert float(clean_df.iloc[0]["revenue"]) == 1234.56


def test_auto_locale_ambiguous_single_comma_emits_warning_and_uses_default_parse() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Ambiguous"],
            "region": ["US"],
            "revenue": ["1,234"],
            "cost": ["100"],
            "units": ["1"],
        }
    )

    clean_df, qc = clean_dataframe(df, number_locale="auto")

    assert len(clean_df) == 1
    assert float(clean_df.iloc[0]["revenue"]) == 1234.0
    assert any("ambiguous numeric value" in warning for warning in qc.warnings)
    assert any("interpreted as thousands separators" in warning for warning in qc.warnings)


def test_invalid_number_locale_raises_value_error() -> None:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["Widget"],
            "region": ["US"],
            "revenue": ["10"],
            "cost": ["5"],
            "units": ["1"],
        }
    )

    with pytest.raises(ValueError, match="Invalid number locale"):
        clean_dataframe(df, number_locale="invalid")  # type: ignore[arg-type]


def test_count_ambiguous_dates_returns_zero_when_no_slash_dates() -> None:
    series = pd.Series(["2024-01-01", "not-a-date", None], dtype="string")
    assert pipeline_mod._count_ambiguous_day_month_dates(series) == 0


def test_count_ambiguous_dates_handles_empty_series() -> None:
    series = pd.Series([], dtype="string")
    assert pipeline_mod._count_ambiguous_day_month_dates(series) == 0


def test_normalize_numeric_token_exercises_locale_specific_branches() -> None:
    assert pipeline_mod._normalize_numeric_token("+1,234", locale="us") == "1234"
    assert pipeline_mod._normalize_numeric_token("1,234,56", locale="eu") == "1,234,56"
    assert pipeline_mod._normalize_numeric_token("1.234", locale="eu") == "1234"


def test_normalize_numeric_token_exercises_auto_comma_and_dot_branches() -> None:
    assert pipeline_mod._normalize_numeric_token("1,234", locale="auto") == "1234"
    assert pipeline_mod._normalize_numeric_token("1234,567", locale="auto") == "1234567"
    assert pipeline_mod._normalize_numeric_token("1,234,56", locale="auto") == "1234.56"
    assert pipeline_mod._normalize_numeric_token("1.234", locale="auto") == "1234"
    assert pipeline_mod._normalize_numeric_token("1,2,3", locale="auto") == "1,2,3"


def test_coerce_numeric_value_handles_isna_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_: object) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_mod.pd, "isna", _boom)
    out = pipeline_mod._coerce_numeric_value(object(), locale="auto")
    assert isinstance(out, str)


def test_coerce_numeric_value_returns_none_for_missing_values() -> None:
    assert pipeline_mod._coerce_numeric_value(pd.NA, locale="auto") is None
