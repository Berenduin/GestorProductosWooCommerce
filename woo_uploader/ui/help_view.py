from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

import flet as ft

from .components import primary_button, section
from .theme import PURPLE

if TYPE_CHECKING:
    from ..app_controller import AppController


WHATSAPP_SUPPORT_URL = "https://wa.me/34673120842?text=" + quote(
    "Hola, necesito ayuda con Gestor de productos · El Baúl de la Tuna.\n\n"
    "Estoy intentando: \n"
    "El mensaje de error es: \n"
)


def _guide_step(number: str, title: str, text: str) -> ft.Row:
    return ft.Row([
        ft.Container(ft.Text(number, color="white", weight=ft.FontWeight.BOLD), bgcolor=PURPLE, border_radius=16, width=28, height=28, alignment=ft.alignment.center),
        ft.Column([ft.Text(title, weight=ft.FontWeight.BOLD), ft.Text(text, color="#665B5E")], spacing=2, expand=True),
    ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=10)


def _info_item(icon: str, title: str, text: str) -> ft.Row:
    return ft.Row([
        ft.Icon(icon, color=PURPLE, size=24),
        ft.Column([ft.Text(title, weight=ft.FontWeight.BOLD), ft.Text(text, color="#665B5E")], spacing=2, expand=True),
    ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=10)


def build_help_view(app: AppController) -> list[ft.Control]:
    connection_steps = [
        _guide_step("1", "Abre el panel de WordPress", "Entra en la administración de tu tienda con una cuenta que pueda gestionar WooCommerce."),
        _guide_step("2", "Crea las claves de WooCommerce", "Ve a WooCommerce → Ajustes → Avanzado → API REST y pulsa «Añadir clave» o «Crear una clave API»."),
        _guide_step("3", "Elige los permisos adecuados", "Pon una descripción como «Gestor de productos», elige un usuario con permisos para gestionar productos y selecciona «Lectura/Escritura». Después genera la clave."),
        _guide_step("4", "Copia los dos valores", "WooCommerce mostrará Consumer Key y Consumer Secret. Copia ambos antes de cerrar la pantalla: el secreto solo se muestra una vez."),
    ]
    application_password_steps = [
        _guide_step("1", "Usa este apartado solo si subes fotos", "El usuario y la contraseña de aplicación son opcionales. Se usan para enviar imágenes a la biblioteca de medios de WordPress."),
        _guide_step("2", "Crea una contraseña de aplicación", "En WordPress ve a Usuarios → Perfil, busca «Contraseñas de aplicación», escribe «Gestor de productos» y genera una nueva."),
        _guide_step("3", "Introduce el usuario y la contraseña generada", "Usa tu nombre de usuario de WordPress y esa contraseña especial; no introduzcas tu contraseña habitual de WordPress."),
    ]
    return [
        ft.Text("Ayuda", size=26, weight=ft.FontWeight.BOLD, color=PURPLE),
        ft.Text("Guía sencilla para preparar la conexión y subir productos con seguridad.", color="#665B5E"),
        section("Subir un producto", "Para añadir o actualizar un producto de uno en uno.", [
            _guide_step("1", "Completa los datos obligatorios", "Escribe nombre, precio y una categoría. El SKU, el alto y el resto de medidas son opcionales."),
            _guide_step("2", "Añade etiquetas e imagen si las necesitas", "Las etiquetas pueden separarse por comas. La imagen puede ser JPG, JPEG, PNG o WEBP."),
            _guide_step("3", "Revisa y confirma", "La aplicación mostrará un resumen. Si ese SKU ya existe, podrás actualizarlo o dejarlo sin cambios."),
            _guide_step("4", "Espera al mensaje final", "Mientras se sube el producto aparecerá una ventana de progreso. No cierres ni uses la aplicación hasta que termine."),
            primary_button("Ir a subir un producto", lambda _: app.set_view("upload"), ft.Icons.UPLOAD_FILE),
        ]),
        section("Subir varios productos desde Excel", "Para cargar un lote completo sin necesidad de crear los productos uno a uno.", [
            _guide_step("1", "Prepara el Excel", "Guarda el archivo como .xlsx. La primera fila debe contener las cabeceras; cada fila posterior es un producto."),
            _guide_step("2", "Revisa la validación", "Después de seleccionar el Excel, comprueba la tabla. Corrige las filas marcadas como «Revisar» antes de subir."),
            _guide_step("3", "Asocia fotos, si quieres", "Elige la carpeta de imágenes y después la columna que contiene el nombre del archivo. Los nombres deben coincidir."),
            _guide_step("4", "Valida y sube", "Para cada SKU ya existente podrás decidir entre actualizar u omitir. Al finalizar se creará el informe resultado_subida_lote.csv."),
            primary_button("Ir a subir por lote", lambda _: app.set_view("upload", upload_tab=1), ft.Icons.CLOUD_UPLOAD_OUTLINED),
        ]),
        section("Categorías", "Gestiona las categorías que aparecerán al crear un producto.", [
            _info_item(ft.Icons.CATEGORY_OUTLINED, "Añade o elimina categorías", "En Configuración → Categorías puedes añadir nuevas opciones, cambiar un nombre o eliminar las que no uses."),
            _info_item(ft.Icons.LIST, "Elige una categoría por producto", "En el formulario de subida selecciona una sola categoría de esta lista."),
            primary_button("Ir a categorías", lambda _: app.set_view("settings"), ft.Icons.CATEGORY_OUTLINED),
        ]),
        section("Conexión", "Configura cómo se comunica la aplicación con WooCommerce.", [
            _info_item(ft.Icons.VISIBILITY_OUTLINED, "Estado predeterminado", "«Borrador» permite revisar los productos antes de publicarlos; «Publicado» los hace visibles inmediatamente."),
            _info_item(ft.Icons.CHECK_CIRCLE_OUTLINE, "Probar conexión", "Después de guardar los datos, usa este botón para comprobar que la tienda acepta la conexión."),
            primary_button("Ir a conexión", lambda _: app.set_view("settings", settings_tab=1), ft.Icons.SETTINGS),
        ]),
        section("Crear las claves de conexión", "Sigue estos pasos si todavía no dispones de Consumer Key y Consumer Secret.", [
            ft.Text("URL de la tienda", weight=ft.FontWeight.BOLD),
            ft.Text("Es la dirección principal de la tienda, por ejemplo https://mitienda.es. No hace falta añadir /wp-json."),
            ft.Divider(),
            ft.Text("Consumer Key y Consumer Secret", weight=ft.FontWeight.BOLD),
            *connection_steps,
            ft.Divider(),
            ft.Text("Usuario y contraseña de aplicación de WordPress", weight=ft.FontWeight.BOLD),
            *application_password_steps,
            ft.Container(ft.Text("Consejo de seguridad: no envíes estas claves por correo, capturas o mensajes. Si crees que se han compartido, elimínalas en WordPress/WooCommerce y crea otras nuevas.", color="#665B5E"), bgcolor="#FFF0C7", border_radius=8, padding=12),
        ]),
        section("Si algo no funciona", "Qué información dar a la persona que administra la tienda.", [
            ft.Text("Indica qué estabas intentando hacer, el texto completo del error y, si era un lote, la fila afectada. No compartas la Consumer Secret, la contraseña de aplicación ni capturas donde aparezcan."),
            ft.Text("Si no puedes crear las claves o no ves las contraseñas de aplicación, pide ayuda a la persona administradora de WordPress/WooCommerce.", color="#665B5E"),
            primary_button("Contactar por WhatsApp", None, ft.Icons.CHAT_OUTLINED, url=WHATSAPP_SUPPORT_URL, url_target=ft.UrlTarget.BLANK, tooltip="Abre WhatsApp Web con un mensaje de soporte preparado"),
        ]),
    ]
