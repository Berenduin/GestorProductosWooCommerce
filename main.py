from __future__ import annotations

import flet as ft

from woo_uploader.app_controller import AppController
from woo_uploader.ui.theme import configure_page


def main(page: ft.Page) -> None:
    configure_page(page)
    AppController(page).start()


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
