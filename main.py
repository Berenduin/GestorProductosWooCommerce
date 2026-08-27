from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import flet as ft

from woo_uploader.config import Settings, SettingsStore
from woo_uploader.excel_import import Spreadsheet, build_products, infer_mapping, read_spreadsheet
from woo_uploader.models import FIELD_LABELS, ProductInput, to_woo_payload, validate_product
from woo_uploader.woocommerce import WooCommerceClient, WooCommerceError

PURPLE = "#623642"
GOLD = "#FFBA00"
LIGHT_GRAY = "#F4F4F4"
WHITE = "#FFFFFF"
BLACK = "#1F1F1F"


@dataclass
class AppState:
    sheet: Spreadsheet | None = None
    image_directory: str = ""
    cancelled: bool = False


def main(page: ft.Page) -> None:
    page.title = "Subidor WooCommerce"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = LIGHT_GRAY
    page.theme = ft.Theme(
        use_material3=True,
        scaffold_bgcolor=LIGHT_GRAY,
        card_color=WHITE,
        divider_color=GOLD,
        color_scheme=ft.ColorScheme(
            primary=PURPLE,
            on_primary=WHITE,
            primary_container="#E9DDE1",
            on_primary_container=PURPLE,
            secondary=GOLD,
            on_secondary=BLACK,
            secondary_container="#FFF0C7",
            on_secondary_container=BLACK,
            surface=WHITE,
            on_surface=BLACK,
            background=LIGHT_GRAY,
            on_background=BLACK,
            outline="#BDB5B7",
        ),
    )
    page.padding = 20
    page.window.min_width = 920
    page.window.min_height = 700
    page.window.maximized = True
    store = SettingsStore()
    settings = store.load()
    state = AppState()
    active_dialog: dict[str, ft.AlertDialog | None] = {"control": None}
    status = ft.Text()
    content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

    def modern_text_field(label: str | None, hint_text: str = "", icon: Any = None, **kwargs: Any) -> ft.TextField:
        return ft.TextField(
            label=label,
            hint_text=hint_text,
            prefix_icon=icon,
            bgcolor="#FAF8F9",
            border_color="#D8CDD0",
            focused_border_color=GOLD,
            focused_border_width=2,
            border_radius=12,
            hint_style=ft.TextStyle(color="#887C80", italic=True),
            **kwargs,
        )

    def modern_dropdown(**kwargs: Any) -> ft.Dropdown:
        return ft.Dropdown(
            bgcolor="#FAF8F9",
            border_color="#D8CDD0",
            focused_border_color=GOLD,
            focused_border_width=2,
            border_radius=12,
            hint_style=ft.TextStyle(color="#887C80", italic=True),
            **kwargs,
        )

    def notify(message: str, error: bool = False) -> None:
        status.value = message
        status.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
        page.update()

    def open_dialog(dialog: ft.AlertDialog) -> None:
        close_dialog()
        active_dialog["control"] = dialog
        page.open(dialog)

    def close_dialog() -> None:
        dialog = active_dialog["control"]
        if dialog:
            page.close(dialog)
            active_dialog["control"] = None

    def credentials() -> tuple[str, str, str]:
        return store.credentials()

    def client() -> WooCommerceClient:
        key, secret, wp_password = credentials()
        if not settings.store_url or not key or not secret:
            raise WooCommerceError("Configure la URL y las claves API antes de subir productos.")
        return WooCommerceClient(settings.store_url, key, secret, settings.wordpress_user, wp_password)

    def set_view(view: str) -> None:
        content.controls.clear()
        if view == "settings":
            render_settings()
        else:
            render_upload()
        page.update()

    def render_settings() -> None:
        nonlocal settings
        key, secret, wp_password = credentials()
        url = modern_text_field("URL de la tienda", "https://mitienda.es", ft.Icons.LINK_OUTLINED, value=settings.store_url)
        consumer_key = modern_text_field("Consumer Key", "ck_…", ft.Icons.KEY_OUTLINED, value=key, password=True, can_reveal_password=True)
        consumer_secret = modern_text_field("Consumer Secret", "cs_…", ft.Icons.KEY_OUTLINED, value=secret, password=True, can_reveal_password=True)
        wp_user = modern_text_field("Usuario WordPress (opcional, para imágenes locales)", "Ej.: administrador", ft.Icons.PERSON_OUTLINE, value=settings.wordpress_user)
        wp_pass = modern_text_field("Contraseña de aplicación WordPress (opcional)", "xxxx xxxx xxxx xxxx", ft.Icons.LOCK_OUTLINE, value=wp_password, password=True, can_reveal_password=True)
        default_status = modern_dropdown(label="Estado predeterminado", value=settings.default_status, prefix_icon=ft.Icons.VISIBILITY_OUTLINED, options=[ft.dropdown.Option("draft", "Borrador"), ft.dropdown.Option("publish", "Publicado")])
        category_list = ft.Column(spacing=4)
        category_inputs: list[ft.TextField] = []
        new_category = modern_text_field("Nueva categoría", "Ej.: Accesorios", ft.Icons.ADD_CIRCLE_OUTLINE, expand=True)

        def refresh_category_colors() -> None:
            for index, control in enumerate(category_inputs):
                control.bgcolor = WHITE if index % 2 == 0 else "#FBF7F8"

        def add_category(name: str) -> None:
            category_input = modern_text_field(None, "Nombre de categoría", value=name, dense=True, expand=True)
            row = ft.Row(spacing=6)

            def remove_category(_: ft.ControlEvent) -> None:
                category_inputs.remove(category_input)
                category_list.controls.remove(row)
                refresh_category_colors()
                save_categories()
                page.update()

            category_input.on_blur = lambda _: save_categories()
            category_inputs.append(category_input)
            row.controls.extend([
                category_input,
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Eliminar categoría", on_click=remove_category),
            ])
            category_list.controls.append(row)
            refresh_category_colors()

        for category in settings.categories:
            add_category(category)

        def add_new_category(_: ft.ControlEvent) -> None:
            name = (new_category.value or "").strip()
            if not name:
                return
            if name.casefold() in {(control.value or "").strip().casefold() for control in category_inputs}:
                notify("Esa categoría ya existe.", True)
                return
            add_category(name)
            new_category.value = ""
            save_categories()
            page.update()

        def configured_categories() -> list[str]:
            result: list[str] = []
            seen: set[str] = set()
            for control in category_inputs:
                name = (control.value or "").strip()
                if name and name.casefold() not in seen:
                    result.append(name)
                    seen.add(name.casefold())
            return result

        def save_categories() -> None:
            nonlocal settings
            settings = Settings(settings.store_url, settings.wordpress_user, settings.default_status, configured_categories())
            try:
                store.save_settings(settings)
                notify("Categorías actualizadas.")
            except Exception as exc:
                notify(f"No se pudieron guardar las categorías: {exc}", True)

        def save_connection(_: ft.ControlEvent) -> None:
            nonlocal settings
            store_url = (url.value or "").strip().rstrip("/").removesuffix("/wp-json")
            settings = Settings(
                store_url,
                (wp_user.value or "").strip(),
                default_status.value or "draft",
                settings.categories,
            )
            try:
                store.save(
                    settings,
                    (consumer_key.value or "").strip(),
                    (consumer_secret.value or "").strip(),
                    (wp_pass.value or "").strip(),
                )
                notify("Conexión guardada. Las claves se han enviado al llavero del sistema.")
            except Exception as exc:
                notify(f"No se pudo guardar en el llavero: {exc}", True)

        def test(_: ft.ControlEvent) -> None:
            save_connection(_)
            try:
                notify(client().test_connection())
            except WooCommerceError as exc:
                notify(str(exc), True)

        categories_tab = ft.Column([
            ft.Text("Categorías de productos", size=20, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Text("Edite los nombres, elimine categorías o añada nuevas."),
            ft.Row([new_category, ft.ElevatedButton("Añadir categoría", icon=ft.Icons.ADD, on_click=add_new_category)]),
            category_list,
        ], scroll=ft.ScrollMode.AUTO)
        connection_tab = ft.Column([
            ft.Text("Conexión con WooCommerce", size=20, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Text("Las claves se almacenan en el llavero del sistema, no en el archivo de configuración."),
            url,
            consumer_key,
            consumer_secret,
            wp_user,
            wp_pass,
            default_status,
            ft.Row([ft.ElevatedButton("Guardar conexión", on_click=save_connection), ft.OutlinedButton("Probar conexión", on_click=test)]),
        ], scroll=ft.ScrollMode.AUTO)
        content.controls.extend([
            ft.Text("Configuración", size=26, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Tabs(selected_index=0, expand=True, tabs=[
                ft.Tab(text="Categorías", content=categories_tab),
                ft.Tab(text="Conexión", content=connection_tab),
            ]),
            status,
        ])

    def render_upload() -> None:
        tabs = ft.Tabs(selected_index=0, animation_duration=150, expand=1, tabs=[
            ft.Tab(text="Un producto", content=single_product_view()),
            ft.Tab(text="Subir por lote", content=bulk_import_view()),
        ])
        content.controls.extend([ft.Text("Subir productos", size=26, weight=ft.FontWeight.BOLD, color=PURPLE), tabs, status])

    def single_product_view() -> ft.Control:
        fields = {
            "name": modern_text_field("Nombre *", "Ej.: Bandurria artesanal", ft.Icons.INVENTORY_2_OUTLINED),
            "sku": modern_text_field("SKU *", "Ej.: BAND-001", ft.Icons.SELL_OUTLINED),
            "featured": modern_dropdown(label="Producto destacado", value="no", prefix_icon=ft.Icons.STAR_OUTLINE, options=[
                ft.dropdown.Option("no", "No"), ft.dropdown.Option("yes", "Sí"),
            ]),
            "regular_price": modern_text_field("Precio *", "Ej.: 24,95", ft.Icons.EURO_OUTLINED),
            "sale_price": modern_text_field("Precio rebajado", "Ej.: 19,95", ft.Icons.LOCAL_OFFER_OUTLINED),
            "manage_stock": modern_dropdown(label="Gestionar cantidad de stock", value="yes", prefix_icon=ft.Icons.INVENTORY_OUTLINED, options=[
                ft.dropdown.Option("yes", "Sí"), ft.dropdown.Option("no", "No (productos bajo demanda)"),
            ]),
            "stock_quantity": modern_text_field("Stock", "Ej.: 12", ft.Icons.WAREHOUSE_OUTLINED),
            "stock_status": modern_dropdown(label="Estado de existencias", value="instock", prefix_icon=ft.Icons.INVENTORY_2_OUTLINED, options=[
                ft.dropdown.Option("instock", "En stock"),
                ft.dropdown.Option("onbackorder", "Bajo pedido / a medida"),
            ]),
            "categories": modern_dropdown(label="Categoría *", hint_text="Elige una categoría", prefix_icon=ft.Icons.CATEGORY_OUTLINED, options=[ft.dropdown.Option(category) for category in settings.categories]),
            "tags": modern_text_field("Etiquetas (separadas por comas)", "Ej.: tuna, instrumento, madera", ft.Icons.LABEL_OUTLINED),
            "weight": modern_text_field("Peso [kg]", "Ej.: 0,85", ft.Icons.SCALE_OUTLINED),
            "length": modern_text_field("Largo [cm]", "Ej.: 65", ft.Icons.STRAIGHTEN_OUTLINED),
            "width": modern_text_field("Ancho [cm]", "Ej.: 25", ft.Icons.STRAIGHTEN_OUTLINED),
            "height": modern_text_field("Alto [cm] *", "Ej.: 12", ft.Icons.STRAIGHTEN_OUTLINED),
            "description": modern_text_field("Descripción", "Cuenta qué hace especial a este producto…", ft.Icons.DESCRIPTION_OUTLINED, multiline=True, min_lines=2),
            "short_description": modern_text_field("Descripción corta", "Resumen breve para la ficha", ft.Icons.SHORT_TEXT, multiline=True, min_lines=2),
        }
        state_path = {"value": ""}
        image_text = ft.Text("No se ha seleccionado ninguna imagen.")
        image_preview = ft.Image(width=120, height=120, fit=ft.ImageFit.CONTAIN, visible=False)
        picker = ft.FilePicker()
        page.overlay.append(picker)

        def selected(event: ft.FilePickerResultEvent) -> None:
            if event.files:
                state_path["value"] = event.files[0].path
                image_text.value = event.files[0].path
                image_preview.src = event.files[0].path
                image_preview.visible = True
                page.update()
        picker.on_result = selected

        product_status = modern_dropdown(label="Publicación", value=settings.default_status, prefix_icon=ft.Icons.PUBLISH_OUTLINED, options=[ft.dropdown.Option("draft", "Guardar como borrador"), ft.dropdown.Option("publish", "Publicar ahora")])

        def upload_result(success: bool, message: str) -> None:
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Producto subido correctamente" if success else "No se pudo subir el producto",
                    color=PURPLE if success else ft.Colors.RED_700,
                ),
                content=ft.Text(message),
                actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close_dialog())],
            )
            open_dialog(dialog)

        def submit(action: str | None = None, existing: dict | None = None, confirmed: bool = False) -> None:
            values: dict[str, str] = {key: control.value or "" for key, control in fields.items()}
            values["catalog_visibility"] = "visible"
            required_labels = {
                "name": "Nombre",
                "sku": "SKU",
                "regular_price": "Precio",
                "categories": "Categoría",
                "height": "Alto",
            }
            missing = [label for key, label in required_labels.items() if not (values.get(key) or "").strip()]
            if missing:
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Faltan campos obligatorios", color=PURPLE),
                    content=ft.Column([
                        ft.Text("Complete los siguientes campos antes de subir el producto:"),
                        *[ft.Text(f"• {label}") for label in missing],
                    ], tight=True),
                    actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close_dialog())],
                )
                open_dialog(dialog)
                return
            product = ProductInput(values, Path(state_path["value"]) if state_path["value"] else None)
            result = validate_product(product, required_fields=("name", "sku", "regular_price", "categories", "height"))
            if not result.valid:
                notify(" ".join(result.errors), True); return
            if not confirmed:
                summary = [
                    ft.Text(f"{FIELD_LABELS[key]}: {value}")
                    for key, value in result.product.values.items()
                    if key != "catalog_visibility"
                ]
                if result.product.image_path:
                    summary.append(ft.Text(f"Imagen: {result.product.image_path.name}"))
                summary.append(ft.Text(f"Publicación: {'Publicado' if product_status.value == 'publish' else 'Borrador'}"))
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Revise el producto antes de subirlo", color=PURPLE),
                    content=ft.Container(ft.Column(summary, tight=True, scroll=ft.ScrollMode.AUTO), width=560, height=min(420, 48 * len(summary))),
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda _: close_dialog()),
                        ft.ElevatedButton("Confirmar subida", icon=ft.Icons.UPLOAD, on_click=lambda _: (close_dialog(), submit(confirmed=True))),
                    ],
                )
                open_dialog(dialog)
                return
            try:
                woo = client(); found = existing if existing is not None else woo.find_by_sku(values["sku"].strip())
                chosen = action or "ask"
                if found and chosen == "ask":
                    dialog = ft.AlertDialog(
                        modal=True, title=ft.Text("SKU existente"), content=ft.Text(f"El SKU pertenece al producto #{found['id']}."),
                        actions=[
                            ft.TextButton("Omitir", on_click=lambda _: (close_dialog(), notify("Producto omitido."))),
                            ft.TextButton("Actualizar", on_click=lambda _: (close_dialog(), submit("update", found, confirmed=True))),
                            ft.TextButton("Cancelar", on_click=lambda _: close_dialog()),
                        ],
                    ); open_dialog(dialog); return
                if found and chosen == "skip":
                    notify("Producto omitido.")
                    upload_result(False, "No se ha subido el producto porque ya existe un producto con ese SKU.")
                    return
                payload = to_woo_payload(result.product, product_status.value or "draft")
                response = woo.update_product(found["id"], payload, result.product.image_path) if found else woo.create_product(payload, result.product.image_path)
                message = f"Producto #{response['id']} {'actualizado' if found else 'creado'} correctamente."
                notify(message)
                upload_result(True, message)
            except WooCommerceError as exc:
                notify(str(exc), True)
                upload_result(False, str(exc))

        def section(title: str, hint: str, controls: list[ft.Control]) -> ft.Container:
            return ft.Container(
                content=ft.Column([ft.Text(title, size=19, weight=ft.FontWeight.BOLD, color=PURPLE), ft.Text(hint, color="#665B5E"), *controls], spacing=10),
                bgcolor="#FAF8F9",
                border_radius=12,
                padding=16,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color="#55000000", offset=ft.Offset(0, 2)),
            )

        return ft.Container(content=ft.Column([
            ft.Text("Todos los campos marcados con asterisco (*) son obligatorios.", color="#665B5E"),
            section("Producto", "Datos principales, contenido y presencia en el catálogo.", [
                ft.ResponsiveRow([
                    ft.Container(fields["name"], col={"sm": 12, "md": 8}),
                    ft.Container(fields["sku"], col={"sm": 12, "md": 4}),
                ]),
                fields["description"], fields["short_description"],
                ft.ResponsiveRow([
                    ft.Container(fields["featured"], col={"sm": 12, "md": 6}),
                    ft.Container(product_status, col={"sm": 12, "md": 6}),
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        "Elegir imagen",
                        icon=ft.Icons.IMAGE_OUTLINED,
                        color=WHITE,
                        style=ft.ButtonStyle(bgcolor=PURPLE),
                        on_click=lambda _: picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["jpg", "jpeg", "png", "webp"]),
                    ),
                    image_text,
                    image_preview,
                ]),
            ]),
            section("Precio", "Define el precio habitual y, si procede, una oferta.", [
                ft.ResponsiveRow([
                    ft.Container(fields["regular_price"], col={"sm": 12, "md": 6}),
                    ft.Container(fields["sale_price"], col={"sm": 12, "md": 6}),
                ]),
            ]),
            section("Inventario", "Controla existencias, productos bajo pedido y alertas.", [
                ft.ResponsiveRow([
                    ft.Container(fields["manage_stock"], col={"sm": 12, "md": 4}),
                    ft.Container(fields["stock_quantity"], col={"sm": 12, "md": 4}),
                    ft.Container(fields["stock_status"], col={"sm": 12, "md": 4}),
                ]),
            ]),
            section("Envío", "Indica el peso y las dimensiones del producto.", [
                ft.ResponsiveRow([
                    ft.Container(fields["weight"], col={"sm": 12}),
                ]),
                ft.ResponsiveRow([ft.Container(fields[key], col={"sm": 4}) for key in ("length", "width", "height")]),
            ]),
            section("Organización", "Clasifica el producto para facilitar su navegación y búsqueda.", [
                fields["categories"], fields["tags"],
            ]),
            ft.Row([
                ft.ElevatedButton(
                    "Subir producto",
                    icon=ft.Icons.UPLOAD,
                    height=52,
                    style=ft.ButtonStyle(bgcolor=PURPLE, color=WHITE),
                    on_click=lambda _: submit(),
                )
            ], alignment=ft.MainAxisAlignment.END),
        ], spacing=20, scroll=ft.ScrollMode.AUTO), padding=10)

    def bulk_import_view() -> ft.Control:
        file_label = ft.Text("Aún no has seleccionado el Excel del lote.")
        directory_label = ft.Text("Opcional: selecciona una carpeta si quieres asociar fotos.")
        preview_area = ft.Column()
        picker = ft.FilePicker()
        folder_picker = ft.FilePicker()
        page.overlay.extend([picker, folder_picker])
        image_column = modern_dropdown(label="Columna usada como nombre de foto (opcional)", hint_text="Selecciona una columna", prefix_icon=ft.Icons.IMAGE_OUTLINED)
        import_status = modern_dropdown(label="Estado de los productos del lote", value=settings.default_status, prefix_icon=ft.Icons.VISIBILITY_OUTLINED, options=[ft.dropdown.Option("draft", "Borrador"), ft.dropdown.Option("publish", "Publicado")])

        def image_notice() -> None:
            dialog = ft.AlertDialog(modal=True, title=ft.Text("Fotos del lote (opcional)"), content=ft.Text("Para asociar fotos, elige una carpeta y después selecciona la columna que contiene el nombre de cada archivo. Los nombres deben coincidir. Se aceptan JPG, JPEG, PNG y WEBP."), actions=[ft.TextButton("Entendido", on_click=lambda _: close_dialog())])
            open_dialog(dialog)

        def configure_excel() -> None:
            assert state.sheet
            image_column.options = [ft.dropdown.Option(header) for header in state.sheet.headers]
            image_column.value = next((header for header in state.sheet.headers if header.casefold() in {"image", "imagen", "foto"}), None)

        def select_excel(event: ft.FilePickerResultEvent) -> None:
            if not event.files: return
            try:
                state.sheet = read_spreadsheet(event.files[0].path)
                file_label.value = f"Lote seleccionado: {event.files[0].name} · {len(state.sheet.rows)} productos detectados."
                configure_excel()
                preview()
            except (ValueError, OSError) as exc:
                notify(str(exc), True)

        def select_directory(event: ft.FilePickerResultEvent) -> None:
            if event.path:
                state.image_directory = event.path; directory_label.value = event.path; image_notice()
                if state.sheet:
                    preview()
                else:
                    page.update()
        picker.on_result = select_excel
        folder_picker.on_result = select_directory

        def preview() -> None:
            if not state.sheet:
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Selecciona el lote primero", color=ft.Colors.RED_700),
                    content=ft.Text("Elige el archivo Excel que contiene los productos antes de validar el lote."),
                    actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close_dialog())],
                )
                open_dialog(dialog)
                return
            results = build_products(state.sheet, infer_mapping(state.sheet.headers), image_column.value, state.image_directory)
            valid_count = sum(result.valid for result in results)
            invalid_results = [result for result in results if not result.valid]
            if state.image_directory and image_column.value:
                image_status = "Fotos: se buscarán en la carpeta seleccionada usando la columna elegida."
            elif state.image_directory:
                image_status = "Fotos: hay una carpeta seleccionada, pero no una columna de imagen; los productos se subirán sin fotos."
            elif image_column.value:
                image_status = "Fotos: hay una columna seleccionada, pero no una carpeta; los productos se subirán sin fotos."
            else:
                image_status = "Fotos: no se ha seleccionado carpeta ni columna; los productos se subirán sin fotos."
            results_by_row = {result.product.row_number: result for result in results}
            table_rows = []
            for row_number, row in state.sheet.rows:
                result = results_by_row[row_number]
                valid = result.valid
                table_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(row_number))),
                    *[ft.DataCell(ft.Text(row.get(header, ""))) for header in state.sheet.headers],
                    ft.DataCell(ft.Text("Válido" if valid else "Revisar", color=ft.Colors.GREEN_700 if valid else ft.Colors.RED_700, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text("Listo para subir" if valid else "; ".join(result.errors), color=ft.Colors.GREEN_700 if valid else ft.Colors.RED_700)),
                ]))
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Fila", weight=ft.FontWeight.BOLD)),
                    *[ft.DataColumn(ft.Text(header, weight=ft.FontWeight.BOLD)) for header in state.sheet.headers],
                    ft.DataColumn(ft.Text("Estado", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Detalle", weight=ft.FontWeight.BOLD)),
                ],
                rows=table_rows,
                heading_row_color="#EEE8EC",
                border=ft.border.all(1, "#DDD4D9"),
                border_radius=8,
                column_spacing=22,
            )
            summary_color = ft.Colors.GREEN_700 if not invalid_results else ft.Colors.RED_700
            preview_area.controls = [
                ft.Text(
                    f"Validación completada: {valid_count} válidas y {len(invalid_results)} con errores.",
                    weight=ft.FontWeight.BOLD,
                    color=summary_color,
                ),
                ft.Text(image_status, color="#665B5E"),
                ft.Container(
                    ft.Column([ft.Row([table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO),
                    height=440,
                ),
            ]
            page.update()

        def perform_import(results, known_products: dict[int, dict | None], duplicate_choices: dict[int, str]) -> None:
            state.cancelled = False
            progress = ft.ProgressBar(value=0); stop = ft.OutlinedButton("Cancelar", on_click=lambda _: setattr(state, "cancelled", True))
            preview_area.controls = [progress, stop]; page.update()
            report: list[list[str]] = [["fila", "sku", "resultado", "detalle"]]
            counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
            failures: list[str] = []
            try:
                woo = client()
            except WooCommerceError as exc:
                notify(str(exc), True)
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("No se pudo iniciar la subida del lote", color=ft.Colors.RED_700),
                    content=ft.Text(str(exc)),
                    actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close_dialog())],
                )
                open_dialog(dialog)
                return
            for index, result in enumerate(results, start=1):
                if state.cancelled: break
                product = result.product; sku = product.values.get("sku", "")
                try:
                    row_number = product.row_number
                    if row_number is None:
                        raise ValueError("La fila de origen del producto no está disponible.")
                    found = known_products.get(row_number)
                    choice = duplicate_choices.get(row_number, "skip")
                    if found and choice == "skip": counts["skipped"] += 1; report.append([str(product.row_number), sku, "omitido", "SKU existente"])
                    else:
                        payload = to_woo_payload(product, import_status.value or "draft")
                        if found: woo.update_product(found["id"], payload, product.image_path); counts["updated"] += 1; outcome = "actualizado"
                        else: woo.create_product(payload, product.image_path); counts["created"] += 1; outcome = "creado"
                        report.append([str(product.row_number), sku, outcome, ""])
                except (ValueError, WooCommerceError) as exc:
                    counts["failed"] += 1; report.append([str(product.row_number), sku, "error", str(exc)])
                    failures.append(f"Fila {product.row_number}: {exc}")
                progress.value = index / len(results); page.update()
            report_path = Path.cwd() / "resultado_subida_lote.csv"
            with report_path.open("w", newline="", encoding="utf-8-sig") as output: csv.writer(output).writerows(report)
            summary = (
                f"{counts['created']} creados, {counts['updated']} actualizados, "
                f"{counts['skipped']} omitidos y {counts['failed']} fallidos."
            )
            if state.cancelled:
                title = "Subida del lote cancelada"
                color = GOLD
            elif counts["failed"]:
                title = "Subida del lote terminada con errores"
                color = ft.Colors.RED_700
            else:
                title = "Lote subido correctamente"
                color = PURPLE
            notify(f"{title}: {summary} Informe: {report_path}", counts["failed"] > 0)
            details = [ft.Text(summary), ft.Text(f"Informe detallado: {report_path}")]
            if failures:
                details.append(ft.Text("Errores detectados:", weight=ft.FontWeight.BOLD))
                details.extend(ft.Text(error) for error in failures[:5])
                if len(failures) > 5:
                    details.append(ft.Text(f"Y {len(failures) - 5} errores más en el informe."))
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title, color=color),
                content=ft.Container(ft.Column(details, tight=True, scroll=ft.ScrollMode.AUTO), width=620, height=min(400, 110 + 42 * len(details))),
                actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close_dialog())],
            )
            open_dialog(dialog)

        def run_import(_: ft.ControlEvent) -> None:
            if not state.sheet: notify("Selecciona el Excel del lote.", True); return
            results = build_products(
                state.sheet,
                infer_mapping(state.sheet.headers),
                image_column.value,
                state.image_directory or None,
            )
            errors = [r for r in results if not r.valid]
            if errors: notify(f"Hay {len(errors)} productos con errores. Corrígelos antes de subir el lote.", True); return
            try:
                woo = client()
                known_products: dict[int, dict | None] = {
                    result.product.row_number: woo.find_by_sku(result.product.values.get("sku", ""))
                    for result in results
                    if result.product.row_number is not None
                }
            except WooCommerceError as exc:
                notify(str(exc), True); return
            conflicts = []
            for result in results:
                row_number = result.product.row_number
                if row_number is None:
                    continue
                found = known_products[row_number]
                if found:
                    conflicts.append((result, row_number, found))
            if not conflicts:
                perform_import(results, known_products, {})
                return
            choices: dict[int, ft.Dropdown] = {}
            rows = []
            for result, row_number, found in conflicts:
                control = modern_dropdown(value="skip", width=160, options=[ft.dropdown.Option("skip", "Omitir"), ft.dropdown.Option("update", "Actualizar")])
                choices[row_number] = control
                rows.append(ft.Row([ft.Text(f"Fila {row_number} — SKU {result.product.values.get('sku', '')} — producto #{found['id']}", expand=True), control]))
            def confirm(_: ft.ControlEvent) -> None:
                close_dialog()
                perform_import(results, known_products, {row: control.value or "skip" for row, control in choices.items()})
            dialog = ft.AlertDialog(modal=True, title=ft.Text("SKU duplicados en el lote"), content=ft.Container(ft.Column([ft.Text("Indica qué hacer con cada producto cuyo SKU ya existe."), *rows], scroll=ft.ScrollMode.AUTO), width=700, height=min(400, 95 + 70 * len(rows))), actions=[ft.TextButton("Cancelar", on_click=lambda _: close_dialog()), ft.ElevatedButton("Continuar con el lote", on_click=confirm)])
            open_dialog(dialog)

        return ft.Container(content=ft.Column([
            ft.Text("Sube varios productos desde un único Excel. La tabla se valida automáticamente al elegirlo; nada se enviará a WooCommerce hasta que pulses “Subir lote”."),
            ft.Text("1. Excel", size=18, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Row([ft.ElevatedButton("Elegir Excel", on_click=lambda _: picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["xlsx"])), file_label]),
            preview_area,
            ft.Divider(),
            ft.Text("2. Fotos (opcional)", size=18, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Row([ft.OutlinedButton("Añadir carpeta de fotos", on_click=lambda _: folder_picker.get_directory_path()), directory_label]),
            image_column,
            ft.Divider(),
            ft.Text("3. Subir", size=18, weight=ft.FontWeight.BOLD, color=PURPLE),
            ft.Text("Si el lote contiene SKU existentes, podrás decidir en ese momento si actualizar u omitir cada producto."),
            ft.Row([import_status, ft.ElevatedButton("Subir lote", icon=ft.Icons.UPLOAD, on_click=run_import)]),
        ], scroll=ft.ScrollMode.AUTO), padding=10)

    navigation = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor=PURPLE,
        indicator_color=GOLD,
        selected_label_text_style=ft.TextStyle(color=WHITE, weight=ft.FontWeight.BOLD),
        unselected_label_text_style=ft.TextStyle(color=WHITE),
        leading=ft.Container(
            content=ft.Image(src="el-baul-logo-white.png", width=92, height=70, fit=ft.ImageFit.CONTAIN),
            margin=ft.margin.only(bottom=12),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.UPLOAD_FILE, color=WHITE),
                selected_icon=ft.Icon(ft.Icons.UPLOAD_FILE, color=PURPLE),
                label="Subir",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.SETTINGS, color=WHITE),
                selected_icon=ft.Icon(ft.Icons.SETTINGS, color=PURPLE),
                label="Configuración",
            ),
        ],
        on_change=lambda e: set_view("upload" if e.control.selected_index == 0 else "settings"),
    )
    navigation_panel = ft.Container(
        navigation,
        bgcolor=PURPLE,
        border_radius=12,
        padding=ft.padding.symmetric(vertical=12, horizontal=6),
        margin=ft.margin.only(right=16),
    )
    page.add(ft.Row(
        [navigation_panel, ft.Container(content, expand=True, bgcolor=WHITE, border_radius=12, padding=10)],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    ))
    set_view("upload")


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
