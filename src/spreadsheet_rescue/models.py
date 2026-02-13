"""Data models / typed dicts used across the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QCReport:
    """Quality-control report emitted alongside every run."""

    rows_in: int = 0
    rows_out: int = 0
    dropped_rows: int = 0
    missing_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "dropped_rows": self.dropped_rows,
            "missing_columns": self.missing_columns,
            "warnings": self.warnings,
        }


@dataclass
class RunManifest:
    """Audit-trail manifest for a single pipeline run."""

    tool: str = "spreadsheet-rescue"
    version: str = ""
    input_path: str = ""
    output_dir: str = ""
    created_at_utc: str = ""
    rows_in: int = 0
    rows_out: int = 0
    sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "version": self.version,
            "input_path": self.input_path,
            "output_dir": self.output_dir,
            "created_at_utc": self.created_at_utc,
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "sha256": self.sha256,
        }
