from typing import Any

import requests

from woo_uploader.woocommerce import WooCommerceClient, WooCommerceError


class Response:
    def __init__(self, status: int, data: Any): self.status_code, self._data = status, data; self.ok = status < 400; self.text = str(data)
    def json(self): return self._data


class Session:
    def __init__(self): self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Response(200, [{"id": 8, "sku": "X"}] if "products" in url else {"environment": {"version": "9.0"}})


def test_find_by_sku_uses_wc_endpoint() -> None:
    session = Session()
    client = WooCommerceClient("https://shop.example/", "ck", "cs", session=session)
    assert client.find_by_sku("X")["id"] == 8
    assert session.calls[0][1] == "https://shop.example/wp-json/wc/v3/products"
    assert session.calls[0][2]["params"]["sku"] == "X"


def test_session_uses_browser_like_user_agent() -> None:
    client = WooCommerceClient("https://shop.example", "ck", "cs")
    assert client.session.headers["User-Agent"].startswith("Mozilla/5.0")
    assert client.session.headers["Accept"] == "application/json"


def test_connection_error_is_wrapped() -> None:
    class Broken:
        def request(self, *args, **kwargs): raise requests.RequestException("offline")
    try:
        WooCommerceClient("https://shop.example", "ck", "cs", session=Broken()).test_connection()
    except WooCommerceError as exc:
        assert "No se pudo conectar" in str(exc)
    else:
        raise AssertionError("Se esperaba WooCommerceError")


def test_uses_rest_route_fallback_after_a_404() -> None:
    class FallbackSession:
        def __init__(self): self.calls = []
        def request(self, method, url, **kwargs):
            self.calls.append((url, kwargs))
            return Response(404, {}) if len(self.calls) == 1 else Response(200, {"environment": {"version": "9.0"}})

    session = FallbackSession()
    client = WooCommerceClient("https://shop.example/wp-json", "ck", "cs", session=session)
    assert client.test_connection() == "Conexión correcta con WooCommerce 9.0"
    assert [call[0] for call in session.calls] == [
        "https://shop.example/wp-json/wc/v3/system_status",
        "https://shop.example/index.php?rest_route=/wc/v3/system_status",
    ]
    assert session.calls[1][1]["params"] == {"consumer_key": "ck", "consumer_secret": "cs"}


def test_uses_rest_route_fallback_after_connection_error() -> None:
    class FallbackSession:
        def __init__(self): self.calls = []
        def request(self, method, url, **kwargs):
            self.calls.append(url)
            if len(self.calls) == 1:
                raise requests.RequestException("connection closed")
            return Response(200, {"environment": {"version": "9.0"}})

    session = FallbackSession()
    client = WooCommerceClient("https://shop.example", "ck", "cs", session=session)
    assert client.test_connection() == "Conexión correcta con WooCommerce 9.0"
    assert session.calls[1] == "https://shop.example/index.php?rest_route=/wc/v3/system_status"
