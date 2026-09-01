from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ..models import FIELD_LABELS, ProductInput, capitalize_initial, is_shield_category, validate_product
from ..services.uploads import DuplicateAction, ProductUploadService
from .components import acknowledgement_dialog, modern_dropdown, modern_text_field, primary_button, section
from .theme import PURPLE, WHITE

if TYPE_CHECKING:
    from ..app_controller import AppController


REQUIRED_FIELDS = ("name", "regular_price", "categories")
IN_STOCK = "instock"
ON_BACKORDER = "onbackorder"


def inventory_values(availability: str, quantity: str) -> dict[str, str]:
    if availability == IN_STOCK:
        return {"manage_stock": "yes", "stock_status": IN_STOCK, "stock_quantity": quantity}
    return {"manage_stock": "no", "stock_status": ON_BACKORDER, "stock_quantity": ""}


def build_single_product_view(app: AppController) -> ft.Control:
    fields = {
        "name": modern_text_field("Nombre *", "Ej.: Bandurria artesanal", ft.Icons.INVENTORY_2_OUTLINED),
        "sku": modern_text_field("SKU", "Opcional. Ej.: BAND-001", ft.Icons.SELL_OUTLINED),
        "regular_price": modern_text_field("Precio *", "Ej.: 24,95", ft.Icons.EURO_OUTLINED),
        "sale_price": modern_text_field("Precio rebajado", "Ej.: 19,95", ft.Icons.LOCAL_OFFER_OUTLINED),
        "stock_quantity": modern_text_field("Cantidad *", "Ej.: 12", ft.Icons.WAREHOUSE_OUTLINED, disabled=True),
        "categories": modern_dropdown(label="Categoría *", hint_text="Elige una categoría", prefix_icon=ft.Icons.CATEGORY_OUTLINED, options=[ft.dropdown.Option(category) for category in app.settings.categories]),
        "ebdlt_pais": modern_text_field("País", "Ej.: España", ft.Icons.PUBLIC),
        "ebdlt_region": modern_text_field("Comunidad o estado", "Ej.: Andalucía", ft.Icons.MAP_OUTLINED),
        "ebdlt_ciudad": modern_text_field("Ciudad", "Ej.: Sevilla", ft.Icons.LOCATION_ON_OUTLINED),
        "tags": modern_text_field("Etiquetas (separadas por comas)", "Ej.: tuna, instrumento, madera", ft.Icons.LABEL_OUTLINED),
        "weight": modern_text_field("Peso [kg]", "Ej.: 0,85", ft.Icons.SCALE_OUTLINED),
        "length": modern_text_field("Largo [cm]", "Ej.: 65", ft.Icons.STRAIGHTEN_OUTLINED),
        "width": modern_text_field("Ancho [cm]", "Ej.: 25", ft.Icons.STRAIGHTEN_OUTLINED),
        "height": modern_text_field("Alto [cm]", "Ej.: 12", ft.Icons.STRAIGHTEN_OUTLINED),
        "description": modern_text_field("Descripción", "Cuenta qué hace especial a este producto…", ft.Icons.DESCRIPTION_OUTLINED, multiline=True, min_lines=2),
        "short_description": modern_text_field("Descripción corta", "Resumen breve para la ficha", ft.Icons.SHORT_TEXT, multiline=True, min_lines=2),
    }
    image_path = {"value": ""}
    image_text = ft.Text("No se ha seleccionado ninguna imagen.")
    image_preview = ft.Image(width=120, height=120, fit=ft.ImageFit.CONTAIN, visible=False)
    featured = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="yes", label="★ Sí"),
            ft.Radio(value="no", label="No"),
        ]),
        value="no",
    )
    product_status = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="draft", label="Guardar como borrador"),
            ft.Radio(value="publish", label="Publicar ahora"),
        ]),
        value=app.settings.default_status,
    )
    featured_control = ft.Column([
        ft.Text("Producto destacado", weight=ft.FontWeight.BOLD, color=PURPLE),
        featured,
    ], spacing=2)
    publication_control = ft.Column([
        ft.Text("Publicación", weight=ft.FontWeight.BOLD, color=PURPLE),
        product_status,
    ], spacing=2)
    availability = ft.RadioGroup(
        content=ft.Column([
            ft.Row([
                ft.Radio(value=ON_BACKORDER, label="Bajo pedido"),
                ft.Text("No se controlará una cantidad concreta.", color="#665B5E"),
            ]),
            ft.Row([
                ft.Radio(value=IN_STOCK, label="En stock"),
                ft.Container(fields["stock_quantity"], width=220),
            ]),
        ], spacing=8),
        value=ON_BACKORDER,
    )
    service = ProductUploadService(app.create_client)

    def select_availability(event: ft.ControlEvent) -> None:
        in_stock = event.control.value == IN_STOCK
        fields["stock_quantity"].disabled = not in_stock
        if not in_stock:
            fields["stock_quantity"].value = ""
        fields["stock_quantity"].update()

    availability.on_change = select_availability

    def capitalize_location(event: ft.ControlEvent) -> None:
        event.control.value = capitalize_initial(event.control.value)
        event.control.update()

    for key in ("ebdlt_pais", "ebdlt_region", "ebdlt_ciudad"):
        fields[key].on_blur = capitalize_location

    location_fields = ft.ResponsiveRow(
        [ft.Container(fields[key], col={"sm": 12, "md": 4}) for key in ("ebdlt_pais", "ebdlt_region", "ebdlt_ciudad")],
        visible=False,
    )

    def show_location_fields(event: ft.ControlEvent) -> None:
        location_fields.visible = is_shield_category(event.control.value)
        if not location_fields.visible:
            for key in ("ebdlt_pais", "ebdlt_region", "ebdlt_ciudad"):
                fields[key].value = ""
        location_fields.update()

    fields["categories"].on_change = show_location_fields

    def selected(event: ft.FilePickerResultEvent) -> None:
        if event.files:
            image_path["value"] = event.files[0].path
            image_text.value = event.files[0].path
            image_preview.src = event.files[0].path
            image_preview.visible = True
            app.page.update()

    app.single_image_picker.on_result = selected

    def product_from_fields() -> ProductInput:
        values = {key: control.value or "" for key, control in fields.items()}
        values["featured"] = featured.value or "no"
        values.update(inventory_values(availability.value or ON_BACKORDER, fields["stock_quantity"].value or ""))
        values["catalog_visibility"] = "visible"
        return ProductInput(values, Path(image_path["value"]) if image_path["value"] else None)

    def show_result(success: bool, message: str) -> None:
        app.open_dialog(acknowledgement_dialog("Producto subido correctamente" if success else "No se pudo subir el producto", message, app.close_dialog, error=not success))

    def submit(action: DuplicateAction | None = None, existing: dict | None = None, confirmed: bool = False) -> None:
        required_fields = REQUIRED_FIELDS + (("stock_quantity",) if availability.value == IN_STOCK else ())
        validation = validate_product(product_from_fields(), required_fields=required_fields)
        quantity = validation.product.values.get("stock_quantity", "")
        if availability.value == IN_STOCK and quantity.replace("-", "", 1).isdigit() and int(quantity) <= 0:
            validation.errors.append("La cantidad debe ser mayor que cero.")
        if not validation.valid:
            app.open_dialog(acknowledgement_dialog("Faltan campos obligatorios", " ".join(validation.errors), app.close_dialog, error=True))
            return
        product = validation.product
        if not confirmed:
            hidden_summary_fields = {"catalog_visibility", "featured", "manage_stock", "stock_status"}
            summary = [ft.Text(f"{FIELD_LABELS[key]}: {value}") for key, value in product.values.items() if key not in hidden_summary_fields]
            summary.append(ft.Text(f"Producto destacado: {'Sí' if featured.value == 'yes' else 'No'}"))
            summary.append(ft.Text(f"Disponibilidad: {'En stock' if availability.value == IN_STOCK else 'Bajo pedido'}"))
            if product.image_path:
                summary.append(ft.Text(f"Imagen: {product.image_path.name}"))
            summary.append(ft.Text(f"Publicación: {'Publicado' if product_status.value == 'publish' else 'Borrador'}"))
            app.open_dialog(ft.AlertDialog(modal=True, title=ft.Text("Revise el producto antes de subirlo", color=PURPLE), content=ft.Container(ft.Column(summary, tight=True, scroll=ft.ScrollMode.AUTO), width=560, height=min(420, 48 * len(summary))), actions=[ft.TextButton("Cancelar", on_click=lambda _: app.close_dialog()), ft.ElevatedButton("Confirmar subida", icon=ft.Icons.UPLOAD, on_click=lambda _: (app.close_dialog(), submit(confirmed=True)))]))
            return
        app.begin_upload("Comprobando el SKU y preparando la subida…")
        try:
            conflict_info = None if existing is not None else service.find_conflict(product)
            conflict = existing if existing is not None else (conflict_info.existing_product if conflict_info else None)
            if conflict and action is None:
                app.open_dialog(ft.AlertDialog(modal=True, title=ft.Text("SKU existente"), content=ft.Text(f"El SKU pertenece al producto #{conflict['id']}."), actions=[ft.TextButton("Omitir", on_click=lambda _: (app.close_dialog(), submit(DuplicateAction.SKIP, conflict, True))), ft.TextButton("Actualizar", on_click=lambda _: (app.close_dialog(), submit(DuplicateAction.UPDATE, conflict, True))), ft.TextButton("Cancelar", on_click=lambda _: app.close_dialog())]))
                return
            app.begin_upload("Subiendo el producto. No cierre ni utilice la aplicación hasta que termine la carga.")
            result = service.upload(product, product_status.value or "draft", action, conflict, lookup_existing=False)
            if result.outcome == "skipped":
                message = "No se ha subido el producto porque ya existe un producto con ese SKU."
                app.notify("Producto omitido.")
                show_result(False, message)
                return
            if result.outcome == "failed":
                app.notify(result.error, True)
                show_result(False, result.error)
                return
            remote_product = result.remote_product
            if remote_product is None:
                raise RuntimeError("La subida terminó sin devolver los datos del producto.")
            message = f"Producto #{remote_product['id']} {'actualizado' if result.outcome == 'updated' else 'creado'} correctamente."
            app.notify(message)
            show_result(True, message)
        except Exception as exc:
            app.notify(str(exc), True)
            show_result(False, str(exc))

    return ft.Container(content=ft.Column([
        ft.Text("Todos los campos marcados con asterisco (*) son obligatorios.", color="#665B5E"),
        section("Producto", "Datos principales, contenido y presencia en el catálogo.", [ft.ResponsiveRow([ft.Container(fields["name"], col={"sm": 12, "md": 8}), ft.Container(fields["sku"], col={"sm": 12, "md": 4})]), fields["description"], fields["short_description"], ft.ResponsiveRow([ft.Container(featured_control, col={"sm": 12, "md": 5}), ft.Container(publication_control, col={"sm": 12, "md": 7})]), ft.Row([primary_button("Elegir imagen", lambda _: app.single_image_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["jpg", "jpeg", "png", "webp"]), ft.Icons.IMAGE_OUTLINED), image_text, image_preview])]),
        section("Precio", "Define el precio habitual y, si procede, una oferta.", [ft.ResponsiveRow([ft.Container(fields["regular_price"], col={"sm": 12, "md": 6}), ft.Container(fields["sale_price"], col={"sm": 12, "md": 6})])]),
        section("Organización", "Elige la categoría. Al seleccionar Escudos podrás indicar su ubicación respetando la mayúscula inicial.", [fields["categories"], location_fields, fields["tags"]]),
        section("Inventario", "Selecciona una única forma de disponibilidad. La cantidad solo se puede editar para productos en stock.", [availability]),
        section("Envío", "Indica el peso y las dimensiones del producto.", [ft.Row([
            ft.Container(fields["weight"], expand=1),
            ft.Container(ft.VerticalDivider(width=24, thickness=1, color="#C8BCC0"), height=56),
            ft.Container(fields["length"], expand=1),
            ft.Container(fields["width"], expand=1),
            ft.Container(fields["height"], expand=1),
        ], spacing=10)]),
        ft.Row([primary_button("Subir producto", lambda _: submit(), ft.Icons.UPLOAD, height=52)], alignment=ft.MainAxisAlignment.END),
    ], spacing=20, scroll=ft.ScrollMode.AUTO), padding=10)
