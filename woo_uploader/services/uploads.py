"""Servicios para sincronizar productos sin depender de la interfaz."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Callable, Protocol

from ..models import ProductInput, ValidationResult, to_woo_payload
from ..woocommerce import WooCommerceError


class ProductGateway(Protocol):
    def find_by_sku(self, sku: str) -> dict | None: ...
    def create_product(self, payload: dict, image_path: Path | None = None) -> dict: ...
    def update_product(self, product_id: int, payload: dict, image_path: Path | None = None) -> dict: ...


class DuplicateAction(StrEnum):
    SKIP = "skip"
    UPDATE = "update"


@dataclass(frozen=True)
class SkuConflict:
    product: ProductInput
    existing_product: dict


@dataclass(frozen=True)
class ProductUploadResult:
    product: ProductInput
    outcome: str
    remote_product: dict | None = None
    error: str = ""


@dataclass(frozen=True)
class BatchRowResult:
    row_number: int | None
    sku: str
    outcome: str
    detail: str = ""


@dataclass
class BatchUploadResult:
    rows: list[BatchRowResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def counts(self) -> dict[str, int]:
        return {
            "created": sum(row.outcome == "created" for row in self.rows),
            "updated": sum(row.outcome == "updated" for row in self.rows),
            "skipped": sum(row.outcome == "skipped" for row in self.rows),
            "failed": sum(row.outcome == "failed" for row in self.rows),
        }

    @property
    def failures(self) -> list[str]:
        return [f"Fila {row.row_number}: {row.detail}" for row in self.rows if row.outcome == "failed"]


ClientFactory = Callable[[], ProductGateway]


def is_duplicate_sku_error(exc: WooCommerceError) -> bool:
    message = str(exc).casefold()
    return exc.code == "product_invalid_sku" or (
        "sku" in message and any(fragment in message for fragment in ("duplic", "ya está", "already present", "already exists"))
    )


class ProductUploadService:
    """Encapsula la detección de duplicados y la operación de un producto."""

    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory

    def find_conflict(self, product: ProductInput) -> SkuConflict | None:
        existing = self._client_factory().find_by_sku(product.values.get("sku", "").strip())
        return SkuConflict(product, existing) if existing else None

    def upload(
        self,
        product: ProductInput,
        status: str,
        action: DuplicateAction | None = None,
        existing_product: dict | None = None,
        lookup_existing: bool = True,
    ) -> ProductUploadResult:
        client = self._client_factory()
        existing = client.find_by_sku(product.values.get("sku", "").strip()) if lookup_existing else existing_product
        if existing and action is None:
            raise ValueError("Se debe decidir qué hacer con un SKU existente.")
        if existing and action == DuplicateAction.SKIP:
            return ProductUploadResult(product, "skipped", existing)
        try:
            payload = to_woo_payload(product, status)
            if existing:
                payload.pop("sku", None)
                remote = client.update_product(existing["id"], payload, product.image_path)
                return ProductUploadResult(product, "updated", remote)
            remote = client.create_product(payload, product.image_path)
            return ProductUploadResult(product, "created", remote)
        except WooCommerceError as exc:
            return ProductUploadResult(product, "failed", error=str(exc))


class BatchUploadService:
    """Planifica conflictos y sincroniza un lote ya validado."""

    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory

    def find_conflicts(self, results: list[ValidationResult]) -> dict[int, SkuConflict]:
        client = self._client_factory()
        conflicts: dict[int, SkuConflict] = {}
        for result in results:
            if not result.valid or result.product.row_number is None:
                continue
            existing = client.find_by_sku(result.product.values.get("sku", ""))
            if existing:
                conflicts[result.product.row_number] = SkuConflict(result.product, existing)
        return conflicts

    def upload(
        self,
        results: list[ValidationResult],
        status: str,
        decisions: dict[int, DuplicateAction],
        conflicts: dict[int, SkuConflict],
        on_progress: Callable[[int, int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> BatchUploadResult:
        invalid = [result for result in results if not result.valid]
        if invalid:
            raise ValueError("El lote contiene productos no válidos.")
        client = self._client_factory()
        output = BatchUploadResult()
        total = len(results)
        for index, validation in enumerate(results, start=1):
            if is_cancelled and is_cancelled():
                output.cancelled = True
                break
            product = validation.product
            row_number = product.row_number
            sku = product.values.get("sku", "")
            try:
                if row_number is None:
                    raise ValueError("La fila de origen del producto no está disponible.")
                conflict = conflicts.get(row_number)
                decision = decisions.get(row_number, DuplicateAction.SKIP)
                if conflict and decision == DuplicateAction.SKIP:
                    output.rows.append(BatchRowResult(row_number, sku, "skipped", "SKU existente"))
                else:
                    payload = to_woo_payload(product, status)
                    if conflict:
                        payload.pop("sku", None)
                        client.update_product(conflict.existing_product["id"], payload, product.image_path)
                        outcome = "updated"
                    else:
                        client.create_product(payload, product.image_path)
                        outcome = "created"
                    output.rows.append(BatchRowResult(row_number, sku, outcome))
            except WooCommerceError as exc:
                if is_duplicate_sku_error(exc) and sku:
                    existing = client.find_by_sku(sku)
                    if existing:
                        output.rows.append(BatchRowResult(row_number, sku, "skipped", "SKU existente detectado durante la subida"))
                    else:
                        output.rows.append(BatchRowResult(
                            row_number,
                            sku,
                            "failed",
                            "WooCommerce conserva este SKU en su tabla interna, pero no devuelve ningún producto. Revise la papelera de productos o regenere la tabla de búsqueda de WooCommerce.",
                        ))
                else:
                    output.rows.append(BatchRowResult(row_number, sku, "failed", str(exc)))
            except ValueError as exc:
                output.rows.append(BatchRowResult(row_number, sku, "failed", str(exc)))
            if on_progress:
                on_progress(index, total)
        return output
