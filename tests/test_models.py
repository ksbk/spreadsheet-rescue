from __future__ import annotations

import pytest

from spreadsheet_rescue.models import QCReport, RunManifest


def test_qcreport_to_dict_returns_list_copies() -> None:
    qc = QCReport(
        rows_in=10,
        rows_out=8,
        dropped_rows=2,
        missing_columns=["date"],
        warnings=["bad row"],
    )

    payload = qc.to_dict()
    payload["missing_columns"].append("region")
    payload["warnings"].append("another")

    assert qc.missing_columns == ["date"]
    assert qc.warnings == ["bad row"]


def test_qcreport_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="rows_in"):
        QCReport(rows_in=-1)

    with pytest.raises(ValueError, match="rows_out"):
        QCReport(rows_out=-1)

    with pytest.raises(ValueError, match="dropped_rows"):
        QCReport(dropped_rows=-1)


def test_qcreport_rejects_inconsistent_row_relationships() -> None:
    with pytest.raises(ValueError, match="rows_out"):
        QCReport(rows_in=2, rows_out=3)

    with pytest.raises(ValueError, match="dropped_rows"):
        QCReport(rows_in=5, rows_out=4, dropped_rows=2)

    with pytest.raises(ValueError, match="dropped_rows"):
        QCReport(rows_in=5, rows_out=4, dropped_rows=0)


def test_qcreport_rejects_non_string_lists() -> None:
    with pytest.raises(TypeError, match="missing_columns"):
        QCReport(missing_columns=["date", 1])  # type: ignore[list-item]

    with pytest.raises(TypeError, match="warnings"):
        QCReport(warnings=["warn", object()])  # type: ignore[list-item]


def test_qcreport_rejects_string_value_for_list_fields() -> None:
    with pytest.raises(TypeError, match="missing_columns"):
        QCReport(missing_columns="date")  # type: ignore[arg-type]


def test_qcreport_accepts_none_for_list_fields() -> None:
    qc = QCReport(rows_in=0, rows_out=0, dropped_rows=0, missing_columns=None, warnings=None)  # type: ignore[arg-type]

    assert qc.missing_columns == []
    assert qc.warnings == []


def test_run_manifest_rejects_non_integer_and_negative_counts() -> None:
    with pytest.raises(TypeError, match="rows_in"):
        RunManifest(rows_in=True)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="rows_out"):
        RunManifest(rows_out=-2)
