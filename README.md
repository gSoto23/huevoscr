# Huevos CR - Sistema de Gestión y Ventas

Bienvenido al repositorio oficial de **Huevos CR**. Esta aplicación es un sistema integral para la gestión de ventas, control de clientes y seguimiento de pedidos, diseñado con un enfoque en la automatización y la integração con WhatsApp mediante inteligencia artificial.

## 🚀 Características Principales

### Panel Administrativo
- **Gestión de Clientes**: Creación, edición y eliminación de clientes. Soporte para ubicación GPS y pre-llenado de datos.
- **Historial de Chat (IA)**: Visualización en tiempo real de las conversaciones, con soporte para media.
- **Control de Ventas**: Registro detallado de pedidos y asignación de rutas.
- **UI Moderna**: Notificaciones tipo "Toaster" y modales de confirmación para acciones críticas.

### Panel de Vendedores
- Registro rápido de pedidos en ruta.
- **Agregar Clientes**: Formulario optimizado con detección automática de números y ubicación.
- Visualización de rutas asignadas.

### Integración IA (WhatsApp)
- **Arquitectura Híbrida**: FastAPI actúa como controlador central (Webhook), gestionando la seguridad y el registro de mensajes.
- **n8n**: Se utiliza exclusivamente para el flujo conversacional y la lógica de IA.
- Reconocimiento de contexto del cliente para respuestas personalizadas.

---

## 🛠 Tecnologías Utilizadas

*   **Backend**: Python 3.10+ con **FastAPI**.
*   **Base de Datos**: SQLite (Optimizado con SQLAlchemy).
*   **Frontend**: HTML5, CSS3, JavaScript (Jinja2 Templates).
*   **Servidor Web**: Gunicorn + Uvicorn + Nginx (Producción).
*   **Integraciones**: Meta for Developers (WhatsApp API).

---

## 📂 Estructura del Proyecto

```
huevoscr/
├── app/
│   ├── api/            # Endpoints de la API (Conversaciones, Ventas, Clientes)
│   ├── core/           # Utilidades y configuración
│   ├── models.py       # Modelos de Base de Datos (SQLAlchemy)
│   ├── schemas.py      # Esquemas Pydantic
│   ├── templates/      # Vistas HTML (Admin, Seller, Landing)
│   └── static/         # Archivos estáticos (CSS, JS, Media)
├── receipts/           # (Local) Comprobantes de pago descargados
├── logs/               # (Local) Logs del sistema y media del chat
├── .env.example        # Plantilla de variables de entorno
├── requirements.txt    # Dependencias de Python
└── README_DEPLOY.md    # Guía de despliegue paso a paso
```

---

## ⚡️ Instalación Local (Desarrollo)

1.  **Clonar el repositorio**:
    ```bash
    git clone <URL_DEL_REPO>
    cd huevoscr
    ```

2.  **Crear entorno virtual**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # En Mac/Linux
    # venv\Scripts\activate   # En Windows
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar Variables de Entorno**:
    Copia el archivo de ejemplo y edítalo con tus claves reales.
    ```bash
    cp .env.example .env
    ```

5.  **Inicializar Base de Datos**:
    ```bash
    python seed_db.py
    ```
    *Esto creará el usuario admin por defecto: `admin` / `admin`.*

6.  **Ejecutar Servidor**:
    ```bash
    uvicorn app.main:app --reload
    ```
    Visita `http://127.0.0.1:8000` en tu navegador.

---

## 🔒 Consideraciones de Seguridad

El sistema cuenta con configuraciones dedicadas para proteger los datos en entornos abiertos:
- **Validación Estricta de Webhook:** El sistema rechaza cualquier solicitud de verificación de Meta si la variable de entorno `WHATSAPP_VERIFY_TOKEN` está vacía o si se está usando una clave insegura. Esto impide que actores externos secuestren tu punto de enganche (webhook).
- **Protección de Dominios (CORS):** El API principal contiene un `CORSMiddleware` explícito y está restringido. Asegúrate de modificar `origins` en `app/main.py` antes de subir a un nuevo dominio.
- **Loggings Seguros y Traza Oculta:** FastAPI interceptará cualquier excepción interna 500 para evitar mostrar la estructura de tus archivos o base de datos a un posible atacante. Para depurar fallas, verifica los logs internos seguros (`logging`).

---

## 🚢 Despliegue en Producción (AWS Lightsail)

Para mantener los costos bajos y predecibles (~$20/mes), el proyecto está optimizado para desplegarse como una solución "Todo en Uno" en un único servidor de **AWS Lightsail**. 

La aplicación utiliza la base de datos local SQLite y almacenamiento en disco de manera segura. Al usar un VPS de Lightsail, aprovechas gigabytes de almacenamiento y terabytes de transferencia de datos gratuitos incluidos, evitando las tarifas complejas de componentes por separado como RDS o S3.

Consulta los siguientes documentos incluidos para mayor detalle:

1.  **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)**: Estrategia de arquitectura y backups en Lightsail.
2.  **[README_DEPLOY.md](README_DEPLOY.md)**: Guía paso a paso para configurar el servidor desde cero usando Nginx y Gunicorn.

---

## 📝 Notas Adicionales

*   **API Docs**: La documentación automática de la API está disponible en `/docs` (Swagger UI) y `/redoc`.
*   **Seguridad**: Asegúrate de nunca subir el archivo `.env` al repositorio público.
*   **Media**: Las imágenes del chat se descargan localmente en `app/static/logs/media` para garantizar persistencia.

---
**Desarrollado para Huevos CR**
