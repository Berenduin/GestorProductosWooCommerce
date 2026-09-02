"""Caso de uso de conexión y validación de credenciales."""

from __future__ import annotations

from ..config import Settings
from ..woocommerce import WooCommerceClient, WooCommerceError


class ConnectionService:
    def create_client(self, settings: Settings, credentials: tuple[str, str, str]) -> WooCommerceClient:
        key, secret, wordpress_password = credentials
        if not settings.store_url or not key or not secret:
            raise WooCommerceError("Configure la URL y las claves API antes de subir productos.")
        return WooCommerceClient(settings.store_url, key, secret, settings.wordpress_user, wordpress_password)

    def test_connection(self, settings: Settings, credentials: tuple[str, str, str]) -> str:
        return self.create_client(settings, credentials).test_connection()

    def test_woocommerce(self, store_url: str, consumer_key: str, consumer_secret: str) -> str:
        if not store_url or not consumer_key or not consumer_secret:
            raise WooCommerceError("Complete la URL, la Consumer Key y la Consumer Secret antes de probar WooCommerce.")
        return WooCommerceClient(store_url, consumer_key, consumer_secret).test_connection()

    def test_wordpress(self, store_url: str, wordpress_user: str, wordpress_password: str) -> str:
        if not store_url or not wordpress_user or not wordpress_password:
            raise WooCommerceError("Complete la URL, el usuario y la contraseña de aplicación antes de probar WordPress.")
        return WooCommerceClient(
            store_url,
            "",
            "",
            wordpress_user,
            wordpress_password,
        ).test_wordpress_connection()
