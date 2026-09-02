from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ..excel_import import Spreadsheet, build_products, infer_mapping, read_spreadsheet
from ..services.reports import BatchReportPaths, write_batch_reports
from ..services.uploads import BatchUploadResult, BatchUploadService, DuplicateAction, SkuConflict
from .components import acknowledgement_dialog, modern_dropdown, primary_button
from .theme import GOLD, PURPLE

if TYPE_CHECKING:
    from ..app_controller import AppController


@dataclass
class BatchImportState:
    sheet: Spreadsheet | None = None
    image_directory: str = ""
    cancelled: bool = False


def build_bulk_import_view(app: AppController) -> ft.Control:
    state = BatchImportState()
    file_label = ft.Text("Aún no has seleccionado el Excel del lote.")
    directory_label = ft.Text("Opcional: selecciona una carpeta si quieres asociar fotos.")
    preview_area = ft.Column()
    image_column = modern_dropdown(label="Columna usada como nombre de foto (opcional)", hint_text="Selecciona una columna", prefix_icon=ft.Icons.IMAGE_OUTLINED)
    import_status = modern_dropdown(label="Estado de los productos del lote", value=app.settings.default_status, prefix_icon=ft.Icons.VISIBILITY_OUTLINED, options=[ft.dropdown.Option("draft", "Borrador"), ft.dropdown.Option("publish", "Publicado")])
    service = BatchUploadService(app.create_client)

    def step_title(number: str, title: str, icon: str) -> ft.Row:
        return ft.Row([
            ft.Container(ft.Icon(icon, color=PURPLE, size=22), bgcolor="#E9DDE1", border_radius=20, padding=8),
            ft.Column([ft.Text(f"Paso {number}", size=12, color="#665B5E"), ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=PURPLE)], spacing=0),
        ], spacing=10)

    def image_notice() -> None:
        app.open_dialog(acknowledgement_dialog("Fotos del lote (opcional)", "Para asociar fotos, elige una carpeta y después selecciona la columna que contiene el nombre de cada archivo. Los nombres deben coincidir. Se aceptan JPG, JPEG, PNG y WEBP.", app.close_dialog))

    def build_results():
        if not state.sheet:
            return []
        return build_products(state.sheet, infer_mapping(state.sheet.headers), image_column.value, state.image_directory or None)

    def preview() -> None:
        if not state.sheet:
            app.open_dialog(acknowledgement_dialog("Selecciona el lote primero", "Elige el archivo Excel que contiene los productos antes de validar el lote.", app.close_dialog, error=True))
            return
        results = build_results()
        valid_count = sum(result.valid for result in results)
        invalid = [result for result in results if not result.valid]
        image_status = ("Fotos: se buscarán en la carpeta seleccionada usando la columna elegida." if state.image_directory and image_column.value else "Fotos: hay una carpeta seleccionada, pero no una columna de imagen; los productos se subirán sin fotos." if state.image_directory else "Fotos: hay una columna seleccionada, pero no una carpeta; los productos se subirán sin fotos." if image_column.value else "Fotos: no se ha seleccionado carpeta ni columna; los productos se subirán sin fotos.")
        by_row = {result.product.row_number: result for result in results}
        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Fila", weight=ft.FontWeight.BOLD)), *[ft.DataColumn(ft.Text(header, weight=ft.FontWeight.BOLD)) for header in state.sheet.headers], ft.DataColumn(ft.Text("Estado", weight=ft.FontWeight.BOLD)), ft.DataColumn(ft.Text("Detalle", weight=ft.FontWeight.BOLD))], rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(str(row_number))), *[ft.DataCell(ft.Text(row.get(header, ""))) for header in state.sheet.headers], ft.DataCell(ft.Text("Válido" if by_row[row_number].valid else "Revisar", color=ft.Colors.GREEN_700 if by_row[row_number].valid else ft.Colors.RED_700, weight=ft.FontWeight.BOLD)), ft.DataCell(ft.Text("Listo para subir" if by_row[row_number].valid else "; ".join(by_row[row_number].errors), color=ft.Colors.GREEN_700 if by_row[row_number].valid else ft.Colors.RED_700))]) for row_number, row in state.sheet.rows], heading_row_color="#EEE8EC", border=ft.border.all(1, "#DDD4D9"), border_radius=8, column_spacing=22)
        preview_area.controls = [ft.Text(f"Validación completada: {valid_count} válidas y {len(invalid)} con errores.", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700 if not invalid else ft.Colors.RED_700), ft.Text(image_status, color="#665B5E"), ft.Container(ft.Column([ft.Row([table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO), height=440)]
        app.page.update()

    def select_excel(event: ft.FilePickerResultEvent) -> None:
        if not event.files:
            return
        try:
            state.sheet = read_spreadsheet(event.files[0].path)
            file_label.value = f"Lote seleccionado: {event.files[0].name} · {len(state.sheet.rows)} productos detectados."
            image_column.options = [ft.dropdown.Option(header) for header in state.sheet.headers]
            image_column.value = next((header for header in state.sheet.headers if header.casefold() in {"image", "imagen", "foto"}), None)
            preview()
        except (ValueError, OSError) as exc:
            app.notify(str(exc), True)

    def select_directory(event: ft.FilePickerResultEvent) -> None:
        if event.path:
            state.image_directory = event.path
            directory_label.value = event.path
            image_notice()
            preview() if state.sheet else app.page.update()

    app.batch_excel_picker.on_result = select_excel
    app.batch_directory_picker.on_result = select_directory

    def open_report_path(path: Path) -> None:
        try:
            app.open_local_path(path)
        except Exception as exc:
            app.notify(f"No se pudo abrir el informe: {exc}", True)

    def show_summary(result: BatchUploadResult, reports: BatchReportPaths) -> None:
        counts = result.counts
        summary = f"{counts['created']} creados, {counts['updated']} actualizados, {counts['skipped']} omitidos y {counts['failed']} fallidos."
        title, color = ("Subida del lote cancelada", GOLD) if result.cancelled else ("Subida del lote terminada con errores", ft.Colors.RED_700) if counts["failed"] else ("Lote subido correctamente", PURPLE)
        app.notify(f"{title}: {summary} Informe Excel disponible en {reports.xlsx}", counts["failed"] > 0)
        details: list[ft.Control] = [
            ft.Text("El proceso de importación ha terminado.", weight=ft.FontWeight.BOLD),
            ft.Text(summary),
            ft.Text("Se ha generado un informe Excel con el resumen y el detalle de cada producto."),
            ft.Text(str(reports.xlsx), selectable=True, color="#665B5E"),
        ]
        if result.failures:
            details.extend([ft.Text("Errores detectados:", weight=ft.FontWeight.BOLD), *[ft.Text(error) for error in result.failures[:5]]])
            if len(result.failures) > 5:
                details.append(ft.Text(f"Y {len(result.failures) - 5} errores más en el informe."))
        app.open_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(title, color=color),
            content=ft.Container(ft.Column(details, tight=True, scroll=ft.ScrollMode.AUTO), width=680, height=min(440, 120 + 42 * len(details))),
            actions=[
                ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN, on_click=lambda _: open_report_path(reports.xlsx.parent)),
                ft.ElevatedButton("Abrir informe Excel", icon=ft.Icons.TABLE_VIEW_OUTLINED, on_click=lambda _: open_report_path(reports.xlsx)),
                ft.TextButton("Cerrar", on_click=lambda _: app.close_dialog()),
            ],
        ))

    def perform_import(results, conflicts: dict[int, SkuConflict], decisions: dict[int, DuplicateAction]) -> None:
        state.cancelled = False
        app.begin_upload("Preparando la subida del lote…", show_progress=True)
        try:
            result = service.upload(results, import_status.value or "draft", decisions, conflicts, on_progress=app.update_upload_progress, is_cancelled=lambda: state.cancelled)
            show_summary(result, write_batch_reports(result))
        except Exception as exc:
            app.notify(str(exc), True)
            app.open_dialog(acknowledgement_dialog("No se pudo iniciar la subida del lote", str(exc), app.close_dialog, error=True))

    def run_import(_: ft.ControlEvent) -> None:
        if not state.sheet:
            app.notify("Selecciona el Excel del lote.", True)
            return
        results = build_results()
        errors = [result for result in results if not result.valid]
        if errors:
            app.notify(f"Hay {len(errors)} productos con errores. Corrígelos antes de subir el lote.", True)
            return
        app.begin_upload("Comprobando los SKU existentes…")
        try:
            conflicts = service.find_conflicts(results)
        except Exception as exc:
            app.close_dialog()
            app.notify(str(exc), True)
            return
        if not conflicts:
            perform_import(results, {}, {})
            return
        choices: dict[int, ft.Dropdown] = {}
        rows = []
        for row_number, conflict in conflicts.items():
            control = modern_dropdown(value="skip", width=160, options=[ft.dropdown.Option("skip", "Omitir"), ft.dropdown.Option("update", "Actualizar")])
            choices[row_number] = control
            location = " (en la papelera)" if conflict.existing_product.get("status") == "trash" else ""
            rows.append(ft.Row([ft.Text(f"Fila {row_number} — SKU {conflict.product.values.get('sku', '')} — producto #{conflict.existing_product['id']}{location}", expand=True), control]))
        def confirm(_: ft.ControlEvent) -> None:
            app.close_dialog()
            perform_import(results, conflicts, {row: DuplicateAction(control.value or "skip") for row, control in choices.items()})
        app.open_dialog(ft.AlertDialog(modal=True, title=ft.Text("SKU duplicados en el lote"), content=ft.Container(ft.Column([ft.Text("Indica qué hacer con cada producto cuyo SKU ya existe."), *rows], scroll=ft.ScrollMode.AUTO), width=700, height=min(400, 95 + 70 * len(rows))), actions=[ft.TextButton("Cancelar", on_click=lambda _: app.close_dialog()), ft.ElevatedButton("Continuar con el lote", on_click=confirm)]))

    return ft.Container(content=ft.Column([
        ft.Text("Carga varios productos desde un Excel en tres pasos. El lote se valida antes de enviarlo; no se modificará la tienda hasta confirmar la subida.", color="#665B5E"),
        step_title("1", "Selecciona el archivo Excel", ft.Icons.DESCRIPTION_OUTLINED),
        ft.Text("El archivo debe tener formato .xlsx y la primera fila debe contener las cabeceras de los productos.", size=13, color="#665B5E"),
        ft.Text("Para los escudos puedes incluir las columnas País, Comunidad o estado y Ciudad. Solo se aplicarán a las filas cuya categoría sea Escudos.", size=13, color="#665B5E"),
        ft.Row([
            primary_button("Seleccionar archivo Excel", lambda _: app.batch_excel_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["xlsx"]), ft.Icons.UPLOAD_FILE, tooltip="Selecciona el Excel con los productos que quieres revisar"),
            file_label,
        ]),
        preview_area,
        ft.Divider(),
        step_title("2", "Asocia fotos (opcional)", ft.Icons.IMAGE_OUTLINED),
        ft.Text("Elige la carpeta donde están las fotos y la columna del Excel que contiene el nombre de cada archivo.", size=13, color="#665B5E"),
        ft.Row([
            ft.OutlinedButton("Seleccionar carpeta de fotos", icon=ft.Icons.FOLDER_OPEN, tooltip="Elige la carpeta local que contiene las imágenes", on_click=lambda _: app.batch_directory_picker.get_directory_path()),
            directory_label,
        ]),
        image_column,
        ft.Divider(),
        step_title("3", "Valida y sube el lote", ft.Icons.CLOUD_UPLOAD_OUTLINED),
        ft.Text("Revisaremos los datos y los SKU existentes. Podrás decidir si actualizar u omitir cada producto duplicado antes de subir.", size=13, color="#665B5E"),
        ft.Row([
            import_status,
            primary_button("Validar y subir lote", run_import, ft.Icons.CLOUD_UPLOAD, tooltip="Valida el lote y, si no hay errores, inicia la subida"),
        ]),
    ], scroll=ft.ScrollMode.AUTO, spacing=12), padding=10)
