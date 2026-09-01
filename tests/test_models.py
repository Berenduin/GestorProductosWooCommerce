from pathlib import Path

from woo_uploader.models import ProductInput, WOO_FIELDS, capitalize_initial, to_woo_payload, validate_product


def test_product_validation_and_payload(tmp_path: Path) -> None:
    image = tmp_path / "SKU-1.JPG"
    image.touch()
    product = ProductInput({"name": "Guitarra", "sku": "SKU-1", "regular_price": "12,50", "stock_quantity": "4", "categories": "Cuerda", "length": "10"}, image)
    result = validate_product(product)
    assert result.valid
    payload = to_woo_payload(result.product, "draft")
    assert payload["name"] == "Guitarra"
    assert payload["manage_stock"] is True
    assert payload["stock_quantity"] == 4
    assert payload["categories"] == [{"name": "Cuerda"}]


def test_invalid_numbers_are_reported() -> None:
    result = validate_product(ProductInput({"name": "Producto", "sku": "SKU-1", "regular_price": "mucho", "stock_quantity": "3.2", "categories": "General"}))
    assert not result.valid
    assert len(result.errors) == 2


def test_single_product_fields_do_not_require_height() -> None:
    result = validate_product(
        ProductInput({"name": "Producto", "sku": "SKU-1", "regular_price": "10", "categories": "General"}),
        required_fields=("name", "sku", "regular_price", "categories"),
    )
    assert result.valid


def test_single_product_fields_do_not_require_sku() -> None:
    result = validate_product(
        ProductInput({"name": "Producto", "regular_price": "10", "categories": "General"}),
        required_fields=("name", "regular_price", "categories"),
    )

    assert result.valid


def test_product_rejects_multiple_categories() -> None:
    result = validate_product(ProductInput({"name": "Producto", "categories": "Cuerda, Oferta"}))
    assert "La categoría debe contener un único valor." in result.errors


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
    assert result.errors == ["Falta sku.", "Falta precio.", "Falta categoría."]


def test_location_taxonomies_are_capitalized_and_serialized() -> None:
    result = validate_product(ProductInput({
        "name": "Escudo de prueba",
        "categories": "Escudos",
        "ebdlt_pais": " españa ",
        "ebdlt_region": "comunidad de madrid",
        "ebdlt_ciudad": "álcala de Henares",
    }))

    assert result.valid
    assert result.product.values["ebdlt_pais"] == "España"
    assert result.product.values["ebdlt_region"] == "Comunidad de madrid"
    assert result.product.values["ebdlt_ciudad"] == "Álcala de Henares"
    payload = to_woo_payload(result.product, "draft")
    assert payload["ebdlt_pais"] == ["España"]
    assert payload["ebdlt_region"] == ["Comunidad de madrid"]
    assert payload["ebdlt_ciudad"] == ["Álcala de Henares"]


def test_location_taxonomies_are_available_to_the_batch_importer() -> None:
    assert "ebdlt_pais" in WOO_FIELDS
    assert "ebdlt_region" in WOO_FIELDS
    assert "ebdlt_ciudad" in WOO_FIELDS


def test_location_taxonomies_are_ignored_outside_the_shields_category() -> None:
    result = validate_product(ProductInput({
        "name": "Bandurria",
        "categories": "Instrumentos",
        "ebdlt_pais": "España",
        "ebdlt_region": "Andalucía",
        "ebdlt_ciudad": "Sevilla",
    }))

    assert result.valid
    assert not set(("ebdlt_pais", "ebdlt_region", "ebdlt_ciudad")) & result.product.values.keys()
    payload = to_woo_payload(result.product, "draft")
    assert "ebdlt_pais" not in payload
    assert "ebdlt_region" not in payload
    assert "ebdlt_ciudad" not in payload


def test_capitalize_initial_handles_empty_and_accented_values() -> None:
    assert capitalize_initial("") == ""
    assert capitalize_initial("  ávila") == "Ávila"
