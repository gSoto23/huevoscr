# Plan de Despliegue en AWS Lightsail (Huevos CR)

Este documento detalla la estrategia recomendada para desplegar la aplicación `huevoscr` en AWS Lightsail, asegurando estabilidad, escalabilidad y seguridad.

## 1. Arquitectura Propuesta

Para un inicio rápido y costo-eficiente, utilizaremos una arquitectura basada en **Instancia Única (VPS)** preparada para escalar.

**Componentes:**
*   **Servidor**: AWS Lightsail OS Only (Ubuntu 22.04 LTS).
*   **Stack Web**:
    *   **Nginx**: Servidor Web y Proxy Inverso (Maneja HTTPS/SSL y carga estática).
    *   **Gunicorn**: Servidor de Aplicaciones WSGI (Ejecuta FastAPI).
    *   **FastAPI**: Framework de la aplicación y **Controlador Central de Mensajería (Webhook)**.
*   **Base de Datos**: SQLite (`huevoscr.db` local).
*   **Integración WhatsApp**: Modelo híbrido donde Python gestiona la conexión con Meta y delega la lógica conversacional a **n8n**.
*   **Almacenamiento (Media)**: Disco local de la instancia.

## 2. Estrategia de Almacenamiento y Backups

### Estructura de Directorios
*   `/home/ubuntu/huevoscr`: Código fuente (vía Git).
*   `/home/ubuntu/huevoscr/huevoscr.db`: Base de datos de producción.
*   `/home/ubuntu/huevoscr/app/static/receipts`: Comprobantes de pago.
*   `/home/ubuntu/huevoscr/app/static/logs/media`: Imágenes/archivos del chat.

### Plan de Backups (Seguridad de Datos)
1.  **Snapshots Automáticos (CRÍTICO)**:
    *   Activaremos la función **"Automatic Snapshots"** de Lightsail.
    *   AWS realizará una copia completa del servidor diariamente.
    *   Esto permite restaurar todo el sistema (código, DB, media) en minutos ante cualquier fallo.

2.  **Backup Manual de DB (Opcional)**:
    *   Se puede configurar un script simple (`cronbase`) que copie el archivo `.db` a un bucket S3 semanalmente para redundancia extra.

## 3. Escalabilidad y Crecimiento

### Fase 1: Escalamiento Vertical (Inmediato)
Si el sitio se vuelve lento:
1.  Detener la instancia en Lightsail.
2.  Cambiar el "Plan" de instancia a uno con más CPU/RAM.
3.  Iniciar nuevamente. (Downtime de ~5 minutos).

### Fase 2: Escalamiento Horizontal (Alto Tráfico)
Si una sola máquina no es suficiente:
1.  **DB Externa**: Migrar SQLite a **Lightsail Managed Database (PostgreSQL)**.
2.  **Media Externa**: Migrar carpeta `/app/static` a **AWS S3 Bucket**.
3.  **Balanceo de Carga**: Crear un Load Balancer en Lightsail y lanzar múltiples copias de la aplicación.

## 4. Requisitos Previos
*   Dominio: `www.huevoscr.com`
*   Cuenta AWS activa.
*   Meta for Developers App (WhatsApp API) configurada.
*   Flujo de n8n configurado.

---
**Siguiente Paso**: Seguir la guía técnica `README_DEPLOY.md`.
