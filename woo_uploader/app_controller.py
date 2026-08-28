"""Composición de la aplicación y coordinación entre vistas y servicios."""

from __future__ import annotations

from typing import Any

import flet as ft

from .config import Settings, SettingsStore
from .services.connection import ConnectionService
from .ui.bulk_import_view import build_bulk_import_view
from .ui.help_view import build_help_view
from .ui.products_view import build_products_view
from .ui.settings_view import build_settings_view
from .ui.single_product_view import build_single_product_view
from .ui.theme import GOLD, PURPLE, WHITE


class AppController:
    def __init__(self, page: ft.Page, store: SettingsStore | None = None) -> None:
        self.page = page
        self.store = store or SettingsStore()
        self.settings = self.store.load()
        self.connection_service = ConnectionService()
        self.status = ft.Text()
        self.content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._active_dialog: ft.AlertDialog | None = None
        self._upload_message: ft.Text | None = None
        self._upload_progress: ft.ProgressBar | None = None
        self.published_products_cache: dict[str, list[dict[str, Any]]] = {}
        self.single_image_picker = ft.FilePicker()
        self.batch_excel_picker = ft.FilePicker()
        self.batch_directory_picker = ft.FilePicker()

    def start(self) -> None:
        self.page.overlay.extend([self.single_image_picker, self.batch_excel_picker, self.batch_directory_picker])
        self.navigation = ft.NavigationRail(selected_index=0, label_type=ft.NavigationRailLabelType.ALL, bgcolor=PURPLE, indicator_color=GOLD, selected_label_text_style=ft.TextStyle(color=WHITE, weight=ft.FontWeight.BOLD), unselected_label_text_style=ft.TextStyle(color=WHITE), leading=ft.Container(content=ft.Image(src="el-baul-logo-white.png", width=92, height=70, fit=ft.ImageFit.CONTAIN), margin=ft.margin.only(bottom=12)), destinations=[ft.NavigationRailDestination(icon=ft.Icon(ft.Icons.UPLOAD_FILE, color=WHITE), selected_icon=ft.Icon(ft.Icons.UPLOAD_FILE, color=PURPLE), label="Subir"), ft.NavigationRailDestination(icon=ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, color=WHITE), selected_icon=ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, color=PURPLE), label="Ver productos"), ft.NavigationRailDestination(icon=ft.Icon(ft.Icons.SETTINGS, color=WHITE), selected_icon=ft.Icon(ft.Icons.SETTINGS, color=PURPLE), label="Configuración"), ft.NavigationRailDestination(icon=ft.Icon(ft.Icons.HELP_OUTLINE, color=WHITE), selected_icon=ft.Icon(ft.Icons.HELP, color=PURPLE), label="Ayuda")], on_change=lambda event: self.set_view(("upload", "products", "settings", "help")[event.control.selected_index]))
        navigation_panel = ft.Container(self.navigation, bgcolor=PURPLE, border_radius=12, padding=ft.padding.symmetric(vertical=12, horizontal=6), margin=ft.margin.only(right=16))
        self.page.add(ft.Row([navigation_panel, ft.Container(self.content, expand=True, bgcolor=WHITE, border_radius=12, padding=10)], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH))
        self.set_view("upload")

    def set_view(self, view: str, upload_tab: int = 0, settings_tab: int = 0) -> None:
        self.content.controls.clear()
        self.navigation.selected_index = {"upload": 0, "products": 1, "settings": 2, "help": 3}[view]
        if view == "settings":
            self.content.controls.extend(build_settings_view(self, selected_tab=settings_tab))
        elif view == "help":
            self.content.controls.extend(build_help_view(self))
        elif view == "products":
            self.content.controls.extend(build_products_view(self))
        else:
            tabs = ft.Tabs(selected_index=upload_tab, animation_duration=150, expand=1, tabs=[ft.Tab(text="Un producto", content=build_single_product_view(self)), ft.Tab(text="Subir por lote", content=build_bulk_import_view(self))])
            self.content.controls.extend([ft.Text("Subir productos", size=26, weight=ft.FontWeight.BOLD, color=PURPLE), tabs, self.status])
        self.page.update()
        self.content.scroll_to(offset=0, duration=0)

    def credentials(self) -> tuple[str, str, str]:
        return self.store.credentials()

    def create_client(self):
        return self.connection_service.create_client(self.settings, self.credentials())

    def test_connection(self) -> str:
        return self.connection_service.test_connection(self.settings, self.credentials())

    def save_connection(self, settings: Settings, consumer_key: str, consumer_secret: str, wordpress_password: str) -> None:
        self.store.save(settings, consumer_key, consumer_secret, wordpress_password)
        self.settings = settings
        self.published_products_cache.clear()

    def save_categories(self, categories: list[str]) -> None:
        self.settings = Settings(self.settings.store_url, self.settings.wordpress_user, self.settings.default_status, categories)
        self.store.save_settings(self.settings)

    def notify(self, message: str, error: bool = False) -> None:
        self.status.value = message
        self.status.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
        self.page.update()

    def open_dialog(self, dialog: ft.AlertDialog) -> None:
        self.close_dialog()
        self._active_dialog = dialog
        self.page.open(dialog)

    def begin_upload(self, message: str, show_progress: bool = False) -> None:
        """Muestra un modal no descartable mientras se realiza una operación remota."""
        self._upload_message = ft.Text(message, text_align=ft.TextAlign.CENTER)
        self._upload_progress = ft.ProgressBar(value=0) if show_progress else None
        indicator: ft.Control = self._upload_progress or ft.ProgressRing()
        controls: list[ft.Control] = [indicator, self._upload_message]
        if show_progress:
            controls.append(ft.Text("No cierre ni utilice la aplicación hasta que termine la carga.", size=12, color="#665B5E", text_align=ft.TextAlign.CENTER))
        self.open_dialog(ft.AlertDialog(modal=True, title=ft.Text("Subiendo productos", color=PURPLE), content=ft.Container(ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=18), width=380, padding=ft.padding.symmetric(vertical=12))))

    def begin_loading(self, title: str, message: str) -> None:
        """Muestra un indicador no descartable durante una consulta remota."""
        self.open_dialog(ft.AlertDialog(modal=True, title=ft.Text(title, color=PURPLE), content=ft.Container(ft.Column([ft.ProgressRing(), ft.Text(message, text_align=ft.TextAlign.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, spacing=18), width=380, padding=ft.padding.symmetric(vertical=12))))

    def update_upload_progress(self, current: int, total: int) -> None:
        if self._upload_progress is None or self._upload_message is None:
            return
        self._upload_progress.value = current / total if total else 0
        self._upload_message.value = f"Subiendo productos: {current} de {total}."
        self.page.update()

    def close_dialog(self) -> None:
        if self._active_dialog:
            self.page.close(self._active_dialog)
            self._active_dialog = None
        self._upload_message = None
        self._upload_progress = None
