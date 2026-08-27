import json

from woo_uploader.config import DEFAULT_CATEGORIES, SettingsStore


def test_loads_default_categories_when_the_setting_does_not_exist(tmp_path) -> None:
    store = SettingsStore(tmp_path)
    store.path.write_text(json.dumps({"store_url": "https://shop.example"}), encoding="utf-8")

    settings = store.load()

    assert settings.categories == list(DEFAULT_CATEGORIES)


def test_loads_saved_categories(tmp_path) -> None:
    store = SettingsStore(tmp_path)
    store.path.write_text(json.dumps({"categories": ["Cuerdas", "Accesorios"]}), encoding="utf-8")

    assert store.load().categories == ["Cuerdas", "Accesorios"]
