from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import keyring
from keyring.errors import PasswordDeleteError
from platformdirs import user_config_path

SERVICE = "woo-product-uploader"
DEFAULT_CATEGORIES = (
    "Banderas",
    "Becas",
    "Capa",
    "Cintas",
    "Escudos",
    "Percusión y accesorios",
    "Prendas Personalizadas",
    "Vestimenta de Tuna",
    "Zurrones",
)


@dataclass
class Settings:
    store_url: str = ""
    wordpress_user: str = ""
    default_status: str = "draft"
    categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))


class SettingsStore:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Path(user_config_path("woo-product-uploader"))
        self.path = self.config_dir / "settings.json"

    def load(self) -> Settings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data.get("categories", list(DEFAULT_CATEGORIES)), list):
                data["categories"] = list(DEFAULT_CATEGORIES)
            return Settings(**data)
        except (OSError, ValueError, TypeError):
            return Settings()

    def save(self, settings: Settings, consumer_key: str, consumer_secret: str, wordpress_password: str = "") -> None:
        self.save_settings(settings)
        self._set_secret("consumer_key", consumer_key)
        self._set_secret("consumer_secret", consumer_secret)
        self._set_secret("wordpress_password", wordpress_password)

    def save_settings(self, settings: Settings) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")

    def credentials(self) -> tuple[str, str, str]:
        return (self._get_secret("consumer_key"), self._get_secret("consumer_secret"), self._get_secret("wordpress_password"))

    @staticmethod
    def _set_secret(name: str, value: str) -> None:
        if value:
            keyring.set_password(SERVICE, name, value)
        else:
            try:
                keyring.delete_password(SERVICE, name)
            except PasswordDeleteError:
                pass

    @staticmethod
    def _get_secret(name: str) -> str:
        return keyring.get_password(SERVICE, name) or ""
