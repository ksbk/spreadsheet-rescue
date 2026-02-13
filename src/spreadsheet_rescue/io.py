"""I/O helpers — load input files, write JSON artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Literal, cast

import pandas as pd

# ── Loading ──────────────────────────────────────────────────────


def load_table(path: Path, delimiter: str | None = None) -> pd.DataFrame:
    """Load a CSV or Excel file and return a raw DataFrame.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the extension is not supported, or CSV decoding/parsing fails.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        last_exc: Exception | None = None
        sep = delimiter if delimiter else None
        engine: Literal["c", "python"] = "c" if delimiter else "python"
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(
                    path,
                    dtype="string",
                    sep=sep,
                    engine=engine,
                    encoding=encoding,
                    encoding_errors="strict",
                    na_filter=True,
                    keep_default_na=True,
                )
            except (UnicodeDecodeError, pd.errors.ParserError) as exc:
                last_exc = exc
        raise ValueError(f"Could not read CSV {path} (decode or parse failed)") from last_exc

    if suffix in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        read_excel = cast(Callable[..., pd.DataFrame], getattr(pd, "read_excel"))
        return read_excel(path, engine="openpyxl", dtype="string")

    if suffix == ".xls":
        try:
            read_excel = cast(Callable[..., pd.DataFrame], getattr(pd, "read_excel"))
            return read_excel(path, engine="xlrd", dtype="string")
        except ImportError as exc:
            raise ValueError(
                "Unsupported .xls input unless 'xlrd' is installed. "
                "Either convert to .xlsx or add dependency: pip install xlrd"
            ) from exc

    raise ValueError(f"Unsupported file type: {suffix!r}. Use .csv, .xlsx, or .xls")


# ── Writing ──────────────────────────────────────────────────────


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    item = getattr(obj, "item", None)
    if callable(item):
        converted = item()
        if isinstance(converted, (str, int, float, bool)) or converted is None:
            return converted
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_json(path: Path, data: Any) -> Path:
    """Write *data* as pretty-printed JSON to *path* (atomic + deterministic)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        data,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=_json_default,
    ) + "\n"
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(path)
    return path
