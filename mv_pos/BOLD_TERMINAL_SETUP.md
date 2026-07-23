# Activacion del datáfono Bold

La integración ya está implementada. No copies llaves al frontend ni las envíes por chat si puedes cargarlas directamente en el archivo `.env` del servidor.

## 1. Requisitos en Bold

1. Usa un datáfono Smart Pro o un Smart compatible y actualizado.
2. En la app Bold activa **Mi perfil > Preferencias de cobro > Conexiones API** y selecciona el datáfono.
3. En `panel.bold.co > Integraciones > Llaves de integración`, copia las llaves de **API datáfono**, no las del botón de pagos.

## 2. Configuración del servidor

Parte de `.env.example` y completa solamente estos valores:

```dotenv
BOLD_TERMINAL_SANDBOX=true
BOLD_API_KEY_SANDBOX=tu_llave_de_identidad_de_pruebas
BOLD_SECRET_KEY_SANDBOX=
BOLD_TERMINAL_WEBHOOK_URL=https://tu-dominio.com/api/v1/webhooks/bold
```

La llave secreta de Sandbox se deja vacía: Bold firma los webhooks de prueba con clave vacía. La llave secreta real solo se usa al pasar a producción:

```dotenv
BOLD_TERMINAL_SANDBOX=false
BOLD_API_KEY_PROD=tu_llave_de_identidad_de_produccion
BOLD_SECRET_KEY_PROD=tu_llave_secreta_de_produccion
```

Reinicia el backend después de modificar `.env`.

## 3. Webhook obligatorio

El backend recibe los resultados en:

`POST /api/v1/webhooks/bold`

El dominio debe ser público y HTTPS. Registra la URL completa en el panel Bold:

- En Sandbox: **Integraciones > Webhooks > Webhooks de prueba**.
- En producción: **Integraciones > Webhooks**.

## 4. Prueba antes de producción

1. Inicia el backend y el frontend con Sandbox activo.
2. Abre una mesa, entra a **Cierre de Cuenta**, elige tarjeta y cobra.
3. Confirma que el datáfono recibe el total, que el webhook marca la orden como pagada y libera la mesa.
4. Repite con montos de Sandbox: `111111` y `222222` deben rechazar la venta.
5. Solo tras validar lo anterior, cambia a las llaves productivas.

El sistema toma el total y el IVA desde la orden guardada en el backend; el navegador no puede modificar el valor enviado al datáfono. También bloquea un segundo cobro mientras exista uno pendiente y puede cerrar la orden usando la consulta manual de respaldo si el webhook se demora.
