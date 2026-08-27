"""Inspecciona el esquema y una muestra de productos de la tienda configurada.

Usa la URL y las credenciales guardadas por la aplicación. No muestra ni guarda
credenciales. Ejecutar desde la raíz del proyecto:

    python3 inspect_woocommerce_products.py
"""

from __future__ import annotations

from typing import Any

import requests

from woo_uploader.config import SettingsStore
from woo_uploader.woocommerce import WooCommerceError


def response_message(response: requests.Response) -> str:
    try:
        return str(response.json().get("message", response.text))
    except (ValueError, AttributeError):
        return response.text


def request_with_fallback(
    session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    credentials: tuple[str, str],
    **kwargs: Any,
) -> requests.Response:
    first_error: requests.RequestException | None = None
    try:
        response = session.request(method, f"{base_url}{path}", auth=credentials, timeout=30, **kwargs)
    except requests.RequestException as first_error:
        response = None
    else:
        first_error = None

    if response is not None and response.status_code != 404:
        return response

    fallback_params = dict(kwargs.pop("params", {}) or {})
    fallback_params.update({"consumer_key": credentials[0], "consumer_secret": credentials[1]})
    route = path.removeprefix("/wp-json")
    try:
        return session.request(
            method,
            f"{base_url}/index.php?rest_route={route}",
            params=fallback_params,
            timeout=30,
            **kwargs,
        )
    except requests.RequestException as fallback_error:
        detail = f" ({first_error})" if first_error else ""
        raise WooCommerceError(f"No se pudo conectar con ninguna ruta REST{detail}: {fallback_error}") from fallback_error


def product_write_fields(options: dict[str, Any]) -> dict[str, dict[str, Any]]:
    route = options.get("routes", {}).get("/wc/v3/products", options)
    fields: dict[str, dict[str, Any]] = {}
    for endpoint in route.get("endpoints", []):
        methods = endpoint.get("methods", [])
        if "POST" in methods or "PUT" in methods:
            fields.update(endpoint.get("args", {}))
    return fields


def main() -> None:
    settings = SettingsStore().load()
    consumer_key, consumer_secret, _ = SettingsStore().credentials()
    if not settings.store_url or not consumer_key or not consumer_secret:
        raise SystemExit("Configura la URL y las claves REST en la aplicación antes de ejecutar este script.")

    base_url = settings.store_url.rstrip("/").removesuffix("/wp-json")
    credentials = (consumer_key, consumer_secret)
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    })

    options_response = request_with_fallback(session, base_url, "OPTIONS", "/wp-json/wc/v3/products", credentials)
    if not options_response.ok:
        raise SystemExit(f"No se pudo obtener el esquema: HTTP {options_response.status_code}: {response_message(options_response)}")
    fields = product_write_fields(options_response.json())

    sample_response = request_with_fallback(
        session,
        base_url,
        "GET",
        "/wp-json/wc/v3/products",
        credentials,
        params={"per_page": 1, "context": "edit"},
    )
    if not sample_response.ok:
        raise SystemExit(f"No se pudo obtener una muestra: HTTP {sample_response.status_code}: {response_message(sample_response)}")
    products = sample_response.json()
    sample_fields = sorted(products[0]) if products else []

    print("CAMPOS EDITABLES ADMITIDOS POR LA API (POST /products)")
    if not fields:
        print("La tienda no ha expuesto el esquema mediante OPTIONS.")
    for name in sorted(fields):
        info = fields[name]
        description = info.get("description", "")
        field_type = info.get("type", "sin tipo indicado")
        required = " obligatorio" if info.get("required") else ""
        enum = f" Valores: {', '.join(map(str, info['enum']))}." if info.get("enum") else ""
        print(f"- {name} ({field_type}{required}). {description}{enum}".rstrip())

    print("\nCAMPOS DEVUELTOS POR UN PRODUCTO REAL (GET /products?context=edit)")
    if sample_fields:
        print(", ".join(sample_fields))
    else:
        print("La tienda no contiene productos accesibles con estas credenciales.")


if __name__ == "__main__":
    main()
