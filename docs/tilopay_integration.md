# Arquitectura e Integración de Pagos: Tilopay y Recibos Automáticos

Este documento describe cómo se orquesta el proceso de pago electrónico dentro de **Huevos CR** utilizando Tilopay, los redireccionamientos web y el sistema automatizado de comprobantes.

---

## 1. Generación del Enlace de Pago (`app/services/tilopay.py`)
Cuando el sistema aprueba enviar un botón interactivo de WhatsApp o el agente solicita un enlace, se ejecuta la función `generate_payment_link_for_order`.

*   **Identificador (Reference)**: Para enlazar el pago con nuestra base de datos, el payload incluye `"reference": f"ORD-{order.id}"`.
*   **Redirect (Callback URL)**: El parámetro `callback_url` es reconstruido dinámicamente apuntando a la nueva vista del sistema: `https://www.huevoscr.com/gracias?order_id={order.id}`.

Al completarse el pago del banco de forma exitosa, Tilopay devolverá al cliente automáticamente a esa ruta.

---

## 2. Pantalla de Éxito (`GET /gracias`)
El `router` en `app/routers/pages.py` intercepta el `order_id` extraído directamente de la URL. 
*   **Seguridad y Validación**: Se consulta a la base de datos `db.query(models.Order)` que dicha orden exista antes de servir HTML.
*   **Plantilla (`gracias.html`)**: Presenta un resumen estético tipo *Landing Page* confirmando al usuario qué pagó y cuándo recibirá sus cartones.

---

## 3. El Webhook de Despacho Inmediato (`app/api/webhook.py -> /tilopay`)
Mientras el usuario es devuelto a la página de gracias, Tilopay dispara silenciosa e independientemente un `POST` JSON webhook a nuestro endpoint (`/webhook/tilopay`). 

El código intercepta la respuesta para activar todos los servicios subordinados de la tienda:

1.  **Recepción**: Lee el `payload` JSON, ubica a la variable `"reference"`, y hace un String Split separando la palabra `ORD-` del número ID entero.
2.  **Validación de Orden**: Marca en tiempo real `order.status = "paid"` y sella el método de pago `payment_method = "Tilopay"`.
3.  **Despacho en WhatsApp**: Formula un reporte textual de la factura que se encarga a `wa_service.send_message` inmediatamente.

---

## 4. Estrategia de Correo (Fallback Mode)
Siendo que el correo es un campo opcional para HuevosCR, hemos implementado una lógica oportunista en el `webhook.py`:

```python
tilopay_email = payload.get("email") or payload.get("customerEmail") or payload.get("customer_email")
target_email = customer.email if customer.email else tilopay_email
```

El servidor detectará si tiene registrado un correo original en la base de datos local. Si está vacío, rastreará la tarjeta de Tilopay en busca de un correo ingresado directamente en su formulario. 

Una vez encontrado (sea propio o del banco), invoca en formato `@background_task` la interfaz `send_payment_receipt_email` alojada en `app/services/email.py`. Esta función se encarga de usar SMTP (Gmail) e inyectar el número, cantidad, total y saludo a la estructura visual y despacharla sin bloquear la interfaz.
