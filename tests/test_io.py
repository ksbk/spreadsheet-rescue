from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from spreadsheet_rescue.io import load_table, write_json


def test_load_table_csv_uses_sniffing_and_string_dtype(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a;b\n1;2\n", encoding="utf-8")
    expected = pd.DataFrame({"a": ["1"], "b": ["2"]})

    calls: list[dict[str, object]] = []

    def _fake_read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
        calls.append({"path": path, **kwargs})
        return expected

    monkeypatch.setattr(pd, "read_csv", _fake_read_csv)

    result = load_table(csv_path)

    assert result.equals(expected)
    assert len(calls) == 1
    assert calls[0]["path"] == csv_path
    assert calls[0]["dtype"] == "string"
    assert calls[0]["sep"] is None
    assert calls[0]["engine"] == "python"
    assert calls[0]["encoding"] == "utf-8-sig"
    assert calls[0]["encoding_errors"] == "strict"
    assert calls[0]["na_filter"] is True
    assert calls[0]["keep_default_na"] is True


def test_load_table_csv_with_delimiter_uses_explicit_sep_and_c_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("a|b\n1|2\n", encoding="utf-8")
    expected = pd.DataFrame({"a": ["1"], "b": ["2"]})

    calls: list[dict[str, object]] = []

    def _fake_read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
        calls.append({"path": path, **kwargs})
        return expected

    monkeypatch.setattr(pd, "read_csv", _fake_read_csv)

    result = load_table(csv_path, delimiter="|")

    assert result.equals(expected)
    assert len(calls) == 1
    assert calls[0]["sep"] == "|"
    assert calls[0]["engine"] == "c"


def test_load_table_csv_retries_encoding_on_unicode_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_bytes(b"x")
    expected = pd.DataFrame({"a": ["1"]})

    encodings: list[str] = []

    def _fake_read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
        del path
        encoding = kwargs.get("encoding")
        assert isinstance(encoding, str)
        encodings.append(encoding)
        if encoding in {"utf-8-sig", "utf-8"}:
            raise UnicodeDecodeError("utf-8", b"x", 0, 1, "bad")
        return expected

    monkeypatch.setattr(pd, "read_csv", _fake_read_csv)

    result = load_table(csv_path)

    assert result.equals(expected)
    assert encodings == ["utf-8-sig", "utf-8", "latin-1"]


def test_load_table_xlsx_uses_openpyxl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xlsx_path = tmp_path / "data.xlsx"
    xlsx_path.write_bytes(b"x")
    expected = pd.DataFrame({"a": ["1"]})

    calls: list[dict[str, object]] = []

    def _fake_read_excel(path: Path, **kwargs: object) -> pd.DataFrame:
        calls.append({"path": path, **kwargs})
        return expected

    monkeypatch.setattr(pd, "read_excel", _fake_read_excel)

    result = load_table(xlsx_path)

    assert result.equals(expected)
    assert len(calls) == 1
    assert calls[0]["path"] == xlsx_path
    assert calls[0]["engine"] == "openpyxl"
    assert calls[0]["dtype"] == "string"


def test_load_table_xls_missing_xlrd_raises_friendly_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    xls_path = tmp_path / "legacy.xls"
    xls_path.write_bytes(b"x")

    def _fake_read_excel(path: Path, **kwargs: object) -> pd.DataFrame:
        del path, kwargs
        raise ImportError("No module named xlrd")

    monkeypatch.setattr(pd, "read_excel", _fake_read_excel)

    with pytest.raises(ValueError, match="xlrd"):
        load_table(xls_path)


def test_load_table_rejects_directory_path(tmp_path: Path) -> None:
    input_dir = tmp_path / "fake.csv"
    input_dir.mkdir()

    with pytest.raises(ValueError, match="not a file"):
        load_table(input_dir)


def test_load_table_csv_wraps_parser_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    csv_path = tmp_path / "broken.csv"
    csv_path.write_text('not,a,valid"\n', encoding="utf-8")

    def _fake_read_csv(path: Path, **kwargs: object) -> pd.DataFrame:
        del path, kwargs
        raise pd.errors.ParserError("malformed csv")

    monkeypatch.setattr(pd, "read_csv", _fake_read_csv)

    with pytest.raises(ValueError, match="decode or parse failed"):
        load_table(csv_path)


def test_load_table_csv_bom_reads_headers_correctly(tmp_path: Path) -> None:
    csv_path = tmp_path / "bom.csv"
    csv_path.write_text("col1,col2\n1,2\n", encoding="utf-8-sig")

    result = load_table(csv_path)

    assert list(result.columns) == ["col1", "col2"]
    assert result.iloc[0].to_dict() == {"col1": "1", "col2": "2"}


def test_load_table_csv_latin1_fallback_reads_non_utf_chars(tmp_path: Path) -> None:
    csv_path = tmp_path / "latin1.csv"
    csv_path.write_bytes("name,city\nAndré,Paris\n".encode("latin-1"))

    result = load_table(csv_path)

    assert result.iloc[0]["name"] == "André"


def test_write_json_is_atomic_and_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "artifact.json"
    payload = {
        "b": 1,
        "a": datetime(2024, 1, 2, 3, 4, 5),
        "path": Path("foo/bar"),
    }

    out = write_json(path, payload)

    assert out == path
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '"a": "2024-01-02T03:04:05"' in text
    assert '"path": "foo/bar"' in text
    assert text.index('"a"') < text.index('"b"') < text.index('"path"')
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_write_json_serializes_item_scalar(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    value = pd.Series([7], dtype="int64").iloc[0]

    write_json(path, {"value": value})

    text = path.read_text(encoding="utf-8")
    assert '"value": 7' in text


def test_write_json_raises_on_unknown_type(tmp_path: Path) -> None:
    class Unknown:
        pass

    path = tmp_path / "artifact.json"

    with pytest.raises(TypeError, match="not JSON serializable"):
        write_json(path, {"x": Unknown()})
