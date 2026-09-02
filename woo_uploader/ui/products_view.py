"""Vista de consulta de los productos publicados en WooCommerce."""

from __future__ import annotations

from typing import Any

import flet as ft

from ..models import LOCATION_TAXONOMIES
from ..woocommerce import WooCommerceError
from .components import primary_button, section
from .theme import PURPLE

def _category_names(product: dict[str, Any]) -> list[str]:
    names = [str(category.get("name", "")).strip() for category in product.get("categories", [])]
    unique_names: list[str] = []
    seen: set[str] = set()
    for name in names:
        normalized = name.casefold()
        if name and normalized not in seen:
            unique_names.append(name)
            seen.add(normalized)
    return unique_names or ["Sin categoría"]


def _products_by_category(products: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for product in products:
        for category in _category_names(product):
            key = category.casefold()
            if key not in grouped:
                grouped[key] = (category, [])
            grouped[key][1].append(product)
    return {name: rows for name, rows in sorted(grouped.values(), key=lambda group: group[0].casefold())}


def _stock(product: dict[str, Any]) -> str:
    if not product.get("manage_stock"):
        return "No se gestiona"
    quantity = product.get("stock_quantity")
    return str(quantity) if quantity is not None else "Sin existencias"


def _stock_status(product: dict[str, Any]) -> str:
    labels = {"instock": "En stock", "outofstock": "Agotado", "onbackorder": "Bajo pedido"}
    return labels.get(str(product.get("stock_status", "")), "—")


def _names(product: dict[str, Any], field: str) -> str:
    names = [str(item.get("name", "")).strip() for item in product.get(field, [])]
    return ", ".join(name for name in names if name) or "—"


def _dimensions(product: dict[str, Any]) -> str:
    dimensions = product.get("dimensions") or {}
    values = [str(dimensions.get(key, "")).strip() for key in ("length", "width", "height")]
    return " × ".join(value or "—" for value in values) if any(values) else "—"


def _published_date(product: dict[str, Any]) -> str:
    value = str(product.get("date_created", "") or product.get("date_created_gmt", ""))
    return value[:10] if value else "—"


def _taxonomy_values(product: dict[str, Any], taxonomy: str) -> str:
    """Obtiene una taxonomía propia sin depender de cómo la serialice la API.

    El filtro del plugin de escudos la expone normalmente como una clave de
    primer nivel. Algunas configuraciones de WooCommerce, sin embargo, la
    devuelven dentro de ``meta_data`` o de los atributos del producto.
    """
    values = product.get(taxonomy)
    if not values:
        values = _metadata_value(product, taxonomy)
    if not values:
        values = _attribute_options(product, taxonomy)
    if values is None:
        values = []
    if not isinstance(values, list):
        values = [values]
    names = [str(value.get("name", "")).strip() if isinstance(value, dict) else str(value).strip() for value in values]
    return ", ".join(name for name in names if name) or "—"


def _metadata_value(product: dict[str, Any], key: str) -> Any:
    metadata = product.get("meta_data", [])
    if not isinstance(metadata, list):
        return None
    for item in metadata:
        if isinstance(item, dict) and item.get("key") == key:
            return item.get("value")
    return None


def _attribute_options(product: dict[str, Any], name: str) -> Any:
    attributes = product.get("attributes", [])
    if not isinstance(attributes, list):
        return None
    for attribute in attributes:
        if isinstance(attribute, dict) and str(attribute.get("name", "")).casefold() == name.casefold():
            return attribute.get("options")
    return None


def _table(products: list[dict[str, Any]], show_location: bool = False) -> ft.Control:
    if not products:
        return ft.Container(
            ft.Text("No hay productos publicados en WooCommerce.", color="#665B5E"),
            padding=ft.padding.symmetric(vertical=24),
        )

    rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(product.get("id", "")) or "—")),
                ft.DataCell(ft.Text(str(product.get("name", "")))),
                ft.DataCell(ft.Text(str(product.get("sku", "")) or "—")),
                *([ft.DataCell(ft.Text(_taxonomy_values(product, taxonomy))) for taxonomy, _ in LOCATION_TAXONOMIES] if show_location else []),
                ft.DataCell(ft.Text(str(product.get("regular_price", "")) or "—")),
                ft.DataCell(ft.Text(str(product.get("sale_price", "")) or "—")),
                ft.DataCell(ft.Text(_stock(product))),
                ft.DataCell(ft.Text(_stock_status(product))),
                ft.DataCell(ft.Text(str(product.get("low_stock_amount", "")) or "—")),
                ft.DataCell(ft.Text("Sí" if product.get("featured") else "No")),
                ft.DataCell(ft.Text(str(product.get("catalog_visibility", "")) or "—")),
                ft.DataCell(ft.Text(_names(product, "tags"))),
                ft.DataCell(ft.Text(str(product.get("weight", "")) or "—")),
                ft.DataCell(ft.Text(_dimensions(product))),
                ft.DataCell(ft.Text(_published_date(product))),
            ]
        )
        for product in products
    ]
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Nombre", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("SKU", weight=ft.FontWeight.BOLD)),
            *([ft.DataColumn(ft.Text(label, weight=ft.FontWeight.BOLD)) for _, label in LOCATION_TAXONOMIES] if show_location else []),
            ft.DataColumn(ft.Text("Precio normal", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Precio oferta", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Cantidad", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Estado stock", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Umbral bajo", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Destacado", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Visibilidad", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Etiquetas", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Peso", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Dimensiones", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Publicado", weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        heading_row_color="#EEE8EC",
        border=ft.border.all(1, "#DDD4D9"),
        border_radius=8,
        column_spacing=22,
    )
    return ft.Row([table], scroll=ft.ScrollMode.AUTO)


def _category_panel(app: Any, category: str) -> ft.Container:
    """Crea una pestaña sin datos hasta que la persona usuaria la consulte."""
    content = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)
    cache_key = category.casefold()

    def button(label: str, force_refresh: bool) -> ft.Control:
        return ft.Container(
            primary_button(label, lambda _: load_products(force_refresh), ft.Icons.REFRESH),
            alignment=ft.alignment.center,
        )

    def show_initial() -> None:
        content.controls[:] = [
            ft.Text(f"La tabla de «{category}» todavía no se ha consultado.", color="#665B5E", text_align=ft.TextAlign.CENTER),
            button(f"Consultar {category}", False),
        ]

    def show_products(products: list[dict[str, Any]]) -> None:
        summary = f"{len(products)} producto{'s' if len(products) != 1 else ''} publicado{'s' if len(products) != 1 else ''} en «{category}»."
        content.controls[:] = [
            button(f"Actualizar {category}", True),
            ft.Text(summary, color="#665B5E"),
            _table(products, category.casefold() == "escudos"),
        ]

    def load_products(force_refresh: bool) -> None:
        if cache_key in app.published_products_cache and not force_refresh:
            show_products(app.published_products_cache[cache_key])
            app.page.update()
            return
        app.begin_loading(f"Consultando {category}", f"Cargando los productos publicados de la categoría «{category}».")
        try:
            products = app.create_client().list_published_products(category)
        except WooCommerceError as exc:
            content.controls[:] = [
                ft.Text(f"No se pudo cargar «{category}».", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD),
                ft.Text(str(exc), color="#665B5E"),
                button(f"Reintentar {category}", True),
            ]
        else:
            app.published_products_cache[cache_key] = products
            show_products(products)
        finally:
            app.close_dialog()
            app.page.update()

    show_initial()
    return ft.Container(content=content, height=540, padding=ft.padding.only(top=22))


def build_products_view(app: Any) -> list[ft.Control]:
    categories = list(dict.fromkeys(category.strip() for category in app.settings.categories if category.strip()))
    tabs: ft.Control
    if categories:
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=150,
            scrollable=True,
            height=620,
            tabs=[ft.Tab(text=category, content=_category_panel(app, category)) for category in categories],
        )
    else:
        tabs = ft.Text("No hay categorías configuradas. Añádelas desde Configuración.", color=ft.Colors.RED_700)
    return [
        ft.Text("Ver productos", size=26, weight=ft.FontWeight.BOLD, color=PURPLE),
        section("Productos publicados", "Selecciona una categoría y consulta solo su tabla. Cada pestaña se actualiza de forma independiente.", [tabs]),
    ]
