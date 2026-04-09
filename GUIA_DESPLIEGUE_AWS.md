# Guía Definitiva de Despliegue (Para Dummys) 🚀

Siguiendo la estrategia de mantener los costos controlados y predecibles (~$20/mes), esta guía te enseña cómo configurar toda tu infraestructura **exclusivamente dentro de AWS Lightsail**, sin lidiar con los complejos paneles de AWS tradicional (como RDS, VPCs, políticas IAM o S3).

---

## 🐘 Fase 1: Crear la Base de Datos (Lightsail Managed Database)

Si decides superar la base de datos local SQLite y quieres algo a nivel empresarial pero fácil, Lightsail te da PostgreSQL a un precio fijo mensual.

1. Entra a tu consola de [AWS Lightsail](https://lightsail.aws.amazon.com/).
2. Ve a la pestaña **Databases** (Bases de Datos).
3. Haz clic en **Create database**.
4. Selecciona **PostgreSQL**.
5. Elige el plan estándar de **$15 USD/mes**.
6. Ponle un nombre para identificarla (ej. `huevoscr-db-prod`).
7. Haz clic en **Create database**.
8. Una vez que termine de crearse (tarda unos minutos), haz clic sobre ella y ve a la información de conexión (Connection details).
9. AWS Lightsail te dará un Endpoint (servidor), un Username (ej. `dbmasteruser`) y un Password. Arma tu URL de conexión así: `postgres://USUARIO:CONTRASEÑA@ENDPOINT:5432/postgres` (reemplaza con los tuyos). Cópiala en tu bloc de notas secreto.

---

## 🪣 Fase 2: Almacenamiento de Imágenes (Disco Local SSD de Lightsail)

¡Buenas noticias! Para ahorrar dinero y evitar configuraciones complejas con Amazon S3 y llaves IAM, usaremos el **generoso disco SSD incluido en tu servidor Lightsail**. 

Tu servidor web de $5/mes viene con **40 GB de disco** SSD súper rápido y **2 TB** de transferencia, lo cual es espacio y ancho de banda más que suficiente para almacenar decenas de miles de comprobantes y fotos de WhatsApp. Todo se guardará automáticamente en el servidor y tus imágenes estarán siempre ahí gracias a los Snapshots (respaldos) de Lightsail. No hay que configurar nada extra en la nube.

---

## 💻 Fase 3: Llevar el Código a tu Servidor (Lightsail)

1. Sube desde tu computadora todo el código a tu Git / GitHub:
   ```bash
   git add .
   git commit -m "Arquitectura Lightsail implementada"
   git push origin main
   ```
2. Conéctate a la terminal negra de tu servidor web en Lightsail mediante SSH (botón naranja).
3. Ve a la carpeta donde vive tu proyecto y trae los cambios frescos (asumiendo que ya lo clonaste antes):
   ```bash
   cd /home/ubuntu/huevoscr
   git pull origin main
   ```
4. **Activa tu entorno y descarga dependencias (por si acaso):**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   *(Esto instalará o actualizará el driver de PostgreSQL en tu servidor).*

---

## ⚙️ Fase 4: Poner el Switch de Producción en el `.env`

Aún dentro de tu servidor de Lightsail mediante la terminal, hay que decirle que empiece a conectarse a la Base de Datos de la Fase 1.

1. Edita el archivo secreto de las variables:
   ```bash
   nano .env
   ```
2. Al fondo del archivo, asegúrate de añadir tu base de datos y borrar/vaciar cualquier cosa relacionada con S3 que tuviéramos antes:
   ```ini
   # NADA DEL WHATSAPP SE TOCA, MANTENLO IGUAL.

   # Modulo Base de Datos (URL de la Fase 1)
   DATABASE_URL=postgres://USUARIO:CONTRASEÑA@EL_ENDPOINT_DE_LIGHTSAIL:5432/postgres

   # Modulo Almacenamiento - APAGADO PARA USAR EL DISCO LOCAL
   # Deja estos valores así o bórralos por completo:
   AWS_BUCKET_NAME=
   AWS_ACCESS_KEY_ID=
   AWS_SECRET_ACCESS_KEY=
   ```
3. Guarda (`Ctrl + O`, `Enter` y `Ctrl + X`).

---

## 🚀 Fase 5: Reiniciar Motores

Por último, hay que reiniciar la aplicación.

Ejecuta en tu terminal:
```bash
sudo systemctl restart huevoscr   # (Reinicia el servicio)
sudo systemctl restart nginx      # (Solo por si acaso)
```

¡Eso es absolutamente todo! Tu servidor ahora leerá la clave `.env` de Postgres y el sistema migrará a tu nueva base de datos dedicada. Todo el stack (Gunicorn, Nginx, PostgreSQL) vivirá en armonía dentro de la red privada, cómoda y económica de **Lightsail**.
