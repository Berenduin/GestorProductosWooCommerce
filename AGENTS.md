# Contexto del proyecto

## Propósito

Aplicación de escritorio en Python para crear y actualizar productos **simples**
en WooCommerce. Está pensada para el catálogo de El Baúl de la Tuna y permite
dos flujos: alta/actualización de un producto desde un formulario y carga por
lotes desde un libro de Excel.

La interfaz y los textos de usuario están en español. Mantener este idioma al
añadir pantallas, validaciones y mensajes de error.

## Arquitectura

- `main.py`: composición de la interfaz Flet y coordinación de los flujos. No
  debe contener lógica de serialización ni detalles HTTP nuevos si pueden vivir
  en los módulos de `woo_uploader`.
- `woo_uploader/models.py`: modelo de entrada, normalización, validación y
  conversión de un producto a un payload de WooCommerce.
- `woo_uploader/excel_import.py`: lectura de la hoja activa de `.xlsx`,
  asociación de columnas y localización opcional de imágenes locales.
- `woo_uploader/woocommerce.py`: único adaptador de red para WordPress y
  WooCommerce. Convierte errores de `requests` en `WooCommerceError`.
- `woo_uploader/config.py`: configuración no sensible y acceso al llavero del
  sistema.
- `tests/`: pruebas unitarias sin red y sin una tienda real.
- `assets/`: recursos visuales cargados por Flet; conservar sus nombres salvo
  que también se actualicen sus referencias en `main.py`.

## Infraestructura y dependencias

- Python 3.11 o posterior, definido en `pyproject.toml`.
- Flet 0.25.x para la aplicación de escritorio.
- `requests` para la API REST.
- `openpyxl` para importar archivos `.xlsx`; solo se usa la primera hoja
  activa y su primera fila son cabeceras.
- `keyring` para los secretos del sistema y `platformdirs` para hallar el
  directorio de configuración de cada plataforma.
- `pytest` como dependencia de desarrollo.

Instalación y ejecución de desarrollo:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/flet run main.py
pytest -q
```

No hay servicios locales, base de datos ni backend propio. La infraestructura
remota es una instalación de WordPress con WooCommerce y su API REST.

## Conexión remota

La URL configurada es la raíz de la tienda. Puede introducirse con o sin el
sufijo `/wp-json`; el cliente lo normaliza.

| Uso | Ruta REST principal | Ruta alternativa ante 404 o fallo de conexión |
| --- | --- | --- |
| Comprobar conexión | `/wp-json/wc/v3/system_status` | `/?rest_route=/wc/v3/system_status` mediante `index.php` |
| Buscar por SKU | `/wp-json/wc/v3/products?sku=…&per_page=1` | equivalente con `rest_route` |
| Crear producto | `POST /wp-json/wc/v3/products` | equivalente con `rest_route` |
| Actualizar producto | `PUT /wp-json/wc/v3/products/{id}` | equivalente con `rest_route` |
| Subir medio | `POST /wp-json/wp/v2/media` | equivalente con `rest_route` |

La autenticación ordinaria usa la pareja de claves REST de WooCommerce. Para
la subida de medios se usan esas mismas claves salvo que se hayan configurado
usuario y contraseña de aplicación de WordPress, que tienen prioridad. Las
solicitudes tienen un tiempo de espera general de 30 segundos y de 60 segundos
para medios.

No registrar, incorporar a pruebas, ni guardar en el repositorio URL privadas,
Consumer Key, Consumer Secret, contraseñas de aplicación ni contenido del
llavero.

## Configuración local y secretos

- La configuración no sensible se guarda como `settings.json` bajo
  `platformdirs.user_config_path("woo-product-uploader")`.
- Contiene `store_url`, `wordpress_user`, `default_status` y categorías.
- Los secretos se guardan con el servicio de llavero
  `woo-product-uploader`: `consumer_key`, `consumer_secret` y
  `wordpress_password`.
- Los valores por defecto incluyen las categorías de `DEFAULT_CATEGORIES` y el
  estado `draft`.

## Reglas de negocio importantes

- Solo se envían productos de tipo `simple`.
- El formulario individual exige nombre, SKU, precio y categoría. La lógica de
  lote mantiene una validación más genérica; no estrecharla sin adaptar la UX y
  sus pruebas.
- Un SKU ya existente puede actualizarse u omitirse, nunca se crea un segundo
  producto con ese SKU desde los flujos previstos.
- Las categorías y etiquetas se separan por comas y se envían como objetos con
  `name`.
- Los decimales admiten coma y se convierten a punto solo para validarlos; el
  payload conserva el valor de entrada.
- Las imágenes de lote se buscan en la carpeta elegida sin distinguir
  mayúsculas, por nombre completo o por nombre sin extensión. Se aceptan JPG,
  JPEG, PNG y WEBP.
- Cada lote genera `resultado_subida_lote.csv` en el directorio de trabajo.
  Es un artefacto de ejecución, no una fuente de la aplicación.

## Pautas de cambio

- Añadir o modificar campos de WooCommerce en `FIELD_LABELS`, validación y
  `to_woo_payload` de forma coherente; después ajustar el formulario y las
  pruebas necesarias.
- Conservar el uso de `WooCommerceError` para errores mostrables al usuario.
- Si se modifica el comportamiento de reintento/fallback REST o autenticación,
  ampliar `tests/test_woocommerce.py` con sesiones falsas: las pruebas no
  deben contactar una tienda real.
- No validar ni ejecutar cargas reales contra producción durante el desarrollo
  automatizado. Usar simulaciones en pruebas o una tienda de staging indicada
  expresamente por la persona usuaria.
- Antes de dar por terminado un cambio de código, ejecutar `pytest -q`.
