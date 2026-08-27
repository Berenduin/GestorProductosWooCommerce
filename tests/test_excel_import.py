from pathlib import Path

from openpyxl import Workbook

from woo_uploader.excel_import import build_products, find_image, infer_mapping, read_spreadsheet


def test_reads_headers_maps_rows_and_finds_case_insensitive_image(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Referencia", "Título", "Precio"])
    sheet.append(["ABC-1", "Producto uno", 12.5])
    source = tmp_path / "productos.xlsx"
    workbook.save(source)
    (tmp_path / "abc-1.WeBp").touch()

    spreadsheet = read_spreadsheet(source)
    results = build_products(spreadsheet, {"Referencia": "sku", "Título": "name", "Precio": "regular_price"}, "Referencia", tmp_path)
    assert spreadsheet.headers == ["Referencia", "Título", "Precio"]
    assert results[0].valid
    assert results[0].product.image_path.name == "abc-1.WeBp"
    assert find_image(tmp_path, "ABC-1") == results[0].product.image_path


def test_rejects_duplicate_headers(tmp_path: Path) -> None:
    workbook = Workbook(); workbook.active.append(["SKU", "SKU"])
    source = tmp_path / "bad.xlsx"; workbook.save(source)
    try:
        read_spreadsheet(source)
    except ValueError as exc:
        assert "únicas" in str(exc)
    else:
        raise AssertionError("Se esperaban cabeceras duplicadas inválidas")


def test_infer_mapping_recognizes_common_spanish_headers() -> None:
    mapping = infer_mapping(["Referencia", "Título", "Precio", "Categorías", "Campo auxiliar"])

    assert mapping == {
        "Referencia": "sku",
        "Título": "name",
        "Precio": "regular_price",
        "Categorías": "categories",
        "Campo auxiliar": "ignore",
    }
