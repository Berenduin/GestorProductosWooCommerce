import pytest

from woo_uploader.services.connection import ConnectionService
from woo_uploader.woocommerce import WooCommerceClient, WooCommerceError


def test_woocommerce_test_requires_only_woocommerce_credentials(monkeypatch) -> None:
    monkeypatch.setattr(WooCommerceClient, "test_connection", lambda self: "WooCommerce correcto")

    assert ConnectionService().test_woocommerce("https://shop.example", "ck", "cs") == "WooCommerce correcto"


def test_wordpress_test_requires_application_credentials(monkeypatch) -> None:
    monkeypatch.setattr(WooCommerceClient, "test_wordpress_connection", lambda self: "WordPress correcto")

    assert ConnectionService().test_wordpress("https://shop.example", "admin", "app-pass") == "WordPress correcto"


@pytest.mark.parametrize(
    ("store_url", "user", "password"),
    [("", "admin", "app-pass"), ("https://shop.example", "", "app-pass"), ("https://shop.example", "admin", "")],
)
def test_wordpress_test_reports_missing_fields(store_url, user, password) -> None:
    with pytest.raises(WooCommerceError, match="Complete la URL, el usuario y la contraseña"):
        ConnectionService().test_wordpress(store_url, user, password)
