from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

LOCATION_TAXONOMIES = (
    ("ebdlt_pais", "País"),
    ("ebdlt_region", "Comunidad o estado"),
    ("ebdlt_ciudad", "Ciudad"),
)
LOCATION_TAXONOMY_KEYS = tuple(key for key, _ in LOCATION_TAXONOMIES)

FIELD_LABELS = {
    "ignore": "Ignorar columna",
    "name": "Nombre *",
    "sku": "SKU",
    "regular_price": "Precio *",
    "sale_price": "Precio rebajado",
    "description": "Descripción",
    "short_description": "Descripción corta",
    "catalog_visibility": "Visibilidad en catálogo",
    "featured": "Producto destacado (sí/no)",
    "stock_quantity": "Cantidad de stock",
    "manage_stock": "Gestionar stock (sí/no)",
    "stock_status": "Estado de existencias",
    "backorders": "Permitir pedidos bajo demanda",
    "low_stock_amount": "Umbral de pocas existencias",
    "sold_individually": "Vender una unidad por pedido (sí/no)",
    "categories": "Categoría *",
    "ebdlt_pais": "País",
    "ebdlt_region": "Comunidad o estado",
    "ebdlt_ciudad": "Ciudad",
    "tags": "Etiquetas (separadas por coma)",
    "weight": "Peso",
    "length": "Largo",
    "width": "Ancho",
    "height": "Alto",
    "shipping_class": "Clase de envío",
    "tax_status": "Estado fiscal",
    "tax_class": "Clase de impuesto",
    "virtual": "Producto virtual (sí/no)",
    "status": "Estado (draft/publish)",
}

WOO_FIELDS = tuple(FIELD_LABELS)
NUMERIC_FIELDS = {"regular_price", "sale_price", "stock_quantity", "low_stock_amount", "weight", "length", "width", "height"}


@dataclass
class ProductInput:
    values: dict[str, Any]
    image_path: Path | None = None
    row_number: int | None = None


@dataclass
class ValidationResult:
    product: ProductInput
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def clean_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def capitalize_initial(value: Any) -> str:
    """Limpia un valor y escribe su primer carácter en mayúscula."""
    cleaned = clean_value(value)
    return cleaned[:1].upper() + cleaned[1:]


def is_shield_category(value: Any) -> bool:
    return clean_value(value).casefold() == "escudos"


def split_names(value: Any) -> list[dict[str, str]]:
    return [{"name": part.strip()} for part in clean_value(value).split(",") if part.strip()]


def parse_boolean(value: Any) -> bool:
    return clean_value(value).casefold() in {"1", "true", "si", "sí", "yes", "y"}


def validate_product(
    product: ProductInput,
    image_required: bool = False,
    required_fields: tuple[str, ...] = ("name",),
) -> ValidationResult:
    values = {key: clean_value(value) for key, value in product.values.items() if clean_value(value)}
    if is_shield_category(values.get("categories")):
        for key in LOCATION_TAXONOMY_KEYS:
            if key in values:
                values[key] = capitalize_initial(values[key])
    else:
        for key in LOCATION_TAXONOMY_KEYS:
            values.pop(key, None)
    result = ValidationResult(ProductInput(values, product.image_path, product.row_number))
    for key in required_fields:
        if not values.get(key):
            label = " ".join(FIELD_LABELS[key].replace("*", " ").split()).lower()
            result.errors.append(f"Falta {label}.")
    for key in NUMERIC_FIELDS:
        if key not in values:
            continue
        try:
            Decimal(values[key].replace(",", "."))
        except InvalidOperation:
            result.errors.append(f"{FIELD_LABELS[key]} debe ser un número.")
    if values.get("stock_quantity") and not values["stock_quantity"].replace("-", "", 1).isdigit():
        result.errors.append("La cantidad de stock debe ser un número entero.")
    if values.get("categories") and "," in values["categories"]:
        result.errors.append("La categoría debe contener un único valor.")
    if values.get("status") and values["status"] not in {"draft", "publish"}:
        result.errors.append("El estado debe ser draft o publish.")
    if values.get("catalog_visibility") and values["catalog_visibility"] not in {"visible", "catalog", "search", "hidden"}:
        result.errors.append("La visibilidad debe ser visible, catalog, search o hidden.")
    if values.get("stock_status") and values["stock_status"] not in {"instock", "outofstock", "onbackorder"}:
        result.errors.append("El estado de existencias debe ser instock, outofstock u onbackorder.")
    if values.get("backorders") and values["backorders"] not in {"no", "notify", "yes"}:
        result.errors.append("Los pedidos bajo demanda deben ser no, notify o yes.")
    if values.get("tax_status") and values["tax_status"] not in {"taxable", "shipping", "none"}:
        result.errors.append("El estado fiscal debe ser taxable, shipping o none.")
    if image_required and not product.image_path:
        result.errors.append("No se ha encontrado una imagen.")
    if product.image_path and not product.image_path.is_file():
        result.errors.append("La imagen indicada no existe.")
    elif product.image_path and product.image_path.suffix.casefold() not in IMAGE_EXTENSIONS:
        result.errors.append("Formato de imagen no compatible.")
    return result


def to_woo_payload(product: ProductInput, default_status: str) -> dict[str, Any]:
    values = product.values
    payload: dict[str, Any] = {"type": "simple", "name": values["name"], "status": values.get("status", default_status)}
    for key in ("sku", "regular_price", "sale_price", "description", "short_description", "weight"):
        if values.get(key):
            payload[key] = values[key]
    for key in ("catalog_visibility", "stock_status", "backorders", "shipping_class", "tax_status", "tax_class"):
        if values.get(key):
            payload[key] = values[key]
    for key in ("featured", "virtual", "sold_individually"):
        if values.get(key):
            payload[key] = parse_boolean(values[key])
    if values.get("stock_quantity"):
        payload["manage_stock"] = True
        payload["stock_quantity"] = int(values["stock_quantity"])
    elif values.get("manage_stock"):
        payload["manage_stock"] = parse_boolean(values["manage_stock"])
    if values.get("low_stock_amount"):
        payload["low_stock_amount"] = int(values["low_stock_amount"])
    dimensions = {key: values[key] for key in ("length", "width", "height") if values.get(key)}
    if dimensions:
        payload["dimensions"] = dimensions
    if values.get("categories"):
        payload["categories"] = [{"name": values["categories"]}]
    if values.get("tags"):
        payload["tags"] = split_names(values["tags"])
    for key in LOCATION_TAXONOMY_KEYS:
        if values.get(key):
            payload[key] = [values[key]]
    return payload
