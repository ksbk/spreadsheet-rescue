"""QC report persistence."""

from __future__ import annotations

from pathlib import Path

from spreadsheet_rescue.io import write_json
from spreadsheet_rescue.models import QCReport


def write_qc_report(out_dir: Path, qc: QCReport) -> Path:
    """Write ``qc_report.json`` into *out_dir* and return the path."""
    return write_json(out_dir / "qc_report.json", qc.to_dict())
