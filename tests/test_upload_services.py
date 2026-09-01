from pathlib import Path

import pytest

from woo_uploader.models import ProductInput, validate_product
from woo_uploader.services.reports import write_batch_report
from woo_uploader.services.uploads import BatchUploadService, DuplicateAction, ProductUploadService
from woo_uploader.woocommerce import WooCommerceError


class FakeClient:
    def __init__(self, existing: dict[str, dict] | None = None, fail_skus: set[str] | None = None) -> None:
        self.existing = existing or {}
        self.fail_skus = fail_skus or set()
        self.created: list[dict] = []
        self.updated: list[tuple[int, dict]] = []

    def find_by_sku(self, sku: str):
        return self.existing.get(sku)

    def create_product(self, payload, image_path=None):
        if payload.get("sku", "") in self.fail_skus:
            raise WooCommerceError("fallo remoto")
        self.created.append(payload)
        return {"id": 100 + len(self.created)}

    def update_product(self, product_id, payload, image_path=None):
        self.updated.append((product_id, payload))
        return {"id": product_id}


def valid_product(sku: str, row: int | None = None):
    return validate_product(ProductInput({"name": f"Producto {sku}", "sku": sku, "regular_price": "12,50", "categories": "General", "height": "10"}, row_number=row), required_fields=("name", "sku", "regular_price", "categories", "height"))


def test_product_service_creates_and_resolves_duplicates() -> None:
    client = FakeClient({"OLD": {"id": 8}})
    service = ProductUploadService(lambda: client)
    created = service.upload(valid_product("NEW").product, "draft")
    assert created.outcome == "created"
    assert client.created[0]["type"] == "simple"
    conflict = service.find_conflict(valid_product("OLD").product)
    assert conflict and conflict.existing_product["id"] == 8
    skipped = service.upload(valid_product("OLD").product, "draft", DuplicateAction.SKIP, conflict.existing_product)
    assert skipped.outcome == "skipped"
    updated = service.upload(valid_product("OLD").product, "publish", DuplicateAction.UPDATE, conflict.existing_product)
    assert updated.outcome == "updated"
    assert client.updated[0][0] == 8


def test_product_service_requires_a_decision_for_existing_sku() -> None:
    service = ProductUploadService(lambda: FakeClient({"OLD": {"id": 8}}))
    with pytest.raises(ValueError, match="decidir"):
        service.upload(valid_product("OLD").product, "draft")


def test_product_service_creates_a_product_without_sku() -> None:
    client = FakeClient()
    product = validate_product(
        ProductInput({"name": "Producto sin referencia", "regular_price": "10", "categories": "General"}),
        required_fields=("name", "regular_price", "categories"),
    ).product

    result = ProductUploadService(lambda: client).upload(product, "draft")

    assert result.outcome == "created"
    assert "sku" not in client.created[0]


def test_product_service_returns_remote_errors_as_a_typed_result() -> None:
    service = ProductUploadService(lambda: FakeClient(fail_skus={"FAIL"}))
    result = service.upload(valid_product("FAIL").product, "draft")
    assert result.outcome == "failed"
    assert result.error == "fallo remoto"


def test_batch_service_handles_conflicts_failures_and_cancellation() -> None:
    client = FakeClient({"UPDATE": {"id": 4}, "SKIP": {"id": 5}}, {"FAIL"})
    service = BatchUploadService(lambda: client)
    results = [valid_product("CREATE", 2), valid_product("UPDATE", 3), valid_product("SKIP", 4), valid_product("FAIL", 5)]
    conflicts = service.find_conflicts(results)
    assert set(conflicts) == {3, 4}
    result = service.upload(results, "draft", {3: DuplicateAction.UPDATE}, conflicts)
    assert result.counts == {"created": 1, "updated": 1, "skipped": 1, "failed": 1}
    assert "Fila 5: fallo remoto" in result.failures
    stopped = service.upload(results, "draft", {}, conflicts, is_cancelled=lambda: True)
    assert stopped.cancelled is True
    assert stopped.rows == []


def test_batch_service_rejects_invalid_products_before_calling_client() -> None:
    client = FakeClient()
    invalid = validate_product(ProductInput({"sku": "X"}), required_fields=("name",))
    with pytest.raises(ValueError, match="no válidos"):
        BatchUploadService(lambda: client).upload([invalid], "draft", {}, {})
    assert client.created == []


def test_batch_service_sends_shield_location_taxonomies() -> None:
    client = FakeClient()
    shield = validate_product(ProductInput({
        "name": "Escudo de Sevilla",
        "sku": "ESC-1",
        "regular_price": "20",
        "categories": "Escudos",
        "ebdlt_pais": "españa",
        "ebdlt_region": "andalucía",
        "ebdlt_ciudad": "sevilla",
    }, row_number=2))

    result = BatchUploadService(lambda: client).upload([shield], "draft", {}, {})

    assert result.counts["created"] == 1
    assert client.created[0]["ebdlt_pais"] == ["España"]
    assert client.created[0]["ebdlt_region"] == ["Andalucía"]
    assert client.created[0]["ebdlt_ciudad"] == ["Sevilla"]


def test_batch_report_uses_historical_name_and_utf8_bom(tmp_path: Path) -> None:
    client = FakeClient({"SKIP": {"id": 2}})
    results = [valid_product("CREATE", 2), valid_product("SKIP", 3)]
    service = BatchUploadService(lambda: client)
    report = write_batch_report(service.upload(results, "draft", {}, service.find_conflicts(results)), tmp_path)
    assert report.name == "resultado_subida_lote.csv"
    data = report.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    assert "creado" in data.decode("utf-8-sig")
    assert "omitido" in data.decode("utf-8-sig")
