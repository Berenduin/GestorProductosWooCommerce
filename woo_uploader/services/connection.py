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
