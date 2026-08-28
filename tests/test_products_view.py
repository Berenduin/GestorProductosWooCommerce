from woo_uploader.ui.products_view import _dimensions, _names, _products_by_category, _published_date, _stock_status, _taxonomy_values


def test_groups_products_by_category_and_keeps_multi_category_products() -> None:
    products = [
        {"id": 1, "categories": [{"name": "Instrumentos"}, {"name": "Cuerda"}]},
        {"id": 2, "categories": [{"name": "Cuerda"}]},
        {"id": 3, "categories": []},
    ]

    grouped = _products_by_category(products)

    assert list(grouped) == ["Cuerda", "Instrumentos", "Sin categoría"]
    assert [product["id"] for product in grouped["Cuerda"]] == [1, 2]
    assert [product["id"] for product in grouped["Instrumentos"]] == [1]
    assert [product["id"] for product in grouped["Sin categoría"]] == [3]


def test_groups_category_names_without_case_sensitive_duplicates() -> None:
    grouped = _products_by_category([
        {"id": 1, "categories": [{"name": "Cuerda"}, {"name": "cuerda"}]},
        {"id": 2, "categories": [{"name": "CUERDA"}]},
    ])

    assert list(grouped) == ["Cuerda"]
    assert [product["id"] for product in grouped["Cuerda"]] == [1, 2]


def test_formats_extended_product_data_for_the_table() -> None:
    product = {
        "stock_status": "onbackorder",
        "tags": [{"name": "Tuna"}, {"name": "Escudo"}],
        "dimensions": {"length": "10", "width": "5", "height": "2"},
        "date_created": "2026-08-28T10:30:00",
    }

    assert _stock_status(product) == "Bajo pedido"
    assert _names(product, "tags") == "Tuna, Escudo"
    assert _dimensions(product) == "10 × 5 × 2"
    assert _published_date(product) == "2026-08-28"


def test_formats_custom_location_taxonomies_from_the_api() -> None:
    product = {
        "ebdlt_pais": ["España"],
        "ebdlt_region": [{"name": "Comunidad de Madrid"}],
        "ebdlt_ciudad": [],
    }

    assert _taxonomy_values(product, "ebdlt_pais") == "España"
    assert _taxonomy_values(product, "ebdlt_region") == "Comunidad de Madrid"
    assert _taxonomy_values(product, "ebdlt_ciudad") == "—"
