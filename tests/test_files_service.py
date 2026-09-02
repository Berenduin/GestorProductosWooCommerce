from pathlib import Path

import pytest

from woo_uploader.services import files


def test_opens_a_local_path_with_linux_desktop_handler(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "informe.xlsx"
    report.touch()
    calls: list[list[str]] = []
    monkeypatch.setattr(files.sys, "platform", "linux")
    monkeypatch.setattr(files.subprocess, "Popen", lambda command: calls.append(command))

    files.open_local_path(report)

    assert calls == [["xdg-open", str(report.resolve())]]


def test_refuses_to_open_a_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No se encontró"):
        files.open_local_path(tmp_path / "ausente.xlsx")
