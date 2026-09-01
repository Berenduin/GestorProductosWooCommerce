# Historial de cambios

Este archivo registra los cambios relevantes de cada versión de **Gestor de
productos · El Baúl de la Tuna**. Las novedades todavía no distribuidas se
mantienen en la sección **Sin publicar** hasta preparar una nueva entrega.

## [Sin publicar]

### Añadido

- Consulta de productos publicados organizada por las categorías configuradas.
- Columnas de País, Comunidad o estado y Ciudad en la tabla de productos de la
  categoría Escudos.
- Campos de ubicación para escudos en el formulario individual, conectados con
  las taxonomías `ebdlt_pais`, `ebdlt_region` y `ebdlt_ciudad` de WordPress.
- Compatibilidad con País, Comunidad o estado y Ciudad en la importación por
  Excel; estos valores solo se aplican a las filas de la categoría Escudos.
- Normalización automática de la mayúscula inicial en las ubicaciones de los
  escudos.
- Documentación para exponer y guardar las taxonomías de escudos mediante la API
  de WooCommerce.

### Cambiado

- El SKU ha dejado de ser obligatorio al crear un producto individual.
- La sección de organización aparece inmediatamente después del precio y solo
  muestra los campos de ubicación al seleccionar la categoría Escudos.
- El inventario utiliza las opciones excluyentes Bajo pedido y En stock. Bajo
  pedido es la opción predeterminada y bloquea el campo Cantidad; En stock lo
  habilita y exige una cantidad mayor que cero.
- Producto destacado y Publicación utilizan botones de opción siempre visibles.
- Peso, Largo, Ancho y Alto aparecen en una misma fila, con un separador entre el
  peso en kilogramos y las dimensiones en centímetros.
- Se han ampliado las pruebas del modelo, la importación Excel, los servicios de
  subida y la construcción del formulario individual.

## [0.1.0] — 2026-08-28

### Añadido

- Primera versión distribuible de la aplicación de escritorio para crear y
  actualizar productos simples de WooCommerce.
- Formulario de subida individual con validación, imagen opcional y detección de
  SKU existentes para actualizar u omitir productos.
- Importación de productos por lotes desde archivos Excel, con vista previa,
  asociación opcional de imágenes y gestión de SKU duplicados.
- Informe `resultado_subida_lote.csv` con el resultado detallado de cada lote.
- Configuración de categorías, estado de publicación y conexión con WooCommerce.
- Almacenamiento de credenciales sensibles en el llavero del sistema.
- Cliente para las API REST de WooCommerce y WordPress, incluida una ruta
  alternativa cuando falla la ruta REST habitual.
- Pantallas de ayuda, configuración y estado de la aplicación en español.
- Pruebas unitarias sin conexión a una tienda real.
- Script de construcción para Windows e instalador mediante Inno Setup.
- Guía para preparar y publicar instaladores mediante GitHub Releases.
