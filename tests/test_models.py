from pathlib import Path

from woo_uploader.models import ProductInput, to_woo_payload, validate_product


def test_product_validation_and_payload(tmp_path: Path) -> None:
    image = tmp_path / "SKU-1.JPG"
    image.touch()
    product = ProductInput({"name": "Guitarra", "sku": "SKU-1", "regular_price": "12,50", "stock_quantity": "4", "categories": "Cuerda, Oferta", "length": "10"}, image)
    result = validate_product(product)
    assert result.valid
    payload = to_woo_payload(result.product, "draft")
    assert payload["name"] == "Guitarra"
    assert payload["manage_stock"] is True
    assert payload["stock_quantity"] == 4
    assert payload["categories"] == [{"name": "Cuerda"}, {"name": "Oferta"}]


def test_invalid_numbers_are_reported() -> None:
    result = validate_product(ProductInput({"name": "Producto", "sku": "SKU-1", "regular_price": "mucho", "stock_quantity": "3.2", "categories": "General"}))
    assert not result.valid
    assert len(result.errors) == 2


def test_optional_inventory_visibility_and_shipping_fields_are_serialized() -> None:
    product = ProductInput({
        "name": "Producto a medida",
        "catalog_visibility": "catalog",
        "featured": "sí",
        "stock_status": "onbackorder",
        "backorders": "notify",
        "low_stock_amount": "2",
        "sold_individually": "no",
        "shipping_class": "voluminoso",
        "tax_status": "taxable",
        "tax_class": "reduced-rate",
        "virtual": "no",
    })

    result = validate_product(product)

    assert result.valid
    payload = to_woo_payload(result.product, "draft")
    assert payload["catalog_visibility"] == "catalog"
    assert payload["featured"] is True
    assert payload["stock_status"] == "onbackorder"
    assert payload["backorders"] == "notify"
    assert payload["low_stock_amount"] == 2
    assert payload["shipping_class"] == "voluminoso"
    assert payload["tax_status"] == "taxable"
    assert payload["virtual"] is False


def test_required_product_fields_are_reported() -> None:
    result = validate_product(
        ProductInput({"name": "Producto"}),
        required_fields=("name", "sku", "regular_price", "categories"),
    )
    assert not result.valid
    assert result.errors == ["Falta sku.", "Falta precio.", "Falta categorías (separadas por coma)."]
