"""I/O helpers — load input files, write JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

# ── Loading ──────────────────────────────────────────────────────


def load_table(path: Path) -> pd.DataFrame:
    """Load a CSV or XLSX file and return a raw DataFrame.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the extension is not ``.csv``, ``.xlsx``, or ``.xls``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str)  # read everything as str first
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, engine="openpyxl", dtype=str)
    raise ValueError(f"Unsupported file type: {suffix!r}. Use .csv or .xlsx")


# ── Writing ──────────────────────────────────────────────────────


def write_json(path: Path, data: dict[str, Any]) -> Path:
    """Write *data* as pretty-printed JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return path
