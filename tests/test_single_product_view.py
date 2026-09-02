import flet as ft

from woo_uploader.ui.single_product_view import IN_STOCK, ON_BACKORDER, inventory_values, reset_product_form


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


class Page:
    def __init__(self) -> None:
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


def test_successful_upload_resets_the_product_form_state() -> None:
    page = Page()
    fields = {
        "name": ft.TextField(value="Bandurria"),
        "stock_quantity": ft.TextField(value="12", disabled=False),
        "categories": ft.Dropdown(value="Instrumentos"),
    }
    featured = ft.RadioGroup(content=ft.Row(), value="yes")
    product_status = ft.RadioGroup(content=ft.Row(), value="publish")
    availability = ft.RadioGroup(content=ft.Row(), value=IN_STOCK)
    image_path = {"value": "/tmp/bandurria.png"}
    image_text = ft.Text("/tmp/bandurria.png")
    image_preview = ft.Image(src="/tmp/bandurria.png", visible=True)
    location_fields = ft.ResponsiveRow([], visible=True)

    reset_product_form(
        page,
        fields,
        featured,
        product_status,
        availability,
        image_path,
        image_text,
        image_preview,
        location_fields,
        "draft",
    )

    assert fields["name"].value == ""
    assert fields["categories"].value == ""
    assert fields["stock_quantity"].value == ""
    assert fields["stock_quantity"].disabled is True
    assert featured.value == "no"
    assert product_status.value == "draft"
    assert availability.value == ON_BACKORDER
    assert image_path["value"] == ""
    assert image_text.value == "No se ha seleccionado ninguna imagen."
    assert image_preview.src == ""
    assert image_preview.visible is False
    assert location_fields.visible is False
    assert page.updates == 1
