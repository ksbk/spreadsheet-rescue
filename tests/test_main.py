from __future__ import annotations

import runpy

import spreadsheet_rescue.cli as cli_mod


def test_python_m_entrypoint_invokes_cli_app(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    called = {"value": False}

    def _fake_app() -> None:
        called["value"] = True

    monkeypatch.setattr(cli_mod, "app", _fake_app)
    runpy.run_module("spreadsheet_rescue.__main__", run_name="__main__")

    assert called["value"] is True
