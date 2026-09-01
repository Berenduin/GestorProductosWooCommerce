from woo_uploader.ui.single_product_view import IN_STOCK, ON_BACKORDER, inventory_values


def test_in_stock_inventory_controls_quantity() -> None:
    assert inventory_values(IN_STOCK, "12") == {
        "manage_stock": "yes",
        "stock_status": "instock",
        "stock_quantity": "12",
    }


def test_backorder_inventory_clears_and_disables_quantity_semantically() -> None:
    assert inventory_values(ON_BACKORDER, "12") == {
        "manage_stock": "no",
        "stock_status": "onbackorder",
        "stock_quantity": "",
    }
