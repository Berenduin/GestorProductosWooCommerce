# Subidor de productos WooCommerce

Aplicación de escritorio en Flet para crear y actualizar productos simples de WooCommerce de uno en uno o desde un Excel.

## Desarrollo

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/flet run main.py
```

En **Configuración**, indique la URL de la tienda y las claves REST de WooCommerce. Para subir imágenes locales, WordPress debe aceptar esas credenciales en su endpoint de medios; si no lo hace, rellene opcionalmente el usuario y contraseña de aplicación de WordPress.

La importación toma la primera hoja y usa la primera fila como cabeceras. Antes de enviar, se puede asignar cada columna a un campo y revisar las filas.
