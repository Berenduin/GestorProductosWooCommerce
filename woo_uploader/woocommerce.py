from __future__ import annotations

from pathlib import Path
from typing import Any

import requests


class WooCommerceError(RuntimeError):
    def __init__(self, message: str, code: str = "", status_code: int | None = None, resource_id: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.resource_id = resource_id


class WooCommerceClient:
    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str, wordpress_user: str = "", wordpress_password: str = "", session: requests.Session | None = None) -> None:
        self.base_url = store_url.rstrip("/")
        if self.base_url.endswith("/wp-json"):
            self.base_url = self.base_url.removesuffix("/wp-json")
        self.auth = (consumer_key, consumer_secret)
        self.has_wordpress_credentials = bool(wordpress_user and wordpress_password)
        self.media_auth = (wordpress_user, wordpress_password) if self.has_wordpress_credentials else self.auth
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
                "Accept": "application/json",
            })

    def _url(self, path: str, fallback: bool = False) -> str:
        if not fallback:
            return f"{self.base_url}{path}"
        route = path.removeprefix("/wp-json")
        return f"{self.base_url}/index.php?rest_route={route}"

    def _send(self, method: str, path: str, auth: tuple[str, str], *, fallback_auth_in_query: bool = True, **kwargs: Any) -> requests.Response:
        timeout = kwargs.pop("timeout", 30)
        try:
            response = self.session.request(method, self._url(path), auth=auth, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            first_error = exc
            response = None
        else:
            first_error = None
        if response is None or response.status_code == 404:
            data = kwargs.get("data")
            if data is not None and hasattr(data, "seek"):
                data.seek(0)
            fallback_kwargs = dict(kwargs)
            if fallback_auth_in_query:
                fallback_params = dict(fallback_kwargs.get("params") or {})
                fallback_params.update({"consumer_key": auth[0], "consumer_secret": auth[1]})
                fallback_kwargs["params"] = fallback_params
            else:
                fallback_kwargs["auth"] = auth
            try:
                response = self.session.request(method, self._url(path, fallback=True), timeout=timeout, **fallback_kwargs)
            except requests.RequestException as exc:
                if first_error:
                    raise WooCommerceError(
                        f"No se pudo conectar: el servidor cerró la conexión tanto en la ruta REST habitual ({first_error}) "
                        f"como en la ruta alternativa ({exc})."
                    ) from exc
                raise WooCommerceError(f"No se pudo conectar con WooCommerce mediante la ruta alternativa: {exc}") from exc
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, self.auth, **kwargs)
        if not response.ok:
            code = ""
            resource_id = None
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    message = error_data.get("message", response.text)
                    code = str(error_data.get("code", ""))
                    details = error_data.get("data") or {}
                    resource_id = details.get("resource_id") if isinstance(details, dict) else None
                else:
                    message = response.text
            except ValueError:
                message = response.text
            raise WooCommerceError(
                f"WooCommerce respondió {response.status_code}: {message}",
                code=code,
                status_code=response.status_code,
                resource_id=resource_id,
            )
        return response.json()

    def _wordpress_request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, self.media_auth, fallback_auth_in_query=False, **kwargs)
        if not response.ok:
            try:
                message = response.json().get("message", response.text)
            except ValueError:
                message = response.text
            raise WooCommerceError(f"WordPress respondió {response.status_code}: {message}")
        return response.json()

    def test_connection(self) -> str:
        data = self._request("GET", "/wp-json/wc/v3/system_status")
        return f"Conexión correcta con WooCommerce {data.get('environment', {}).get('version', '')}".strip()

    def test_wordpress_connection(self) -> str:
        data = self._wordpress_request("GET", "/wp-json/wp/v2/users/me", params={"context": "edit"})
        capabilities = data.get("capabilities") or {}
        if capabilities and not capabilities.get("upload_files", False):
            raise WooCommerceError("La conexión con WordPress es correcta, pero el usuario no tiene permiso para subir archivos.")
        identity = data.get("name") or data.get("slug") or data.get("username") or ""
        return f"Conexión correcta con WordPress{f': {identity}' if identity else ''}"

    def find_by_sku(self, sku: str) -> dict[str, Any] | None:
        if not sku:
            return None
        params = {"sku": sku, "per_page": 1, "context": "edit", "include_status": "any,trash"}
        try:
            products = self._request("GET", "/wp-json/wc/v3/products", params=params)
        except WooCommerceError as exc:
            if exc.status_code != 400:
                raise
            products = self._request("GET", "/wp-json/wc/v3/products", params={"sku": sku, "per_page": 1})
        return products[0] if products else None

    def _category_id(self, category_name: str) -> int:
        categories = self._request(
            "GET",
            "/wp-json/wc/v3/products/categories",
            params={"search": category_name, "per_page": 100, "hide_empty": False},
        )
        for category in categories:
            if str(category.get("name", "")).casefold() == category_name.casefold():
                return int(category["id"])
        raise WooCommerceError(f"No se encontró la categoría «{category_name}» en WooCommerce.")

    def list_published_products(self, category_name: str | None = None) -> list[dict[str, Any]]:
        """Devuelve los productos publicados de una categoría, recorriendo la paginación REST."""
        products: list[dict[str, Any]] = []
        page = 1
        per_page = 100
        category_id = self._category_id(category_name) if category_name else None
        while True:
            # La vista autenticada incluye campos y metadatos que WooCommerce
            # omite del contexto público, como las taxonomías de Escudos.
            params: dict[str, Any] = {"status": "publish", "per_page": per_page, "page": page, "context": "edit"}
            if category_id is not None:
                params["category"] = category_id
            batch = self._request(
                "GET",
                "/wp-json/wc/v3/products",
                params=params,
            )
            if not batch:
                return products
            products.extend(batch)
            page += 1

    def upload_image(self, path: Path) -> str:
        headers = {"Content-Disposition": f'attachment; filename="{path.name}"', "Content-Type": "application/octet-stream"}
        try:
            with path.open("rb") as image:
                response = self._send(
                    "POST",
                    "/wp-json/wp/v2/media",
                    self.media_auth,
                    fallback_auth_in_query=not self.has_wordpress_credentials,
                    data=image,
                    headers=headers,
                    timeout=60,
                )
        except (OSError, requests.RequestException) as exc:
            raise WooCommerceError(f"No se pudo subir la imagen: {exc}") from exc
        if not response.ok:
            raise WooCommerceError("No se pudo subir la imagen a WordPress. Configure un usuario y contraseña de aplicación de WordPress si la tienda no acepta las claves WooCommerce para medios.")
        return response.json()["source_url"]

    def create_product(self, payload: dict[str, Any], image_path: Path | None = None) -> dict[str, Any]:
        if image_path:
            payload = {**payload, "images": [{"src": self.upload_image(image_path)}]}
        return self._request("POST", "/wp-json/wc/v3/products", json=payload)

    def update_product(self, product_id: int, payload: dict[str, Any], image_path: Path | None = None) -> dict[str, Any]:
        if image_path:
            payload = {**payload, "images": [{"src": self.upload_image(image_path)}]}
        return self._request("PUT", f"/wp-json/wc/v3/products/{product_id}", json=payload)
