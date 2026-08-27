"""Artefactos de ejecución producidos por los casos de uso."""

from __future__ import annotations

import csv
from pathlib import Path

from .uploads import BatchUploadResult


def write_batch_report(result: BatchUploadResult, directory: Path | None = None) -> Path:
    """Escribe el informe de lote con el nombre histórico de la aplicación."""
    path = (directory or Path.cwd()) / "resultado_subida_lote.csv"
    rows = [["fila", "sku", "resultado", "detalle"]]
    outcome_names = {"created": "creado", "updated": "actualizado", "skipped": "omitido", "failed": "error"}
    rows.extend([str(item.row_number or ""), item.sku, outcome_names[item.outcome], item.detail] for item in result.rows)
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        csv.writer(output).writerows(rows)
    return path
