# Publicar versiones en GitHub

Esta guía explica cómo publicar el instalador de **Gestor de productos · El Baúl de la Tuna** en GitHub para que las personas usuarias lo descarguen.

Una *release* es una página de GitHub asociada a una versión concreta del código. En ella se adjunta el instalador `.exe`. No hace falta subir ese archivo al repositorio ni hacer `git add` del instalador.

## Antes de la primera publicación

Necesitas:

- Una cuenta de GitHub.
- Un repositorio de GitHub que contenga este proyecto.
- Permiso de escritura en ese repositorio. Si eres su propietario, ya lo tienes.
- Tener instalado Git y haber enviado el código al repositorio al menos una vez.

> GitHub crea automáticamente archivos ZIP y TAR del código fuente. Esos archivos **no son el instalador de Windows**. El archivo que hay que adjuntar manualmente es el `.exe` generado en `installer/output`.

## Idea general

Cada publicación sigue este orden:

1. Decidir la nueva versión.
2. Actualizar el número de versión en el proyecto.
3. Probar y generar el instalador.
4. Guardar el código de esa versión en Git y enviarlo a GitHub.
5. Crear una release en la web de GitHub y adjuntar el instalador.
6. Publicar y compartir el enlace de descarga.

Es importante que el número de la versión del instalador, la etiqueta de GitHub y el código enviado sean el mismo.

## Elegir el número de versión

Se usa el formato `MAYOR.MENOR.PARCHE`, por ejemplo `1.2.3`.

| Cambio realizado | Ejemplo | Cuándo usarlo |
| --- | --- | --- |
| Parche | `1.0.0` → `1.0.1` | Correcciones pequeñas sin cambiar el uso normal. |
| Menor | `1.0.0` → `1.1.0` | Nuevas funciones compatibles. |
| Mayor | `1.0.0` → `2.0.0` | Cambios importantes que alteran el flujo o la compatibilidad. |

Para una primera publicación se recomienda `1.0.0`, en lugar de `0.1.0`.

## Preparar una versión

### 1. Actualizar el número de versión

Edita de forma coordinada estos dos archivos:

- `pyproject.toml`: la línea `version = "..."`.
- `woo_uploader/version.py`: la constante de versión.

Por ejemplo, cambia ambos valores a `1.0.0`.

### 2. Guardar y enviar el código a GitHub

Desde la raíz del proyecto, en PowerShell:

```powershell
git status
git add .
git commit -m "Publicar versión 1.0.0"
git push
```

Antes de confirmar, revisa siempre la salida de `git status`. No deben aparecer secretos, configuraciones personales ni instaladores dentro de los archivos preparados para el commit.

### 3. Generar el instalador

Ejecuta:

```powershell
.\scripts\build_instalador_windows.ps1
```

El archivo que se distribuirá quedará en:

```text
installer\output\Instalador-Gestor de productos · El Baúl de la Tuna-VERSION.exe
```

Por ejemplo, para la versión `1.0.0`:

```text
installer\output\Instalador-Gestor de productos · El Baúl de la Tuna-1.0.0.exe
```

No cierres PowerShell hasta que el script termine sin errores.

### 4. Comprobar el instalador

Como mínimo, comprueba que el archivo existe y que su tamaño tiene decenas de MB, no unos pocos KB.

