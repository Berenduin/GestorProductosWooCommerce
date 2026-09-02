from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..version import APP_NAME, APP_VERSION
from .components import modern_dropdown, modern_text_field, section
from .theme import PURPLE, WHITE

if TYPE_CHECKING:
    from ..app_controller import AppController


def _show_connection_feedback(page: ft.Page, control: ft.Text, message: str, error: bool = False) -> None:
    control.value = message
    control.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
    control.visible = True
    page.update()


def build_settings_view(app: AppController, selected_tab: int = 0) -> list[ft.Control]:
    key, secret, wp_password = app.credentials()
    settings = app.settings
    url = modern_text_field("URL de la tienda", "https://mitienda.es", ft.Icons.LINK_OUTLINED, value=settings.store_url)
    consumer_key = modern_text_field("Consumer Key", "ck_…", ft.Icons.KEY_OUTLINED, value=key, password=True, can_reveal_password=True)
    consumer_secret = modern_text_field("Consumer Secret", "cs_…", ft.Icons.KEY_OUTLINED, value=secret, password=True, can_reveal_password=True)
    wp_user = modern_text_field("Usuario de WordPress", "Ej.: administrador", ft.Icons.PERSON_OUTLINE, value=settings.wordpress_user)
    wp_pass = modern_text_field("Contraseña de aplicación de WordPress", "xxxx xxxx xxxx xxxx", ft.Icons.LOCK_OUTLINE, value=wp_password, password=True, can_reveal_password=True)
    default_status = modern_dropdown(label="Estado predeterminado", value=settings.default_status, prefix_icon=ft.Icons.VISIBILITY_OUTLINED, options=[ft.dropdown.Option("draft", "Borrador"), ft.dropdown.Option("publish", "Publicado")])
    woo_feedback = ft.Text(visible=False, size=13, selectable=True)
    wordpress_feedback = ft.Text(visible=False, size=13, selectable=True)
    category_list = ft.Column(spacing=4)
    category_inputs: list[ft.TextField] = []
    new_category = modern_text_field("Nueva categoría", "Ej.: Accesorios", ft.Icons.ADD_CIRCLE_OUTLINE, expand=True)

    def configured_categories() -> list[str]:
        categories: list[str] = []
        seen: set[str] = set()
        for control in category_inputs:
            name = (control.value or "").strip()
            if name and name.casefold() not in seen:
                categories.append(name)
                seen.add(name.casefold())
        return categories

    def refresh_category_colors() -> None:
        for index, control in enumerate(category_inputs):
            control.bgcolor = WHITE if index % 2 == 0 else "#FBF7F8"

    def save_categories() -> None:
        try:
            app.save_categories(configured_categories())
            app.notify("Categorías actualizadas.")
        except Exception as exc:
            app.notify(f"No se pudieron guardar las categorías: {exc}", True)

    def add_category(name: str) -> None:
        category_input = modern_text_field(None, "Nombre de categoría", value=name, dense=True, expand=True)
        row = ft.Row(spacing=6)

        def remove_category(_: ft.ControlEvent) -> None:
            category_inputs.remove(category_input)
            category_list.controls.remove(row)
            refresh_category_colors()
            save_categories()
            app.page.update()

        category_input.on_blur = lambda _: save_categories()
        category_inputs.append(category_input)
        row.controls.extend([category_input, ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Eliminar categoría", on_click=remove_category)])
        category_list.controls.append(row)
        refresh_category_colors()

    for category in settings.categories:
        add_category(category)

    def add_new_category(_: ft.ControlEvent) -> None:
        name = (new_category.value or "").strip()
        if not name:
            return
        if name.casefold() in {(control.value or "").strip().casefold() for control in category_inputs}:
            app.notify("Esa categoría ya existe.", True)
            return
        add_category(name)
        new_category.value = ""
        save_categories()
        app.page.update()

    def normalized_url() -> str:
        return (url.value or "").strip().rstrip("/").removesuffix("/wp-json")

    def save_woocommerce(_: ft.ControlEvent) -> None:
        try:
            app.save_woocommerce_connection(normalized_url(), default_status.value or "draft", (consumer_key.value or "").strip(), (consumer_secret.value or "").strip())
            _show_connection_feedback(app.page, woo_feedback, "Conexión de WooCommerce guardada. Las claves se han enviado al llavero del sistema.")
        except Exception as exc:
            _show_connection_feedback(app.page, woo_feedback, f"No se pudo guardar la conexión de WooCommerce: {exc}", True)

    def test_woocommerce(_: ft.ControlEvent) -> None:
        _show_connection_feedback(app.page, woo_feedback, "Comprobando la conexión con WooCommerce…")
        try:
            _show_connection_feedback(app.page, woo_feedback, app.test_woocommerce_connection(normalized_url(), (consumer_key.value or "").strip(), (consumer_secret.value or "").strip()))
        except Exception as exc:
            _show_connection_feedback(app.page, woo_feedback, str(exc), True)

    def save_wordpress(_: ft.ControlEvent) -> None:
        try:
            app.save_wordpress_connection(normalized_url(), (wp_user.value or "").strip(), (wp_pass.value or "").strip())
            _show_connection_feedback(app.page, wordpress_feedback, "Conexión de WordPress guardada. La contraseña se ha enviado al llavero del sistema.")
        except Exception as exc:
            _show_connection_feedback(app.page, wordpress_feedback, f"No se pudo guardar la conexión de WordPress: {exc}", True)

    def test_wordpress(_: ft.ControlEvent) -> None:
        _show_connection_feedback(app.page, wordpress_feedback, "Comprobando la conexión con WordPress…")
        try:
            _show_connection_feedback(app.page, wordpress_feedback, app.test_wordpress_connection(normalized_url(), (wp_user.value or "").strip(), (wp_pass.value or "").strip()))
        except Exception as exc:
            _show_connection_feedback(app.page, wordpress_feedback, str(exc), True)

    categories_tab = ft.Column([
        ft.Text("Categorías de productos", size=20, weight=ft.FontWeight.BOLD, color=PURPLE),
        ft.Text("Añade, modifica o elimina las categorías disponibles al subir un producto."),
        ft.Row([new_category, ft.ElevatedButton("Añadir categoría", icon=ft.Icons.ADD, on_click=add_new_category)]),
        category_list,
    ], scroll=ft.ScrollMode.AUTO)
    connection_tab = ft.Column([
        ft.Text("Conexiones con la tienda", size=20, weight=ft.FontWeight.BOLD, color=PURPLE),
        ft.Text("WooCommerce gestiona los productos y WordPress recibe las imágenes. Sus credenciales se guardan y se comprueban por separado."),
        url,
        section("API de WooCommerce · Productos", "Utiliza la Consumer Key y la Consumer Secret creadas en WooCommerce.", [
            consumer_key,
            consumer_secret,
            default_status,
            ft.Row([ft.ElevatedButton("Guardar WooCommerce", icon=ft.Icons.SAVE_OUTLINED, on_click=save_woocommerce), ft.OutlinedButton("Probar WooCommerce", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=test_woocommerce)], wrap=True),
            woo_feedback,
        ]),
        section("API de WordPress · Imágenes", "Utiliza un usuario de WordPress y su contraseña de aplicación. No introduzcas aquí la contraseña normal de acceso.", [
            wp_user,
            wp_pass,
            ft.Row([ft.ElevatedButton("Guardar WordPress", icon=ft.Icons.SAVE_OUTLINED, on_click=save_wordpress), ft.OutlinedButton("Probar WordPress", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=test_wordpress)], wrap=True),
            wordpress_feedback,
        ]),
        ft.Text("Los datos sensibles se almacenan en el llavero del sistema, no en el archivo de configuración.", size=12, color="#665B5E"),
    ], scroll=ft.ScrollMode.AUTO)
    updates_tab = ft.Column([
        ft.Text("Actualizaciones", size=20, weight=ft.FontWeight.BOLD, color=PURPLE),
        ft.Text(f"{APP_NAME} versión {APP_VERSION}", weight=ft.FontWeight.BOLD),
        ft.Text("En futuras versiones, este apartado avisará cuando haya una actualización disponible y permitirá descargar el instalador de forma segura.", color="#665B5E"),
        ft.Container(
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=PURPLE),
                ft.Text("La comprobación automática de actualizaciones se activará cuando se publique la primera versión de distribución.", expand=True),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor="#FBF7F8",
            border_radius=8,
            padding=12,
        ),
    ], scroll=ft.ScrollMode.AUTO)
    return [ft.Text("Configuración", size=26, weight=ft.FontWeight.BOLD, color=PURPLE), ft.Tabs(selected_index=selected_tab, expand=True, tabs=[ft.Tab(text="Categorías", content=categories_tab), ft.Tab(text="Conexión", content=connection_tab), ft.Tab(text="Actualizaciones", content=updates_tab)]), app.status]
