from __future__ import annotations

import flet as ft

PURPLE = "#623642"
GOLD = "#FFBA00"
LIGHT_GRAY = "#F4F4F4"
WHITE = "#FFFFFF"
BLACK = "#1F1F1F"


def configure_page(page: ft.Page) -> None:
    page.title = "Gestor de productos · El Baúl de la Tuna"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = LIGHT_GRAY
    page.theme = ft.Theme(
        use_material3=True,
        scaffold_bgcolor=LIGHT_GRAY,
        card_color=WHITE,
        divider_color=GOLD,
        color_scheme=ft.ColorScheme(
            primary=PURPLE, on_primary=WHITE, primary_container="#E9DDE1", on_primary_container=PURPLE,
            secondary=GOLD, on_secondary=BLACK, secondary_container="#FFF0C7", on_secondary_container=BLACK,
            surface=WHITE, on_surface=BLACK, background=LIGHT_GRAY, on_background=BLACK, outline="#BDB5B7",
        ),
    )
    page.padding = 20
    page.window.min_width = 920
    page.window.min_height = 700
    page.window.maximized = True
