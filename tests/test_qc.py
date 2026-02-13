from __future__ import annotations

import json
from pathlib import Path

from spreadsheet_rescue.models import QCReport
from spreadsheet_rescue.qc import write_qc_report


def test_write_qc_report_writes_expected_contract(tmp_path: Path) -> None:
    qc = QCReport(
        rows_in=3, rows_out=2, dropped_rows=1, missing_columns=["cost"], warnings=["warn"]
    )

    out = write_qc_report(tmp_path, qc)

    assert out == tmp_path / "qc_report.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == {
        "dropped_rows": 1,
        "missing_columns": ["cost"],
        "rows_in": 3,
        "rows_out": 2,
        "warnings": ["warn"],
    }
