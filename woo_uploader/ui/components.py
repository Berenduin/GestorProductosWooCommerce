from __future__ import annotations

from typing import Any

import flet as ft

from .theme import GOLD, PURPLE, WHITE


def modern_text_field(label: str | None, hint_text: str = "", icon: Any = None, **kwargs: Any) -> ft.TextField:
    return ft.TextField(label=label, hint_text=hint_text, prefix_icon=icon, bgcolor="#FAF8F9", border_color="#D8CDD0", focused_border_color=GOLD, focused_border_width=2, border_radius=12, hint_style=ft.TextStyle(color="#887C80", italic=True), **kwargs)


def modern_dropdown(**kwargs: Any) -> ft.Dropdown:
    return ft.Dropdown(bgcolor="#FAF8F9", border_color="#D8CDD0", focused_border_color=GOLD, focused_border_width=2, border_radius=12, hint_style=ft.TextStyle(color="#887C80", italic=True), **kwargs)


def section(title: str, hint: str, controls: list[ft.Control]) -> ft.Container:
    return ft.Container(content=ft.Column([ft.Text(title, size=19, weight=ft.FontWeight.BOLD, color=PURPLE), ft.Text(hint, color="#665B5E"), *controls], spacing=10), bgcolor="#FAF8F9", border_radius=12, padding=16, shadow=ft.BoxShadow(spread_radius=1, blur_radius=6, color="#55000000", offset=ft.Offset(0, 2)))


def acknowledgement_dialog(title: str, message: str, close: Any, error: bool = False) -> ft.AlertDialog:
    return ft.AlertDialog(modal=True, title=ft.Text(title, color=ft.Colors.RED_700 if error else PURPLE), content=ft.Text(message), actions=[ft.ElevatedButton("Entendido", on_click=lambda _: close())])


def primary_button(text: str, on_click: Any, icon: Any = None, **kwargs: Any) -> ft.ElevatedButton:
    return ft.ElevatedButton(text, icon=icon, on_click=on_click, style=ft.ButtonStyle(bgcolor=PURPLE, color=WHITE), **kwargs)
