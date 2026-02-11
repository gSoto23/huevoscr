# Huevos CR - Sistema de Gestión y Ventas

Bienvenido al repositorio oficial de **Huevos CR**. Esta aplicación es un sistema integral para la gestión de ventas, control de clientes y seguimiento de pedidos, diseñado con un enfoque en la automatización y la integração con WhatsApp mediante inteligencia artificial.

## 🚀 Características Principales

### Panel Administrativo
- **Gestión de Clientes**: Base de datos completa con historial de pedidos, dirección (GPS), y preferencias de entrega.
- **Historial de Chat (IA)**: Visualización en tiempo real de las conversaciones de WhatsApp entre el cliente y el Agente IA (n8n), incluyendo **soporte para imágenes y archivos (PDF)**.
- **Control de Ventas**: Registro detallado de pedidos, estados de entrega y asignación de rutas.

### Panel de Vendedores
- Vista simplificada para agentes de ventas.
- Registro de pedidos en campo.
- Visualización de rutas asignadas.

### Integración IA (WhatsApp)
- Conexión vía **n8n** para flujo conversacional.
- Ingesta de mensajes en tiempo real.
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

## 🚢 Despliegue en Producción (AWS)

Para desplegar este proyecto en un servidor AWS Lightsail, consulta los siguientes documentos incluidos:

1.  **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)**: Estrategia de arquitectura y backups.
2.  **[README_DEPLOY.md](README_DEPLOY.md)**: Guía paso a paso para configurar el servidor desde cero.

---

## 📝 Notas Adicionales

*   **API Docs**: La documentación automática de la API está disponible en `/docs` (Swagger UI) y `/redoc`.
*   **Seguridad**: Asegúrate de nunca subir el archivo `.env` al repositorio público.
*   **Media**: Las imágenes del chat se descargan localmente en `app/static/logs/media` para garantizar persistencia.

---
**Desarrollado para Huevos CR**
