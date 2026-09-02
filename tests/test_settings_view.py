import flet as ft

from woo_uploader.ui.settings_view import _show_connection_feedback


class Page:
    def __init__(self) -> None:
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


def test_connection_feedback_is_made_visible() -> None:
    page = Page()
    feedback = ft.Text(visible=False)

    _show_connection_feedback(page, feedback, "Conexión correcta")

    assert feedback.visible is True
    assert feedback.value == "Conexión correcta"
    assert feedback.color == ft.Colors.GREEN_700
    assert page.updates == 1


def test_connection_error_feedback_uses_error_color() -> None:
    page = Page()
    feedback = ft.Text(visible=False)

    _show_connection_feedback(page, feedback, "Credenciales incorrectas", True)

    assert feedback.visible is True
    assert feedback.value == "Credenciales incorrectas"
    assert feedback.color == ft.Colors.RED_700
