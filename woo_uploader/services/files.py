"""Apertura de archivos y carpetas locales con la aplicación del sistema."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def open_local_path(path: Path) -> None:
    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(f"No se encontró {target}")
    if sys.platform.startswith("win"):
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["xdg-open", str(target)])
