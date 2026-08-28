# Exponer las taxonomías de escudos a la aplicación

La aplicación consulta `wc/v3/products`. Aunque las taxonomías del buscador usan
`show_in_rest`, WooCommerce no las incorpora automáticamente a la respuesta de
ese endpoint. Añade el siguiente cambio al archivo principal del plugin **El Baúl
— Buscador de Escudos**, sin modificar Divi ni PPOM.

1. En `EBDLT_Buscador_Escudos::init()`, añade esta línea:

```php
add_filter( 'woocommerce_rest_prepare_product_object', array( __CLASS__, 'incluir_ubicacion_en_api' ), 10, 3 );
```

2. Dentro de la misma clase, añade este método:

```php
public static function incluir_ubicacion_en_api( $response, $producto, $request ) {
	$datos = $response->get_data();
	foreach ( array( 'ebdlt_pais', 'ebdlt_region', 'ebdlt_ciudad' ) as $taxonomia ) {
		$terminos = wp_get_post_terms( $producto->get_id(), $taxonomia, array( 'fields' => 'names' ) );
		$datos[ $taxonomia ] = is_wp_error( $terminos ) ? array() : array_values( $terminos );
	}
	$response->set_data( $datos );
	return $response;
}
```

Tras activar ese cambio, cada producto de `wc/v3/products` incluirá las claves
`ebdlt_pais`, `ebdlt_region` y `ebdlt_ciudad`. La pestaña **Escudos** de la
aplicación mostrará las tres columnas; pulsa **Actualizar** una vez para renovar
la caché de la sesión.
