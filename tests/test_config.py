import json

from woo_uploader.config import DEFAULT_CATEGORIES, Settings, SettingsStore


def test_loads_default_categories_when_the_setting_does_not_exist(tmp_path) -> None:
    store = SettingsStore(tmp_path)
    store.path.write_text(json.dumps({"store_url": "https://shop.example"}), encoding="utf-8")

    settings = store.load()

    assert settings.categories == list(DEFAULT_CATEGORIES)


def test_loads_saved_categories(tmp_path) -> None:
    store = SettingsStore(tmp_path)
    store.path.write_text(json.dumps({"categories": ["Cuerdas", "Accesorios"]}), encoding="utf-8")

    assert store.load().categories == ["Cuerdas", "Accesorios"]


def test_saves_woocommerce_secrets_without_touching_wordpress_password(tmp_path, monkeypatch) -> None:
    saved: list[tuple[str, str]] = []
    monkeypatch.setattr(SettingsStore, "_set_secret", staticmethod(lambda name, value: saved.append((name, value))))
    store = SettingsStore(tmp_path)

    store.save_woocommerce(Settings(store_url="https://shop.example"), "ck_test", "cs_test")

    assert saved == [("consumer_key", "ck_test"), ("consumer_secret", "cs_test")]


def test_saves_wordpress_password_without_touching_woocommerce_secrets(tmp_path, monkeypatch) -> None:
    saved: list[tuple[str, str]] = []
    monkeypatch.setattr(SettingsStore, "_set_secret", staticmethod(lambda name, value: saved.append((name, value))))
    store = SettingsStore(tmp_path)

    store.save_wordpress(Settings(store_url="https://shop.example", wordpress_user="admin"), "app-pass")

    assert saved == [("wordpress_password", "app-pass")]
