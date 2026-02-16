# Guía de Despliegue en AWS Lightsail (Paso a Paso)

Esta guía explica cómo poner en producción la aplicación `huevoscr` en un servidor AWS Lightsail con dominio propio (`www.huevoscr.com`) y HTTPS seguro.

## Paso 1: Crear Instancia en AWS Lightsail

1.  Iniciar sesión en la consola de AWS Lightsail: https://lightsail.aws.amazon.com/
2.  Clic en **Create instance**.
3.  **Platform**: Linux/Unix.
4.  **Blueprint**: OS Only > **Ubuntu 22.04 LTS**.
5.  **Instance Plan**: Seleccionar el plan de $5 USD/mes (o superior según presupuesto).
6.  **Identify your instance**: Nombre único, ej: `huevoscr-prod`.
7.  Clic en **Create instance**.
8.  Esperar unos minutos y hacer clic en el nombre de la instancia.
9.  Ir a la pestaña **Networking** > **Attach static IP**. Crear una nueva IP estática (ej: `StaticIp-1`) y adjuntarla. **Anota esta IP**.

## Paso 2: Configurar Dominio (DNS)

1.  Ve a tu proveedor de dominio (donde compraste `huevoscr.com`).
2.  Administrar DNS.
3.  Crear o editar registro **A**:
    *   **Host/Name**: `@` (o dejar vacío) -> Apunta a tu **IP Estática de Lightsail**.
    *   **Host/Name**: `www` -> Apunta a tu **IP Estática de Lightsail**.
4.  Esto puede tardar hasta 48 horas en propagarse, pero suele ser rápido.

## Paso 3: Configurar el Servidor (Terminal)

Conéctate a tu instancia usando el botón naranja **"Connect using SSH"** en la consola de Lightsail.

### 3.1 Actualizar Sistema y Dependencias
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx git -y
```

### 3.2 Clonar el Proyecto
*(Nota: Asumimos que el código está en un repo Git. Si no, puedes subirlo vía SFTP/FileZilla)*.

```bash
cd /home/ubuntu
git clone <TU_REPO_URL_HUEVOSCR> huevoscr
# O si subes archivos manuales, crea la carpeta y súbelos.
```

### 3.3 Configurar Entorno Virtual y Dependencias
```bash
cd /home/ubuntu/huevoscr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn uvloop
```

### 3.4 Configurar Variables de Entorno (.env)
Crea el archivo `.env` de producción:
```bash
nano .env
```
Pega tu configuración (asegúrate de usar datos reales):
```env
SECRET_KEY=tu_clave_secreta_generada
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
WHATSAPP_TOKEN=<TU_TOKEN_PERMANENTE_META>
WHATSAPP_PHONE_ID=<TU_PHONE_ID_META>
# Otros secrets...
```
Guarda con `Ctrl+O`, `Enter`, `Ctrl+X`.

### 3.5 Inicializar Base de Datos
```bash
python3 seed_db.py
# Esto creará huevoscr.db y el usuario admin inicial.
```

---

## Paso 4: Configurar Gunicorn (Servicio de Aplicación)

Vamos a crear un servicio de sistema para que la app corra siempre, incluso si el servidor se reinicia.

1.  Crear archivo de servicio:
```bash
sudo nano /etc/systemd/system/huevoscr.service
```

2.  Pegar el siguiente contenido:
```ini
[Unit]
Description=Gunicorn instance to serve huevoscr
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/huevoscr
Environment="PATH=/home/ubuntu/huevoscr/venv/bin"
ExecStart=/home/ubuntu/huevoscr/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

3.  Activar el servicio:
```bash
sudo systemctl start huevoscr
sudo systemctl enable huevoscr
```
(Verifica que esté corriendo con `sudo systemctl status huevoscr`).

---

## Paso 5: Configurar Nginx (Proxy y SSL)

Nginx recibirá las peticiones de internet y se las pasará a Gunicorn.

