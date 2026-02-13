"""Data models / typed dicts used across the package."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from numbers import Integral
from typing import Any


def _to_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    result = int(value)
    if result < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return result


def _to_string_list(values: Sequence[Any] | None, field_name: str) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raise TypeError(f"{field_name} must be a sequence of strings")
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise TypeError(f"{field_name} items must be strings")
        normalized.append(item)
    return normalized


@dataclass
class QCReport:
    """Quality-control report emitted alongside every run.

    Contract invariant: ``dropped_rows == rows_in - rows_out``.
    """

    rows_in: int = 0
    rows_out: int = 0
    dropped_rows: int = 0
    missing_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rows_in = _to_non_negative_int(self.rows_in, "rows_in")
        self.rows_out = _to_non_negative_int(self.rows_out, "rows_out")
        self.dropped_rows = _to_non_negative_int(self.dropped_rows, "dropped_rows")
        self.missing_columns = _to_string_list(self.missing_columns, "missing_columns")
        self.warnings = _to_string_list(self.warnings, "warnings")
        if self.rows_out > self.rows_in:
            raise ValueError("rows_out must be <= rows_in")
        expected_dropped = self.rows_in - self.rows_out
        if self.dropped_rows != expected_dropped:
            raise ValueError("dropped_rows must equal rows_in - rows_out")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "dropped_rows": self.dropped_rows,
            "missing_columns": list(self.missing_columns),
            "warnings": list(self.warnings),
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

    def __post_init__(self) -> None:
        self.rows_in = _to_non_negative_int(self.rows_in, "rows_in")
        self.rows_out = _to_non_negative_int(self.rows_out, "rows_out")

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