Para obtener su huella de verificación:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "installer\output\Instalador-Gestor de productos · El Baúl de la Tuna-1.0.0.exe"
```

Guarda el resultado: puedes incluirlo en las notas de la release para que otra persona pueda comprobar que descargó el archivo correcto.

Si es posible, instala y abre el programa en otro ordenador Windows antes de publicarlo.

## Crear la release en la web de GitHub

1. Entra en la página principal del repositorio en GitHub.
2. Pulsa **Releases**, a la derecha de la lista de archivos o en la sección lateral del repositorio.
3. Pulsa **Draft a new release** (crear borrador de una nueva versión).
4. En **Choose a tag**, escribe `v1.0.0` y elige **Create new tag: v1.0.0**.
   - La `v` es una convención útil para distinguir la etiqueta de GitHub del número mostrado por la aplicación.
   - En **Target**, selecciona la rama que acabas de enviar, normalmente `main`.
5. En **Release title**, escribe `Gestor de productos 1.0.0`.
6. En **Describe this release**, escribe las notas de la versión. Puedes usar el modelo de la siguiente sección.
7. En la zona para archivos binarios, arrastra o selecciona el instalador `.exe` de `installer/output`.
8. Espera a que termine la subida y comprueba que aparece el nombre completo del archivo.
9. Para una versión de prueba, marca **This is a pre-release**. Para una versión lista para usuarios, déjalo sin marcar.
10. Pulsa **Publish release**.

GitHub mostrará una página propia para esa versión. El enlace que puedes compartir suele tener esta forma:

```text
https://github.com/USUARIO/REPOSITORIO/releases/latest
```

Ese enlace siempre lleva a la última release publicada. El enlace de una versión concreta incluye la etiqueta, por ejemplo `.../releases/tag/v1.0.0`.

## Modelo de notas de versión

Puedes copiar y adaptar este texto:

```markdown
## Gestor de productos 1.0.0

### Novedades
- Primera versión pública del gestor de productos para WooCommerce.

### Instalación
1. Descarga el archivo `Instalador-Gestor de productos · El Baúl de la Tuna-1.0.0.exe` de esta página.
2. Ábrelo y sigue el asistente.
3. Si Windows muestra un aviso por ser una aplicación nueva, confirma solo si has descargado el archivo desde esta release oficial.

### Verificación
SHA-256: PEGA_AQUI_LA_HUELLA_GENERADA
```

Describe también cualquier corrección o función añadida desde la versión anterior. Evita incluir claves de WooCommerce, contraseñas, direcciones privadas o datos de clientes.

## Editar una release ya creada

En GitHub:

1. Ve a **Releases** en el repositorio.
2. Busca la versión que quieres modificar.
3. Pulsa el icono de lápiz (**Edit**).
4. Cambia el título, las notas o los archivos adjuntos necesarios.
5. Pulsa **Update release**.

Puedes añadir o eliminar el instalador adjunto desde esa pantalla. Sin embargo, si el instalador publicado contiene un error real, la práctica recomendable es crear una versión nueva de parche, por ejemplo `1.0.1`, en vez de sustituir silenciosamente el archivo de `1.0.0`. Así queda claro qué ha instalado cada persona.

Si la release todavía no está lista, usa **Save draft** en lugar de publicarla. Un borrador no se muestra como versión pública.

## Publicar la siguiente versión

Para `1.0.1`, repite el mismo proceso:

1. Cambia la versión en `pyproject.toml` y `woo_uploader/version.py`.
2. Ejecuta las pruebas y genera el instalador.
3. Haz `git add`, `git commit` y `git push`.
4. Crea la release con etiqueta `v1.0.1`.
5. Adjunta únicamente el instalador `...-1.0.1.exe`.
6. Publica la release y comparte `.../releases/latest`.

## Problemas frecuentes

### No veo el botón Releases

Entra en la página principal del repositorio y revisa la sección lateral. Si el repositorio no es tuyo, quizá no tienes permisos para publicar: pide acceso de escritura a la persona propietaria.

### El instalador no se puede subir

Comprueba que has elegido el `.exe` de `installer/output`, que el script de empaquetado terminó correctamente y que el archivo no está abierto en otro programa. No intentes subir la carpeta `dist` completa.

### He publicado una versión con un error

Si el problema está en el programa o en el instalador, crea una nueva versión de parche. Si solo hay un error de texto en las notas, edita la release existente con el lápiz.

### Quiero retirar una release

En **Releases**, abre la edición de esa versión y usa **Delete this release**. Hazlo solo si estás seguro: si otras personas ya la descargaron, no recibirán automáticamente una corrección. Publicar una versión nueva suele ser preferible.

## Referencias oficiales

- [Administrar lanzamientos en un repositorio — GitHub Docs](https://docs.github.com/es/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [Acerca de los lanzamientos — GitHub Docs](https://docs.github.com/es/repositories/releasing-projects-on-github/about-releases)