1.  Crear configuración de sitio:
```bash
sudo nano /etc/nginx/sites-available/huevoscr
```

2.  Pegar contenido (reemplaza `huevoscr.com` con tu dominio real):
```nginx
server {
    listen 80;
    server_name huevoscr.com www.huevoscr.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Servir archivos estáticos (imágenes/media)
    location /static {
        alias /home/ubuntu/huevoscr/app/static;
    }
}
```

3.  Activar sitio y reiniciar Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/huevoscr /etc/nginx/sites-enabled
sudo nginx -t  # Verificar sintaxis
sudo systemctl restart nginx
```

### 5.1 Certificado SSL (HTTPS Gratuito con Certbot)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d huevoscr.com -d www.huevoscr.com
```
Sigue las instrucciones en pantalla (email, aceptar términos). Certbot configurará HTTPS automáticamente.

---

## Paso 6: Configuraciones Externas

### 6.1 Meta for Developers (WhatsApp API)
1.  Ve a tu App en Meta Developers > WhatsApp > Configuration.
2.  **Callback URL**: Actualiza la URL por tu endpoint seguro de FastAPI:
    `https://www.huevoscr.com/webhook`
3.  **Verify Token**: Asegúrate que coincida con la variable `WHATSAPP_VERIFY_TOKEN` en tu archivo `.env`.

### 6.2 n8n (Flujo Conversacional)
La arquitectura ahora utiliza Python como intermediario:
1.  **Entrada (Inbound)**: FastAPI recibe el mensaje de Meta y lo reenvía a n8n.
    *   En n8n, usa un nodo **Webhook (POST)**.
    *   Configura la URL de este webhook en tu variable de entorno `N8N_WEBHOOK_URL` en el servidor (`.env`).
2.  **Salida (Outbound)**: n8n ya no contacta directo a Meta.
    *   En n8n, usa un nodo **HTTP Request (POST)** para responder.
    *   **URL**: `https://www.huevoscr.com/messages/send`
    *   **Authentication**: Generic Credential Type > Header Auth.
        *   Name: `Authorization`
        *   Value: `Bearer <TU_TOKEN_LARGA_DURACION>`
    *   **Body Content**: JSON
    *   **JSON**:
        ```json
        {
          "to": "506{{ $json.body.entry[0].changes[0].value.messages[0].from }}",
          "body": "Respuesta desde n8n"
        }
        ```
        *(Asegúrate de mapear el campo "to" dinámicamente con el número del remitente)*.

3.  **Confirmación de Recibo (n8n)**:
    *   Cuando el cliente confirma que envió el pago, usa un nodo **HTTP Request (POST)**.
    *   **URL**: `https://www.huevoscr.com/customers/{{ $json.sender }}/confirm_receipt`
    *   **Authentication**: Generic Credential Type > Header Auth (Bearer Token).
    *   **Body Content**: JSON
    *   **JSON**:
        ```json
        {
          "order_id": {{ $json.pending_order_id }} 
        }
        ```
        *(El campo `pending_order_id` viene en el webhook inicial si es un recibo candidato, o puedes omitirlo para usar el último detectado)*.

---

## Mantenimiento Futuro

*   **Ver Logs de la App (Tiempo Real)**:
    ```bash
    sudo journalctl -u huevoscr -f
    ```
*   **Verificar Último Mensaje Recibido (Script)**:
    ```bash
    ./venv/bin/python3 scripts/check_last_message.py
    ```
*   **Generar Token de Larga Duración (10 Años - Para n8n)**:
    ```bash
    ./venv/bin/python3 scripts/generate_token.py
    ```
*   **Reiniciar App (tras cambios de código)**:
    ```bash
    cd /home/ubuntu/huevoscr
    git pull
    sudo systemctl restart huevoscr
    ```
*   **Backups**: Configura Snapshots automáticos en la consola de Lightsail.
