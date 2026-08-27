# Gestor de productos · El Baúl de la Tuna

Aplicación de escritorio en Flet para crear y actualizar productos simples de WooCommerce de uno en uno o desde un Excel.

## Distribución para Windows

La aplicación se distribuye como instalador, por lo que la persona cliente no necesita instalar Python. Antes de crear una entrega, cambia de forma coordinada la versión de `pyproject.toml` y `woo_uploader/version.py`.

Desde un equipo Windows, instala Python 3.11 o posterior e [Inno Setup](https://jrsoftware.org/isinfo.php). Después ejecuta en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[build]"
.\scripts\build_instalador_windows.ps1
```

El instalador se genera en `installer\output`. La primera versión se puede compartir mediante un enlace de descarga; no conviene adjuntar ejecutables directamente por correo. El apartado **Configuración → Actualizaciones** muestra la versión instalada y queda preparado para incorporar la comprobación y descarga de futuras Releases.

## Desarrollo y validación

Se necesita Python 3.11 o posterior. Cree un entorno virtual e instale las
dependencias de desarrollo antes de ejecutar la aplicación o las pruebas.

### Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/flet run main.py
.venv/bin/pytest -q
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e '.[dev]'
flet run main.py
pytest -q
```

Si la política de ejecución de PowerShell bloquea la activación del entorno,
puede omitirla y llamar directamente a sus ejecutables:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\flet.exe run main.py
.\.venv\Scripts\pytest.exe -q
```

En **Configuración**, indique la URL de la tienda y las claves REST de WooCommerce. Para subir imágenes locales, WordPress debe aceptar esas credenciales en su endpoint de medios; si no lo hace, rellene opcionalmente el usuario y contraseña de aplicación de WordPress.

La importación toma la primera hoja activa y usa la primera fila como cabeceras. Antes de enviar, se valida y previsualiza el lote.

## Arquitectura

La aplicación sigue la dirección de dependencias **interfaz → servicios → dominio/infraestructura**. Las reglas de negocio y las peticiones HTTP nunca deben incorporarse a una vista Flet.

| Capa | Responsabilidad |
| --- | --- |
| `main.py` | Arranque de Flet y composición mínima de la aplicación. |
| `woo_uploader/app_controller.py` | Estado de sesión, navegación, diálogos, mensajes, selectores de archivos y configuración cargada. |
| `woo_uploader/ui/` | Controles Flet, tema y presentación de los resultados en español. |
| `woo_uploader/services/` | Casos de uso de conexión, subida individual, lote e informe CSV; no depende de Flet. |
| `woo_uploader/models.py` | Producto de entrada, normalización, validación y payload de WooCommerce. |
| `woo_uploader/excel_import.py` | Lectura de Excel, asociación de cabeceras y búsqueda local de imágenes. |
| `woo_uploader/woocommerce.py` | Único adaptador HTTP de WordPress/WooCommerce. |

Las vistas pueden convertir controles en `ProductInput`, validar mediante el dominio y mostrar diálogos. La detección de SKU, la elección técnica entre crear/actualizar/omitir y la serialización de resultados se delegan a los servicios. `WooCommerceClient` continúa siendo la única clase que conoce rutas REST, autenticación y reintentos.

## Flujos de uso

### Producto individual

1. La vista reúne y valida los campos obligatorios: nombre, SKU, precio y una única categoría. El alto es opcional; las etiquetas sí pueden separarse por comas.
2. El servicio consulta el SKU. Si existe, la interfaz ofrece actualizar u omitir.
3. El servicio crea o actualiza el producto y devuelve un resultado tipado para que la vista lo presente.

### Importación por lote

1. `excel_import` lee el Excel, infiere las cabeceras y localiza imágenes opcionales.
2. La vista muestra la validación. Si alguna fila no es válida, no inicia la subida.
3. El servicio busca conflictos de SKU y la interfaz recoge la decisión por fila.
4. El servicio procesa el lote, notifica el avance mediante un callback y devuelve el resumen por filas.
5. El escritor de informes crea `resultado_subida_lote.csv` en el directorio de trabajo, con UTF-8 con BOM.

Durante cualquier comprobación o subida remota se muestra un modal no descartable. Bloquea la interacción para evitar modificaciones concurrentes y, en el lote, muestra el número de filas procesadas. La ejecución de lote es deliberadamente síncrona para conservar el comportamiento existente; por ello el botón Cancelar no se muestra durante la carga. Una evolución futura será ejecutar ese servicio de forma asíncrona para que la cancelación sea realmente interactiva durante cargas largas.

## Configuración y seguridad

La configuración no sensible se guarda en el directorio de configuración de la plataforma. Las claves REST y la contraseña de aplicación de WordPress se guardan exclusivamente en el llavero del sistema. No añada URL privadas, claves, contraseñas ni contenido del llavero al repositorio, a pruebas o a mensajes de error.

## Pruebas

Las pruebas no contactan una tienda real. Cubren validación/payload, lectura de Excel, configuración, rutas REST y los servicios de subida con clientes falsos. Al modificar una regla de negocio, añada la prueba correspondiente en la capa de dominio o servicio antes de cambiar la vista.

## Hoja de ruta de refactorización

- Completado: separar arranque, controlador, UI, servicios de aplicación e informe de lote; mantener la UX y los artefactos existentes.
- Pendiente: mover la ejecución del lote a una tarea asíncrona, conservando los contratos de `BatchUploadService` y añadiendo pruebas de progreso/cancelación en la interfaz.
- Pendiente: añadir pruebas ligeras de construcción de vistas cuando Flet ofrezca un entorno de prueba estable para esta versión.
