# Guía Definitiva de Despliegue (Para Dummys) 🚀

Dado que tu código antiguo ya vive en Producción (AWS), lo único que nos separa del nivel _Enterprise_ es indicarle al servidor cómo consumir tu nueva arquitectura (S3 y PostgreSQL). Sigue estos pasos exactos uno a uno.

---

## 🐘 Fase 1: Crear la Base de Datos (PostgreSQL)

Tienes dos opciones excelentes, y **ambas funcionan igual de bien:** un servicio externo rápido (Neon) o AWS RDS. Te recomiendo usar un proveedor _Serverless_ gratuito o súper barato para arrancar rápido y sin tocar terminales dolorosas.

**Opción A (Súper fácil - Neon.tech o Supabase):**
1. Entra a [Neon.tech](https://neon.tech) o [Supabase.com](https://supabase.com) y crea una cuenta con tu GitHub/Google.
2. Crea un **Nuevo Proyecto** y nombra tu base de datos `huevoscr_db`.
3. ¡No tienes que hacer nada más! Busca en el Panel Principal (*Dashboard*) una sección que diga **Connection String** o **Database URL**.
4. Copia ese código. Se verá algo como: `postgres://usuario:contraseña@servidor.neon.tech/huevoscr_db`.
5. Guárdalo en un bloc de notas secreto.

**Opción B (Todo en Amazon - AWS RDS):**
1. En tu consola de AWS, busca **RDS**.
2. Dale al botón naranja **Create Database** (Crear base de datos).
3. Selecciona **PostgreSQL** y la capa *Free Tier* (Capa gratuita).
4. Inventa un nombre de usuario (ej. `huevos_admin`) y una contraseña segura.
5. Apaga tu Firewall ("Public Acces: Yes") y lánzala. AWS tardará 10 minutos. Una vez lista, arma tu propia URL juntando los datos de este modo: `postgres://huevos_admin:TU_PASS@el-host-que-da-aws.com:5432/el_nombre_db`.

---

## 🪣 Fase 2: Crear el Almacén de Imágenes (AWS S3)

1. En tu consola principal de AWS, busca en la barra de arriba **S3** y entra.
2. Haz clic en **Create bucket** (Crear bucket/cubeta).
3. Nómbralo algo único globalmente, por ejemplo: `huevoscr-imagenes-2026`.
4. **IMPORTANTE:** Destilda (apaga) el cuadrito que dice *"Block all public access"* (Bloquear todo el acceso público). Vas a querer que cualquiera pueda ver sus recibos y que WhatsApp las cargue. Dale click al recuadro rojo de confirmación aceptando que será público.
5. Baja al final y dale **Create bucket**. ¡Listo! Anota tu `huevoscr-imagenes-2026` en tu bloc de notas.

### Consiguiendo tus Llaves de Acceso (Llaves Maestras de Amazon)
Para que el código hable con S3, necesita tus credenciales:
1. En el buscador de arriba de AWS, busca **IAM** (Identity and Access Management).
2. Ve a **Users** (Usuarios) a la izquierda y dale **Add user**. Nómbralo `app_huevoscr`.
3. Asígnale la política `AmazonS3FullAccess` (para que controle tu S3).
4. Dale a crear. Luego haz clic sobre tu nuevo usuario `app_huevoscr` y busca la pestaña **Security credentials**.
5. Baja hasta **Access keys** y dale **Create access key**.
6. **¡Detente aquí!** AWS te mostrará 2 textos aleatorios larguísimos: el `Access key ID` y el `Secret access key`. Cópialos en tu bloc de notas porque la clave secreta *no te la volverá a mostrar nunca*.

---

## 💻 Fase 3: Llevar el Código a tu Servidor (Lightsail)

Ahora vas a jalar nuevas mejoras (S3/DB/Favicons/SEO) a tu AWS principal. 
1. Sube desde tu computadora todo el código a tu Git / GitHub:
   ```bash
   git add .
   git commit -m "Arquitectura hibrida S3/Postgres, Favicons, y SEO"
   git push origin main
   ```
2. Conéctate a la terminal negra de tu servidor en Amazon (Lightsail o EC2) mediante SSH.
3. Ve a la carpeta donde vive tu proyecto y trae los cambios frescos:
   ```bash
   cd /ruta/a/tu/app/huevoscr
   git pull origin main
   ```
4. **Activa tu entorno y descarga las dependencias nuevas:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   *(Esto instalará Boto3 y el driver de PostgreSQL en tu servidor).*

---

## ⚙️ Fase 4: Poner el Switch de Producción en el `.env`

Aún dentro de tu servidor de AWS mediante la terminal, hay que decirle que empiece a comportarse como Producción.
1. Edita el archivo secreto de las variables:
   ```bash
   nano .env
   ```
2. Al fondo del archivo, empuja/pega todos los textos de tu bloc de notas secreto:
   ```ini
   # NADA DEL WHATSAPP SE TOCA, SOLO AGREGAS ESTO ABAJO:

   # Modulo Base de Datos
   DATABASE_URL=AQUI_PEGAS_TU_URL_DE_NEON_O_RDS

   # Modulo Almacenamiento S3
   AWS_BUCKET_NAME=AQUI_TU_TITULO_DEL_BUCKET
   AWS_ACCESS_KEY_ID=AQUI_LA_LLAVE_CORTA_DE_IAM
   AWS_SECRET_ACCESS_KEY=AQUI_LA_LLAVE_SECRETA_LARGA_DE_IAM
   ```
3. Guarda (`Ctrl + O`, `Enter` y `Ctrl + X`).

---

## 🚀 Fase 5: Reiniciar Motores

Por último, hay que reiniciar el Daemon de Linux que mantiene la aplicación viva tras bambalinas, para que absorba inmediatamente todo (Las dependencias, .env nuevo y código nuevo).
Si seguiste la fórmula clásica de `Gunicorn + Systemd` ejecuta:
```bash
sudo systemctl restart huevoscr   # (Cámbialo por el nombre del daemon que usaste de Uvicorn)
sudo systemctl restart nginx      # (Solo si también tocaste URLs o puertos estáticos hoy)
```

¡Eso es absolutamente todo! Tu servidor ahora leerá las claves .env y el sistema mutará en silencio, enviándote a Postgres y usando S3 mágicamente.
