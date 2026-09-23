# Instabox

Práctica 1 — Desarrollo en la Nube.

## Estructura del repo

```
instabox/
├── README.md
├── scripts/
│   ├── setup.sh        
│   └── teardown.sh     
└── src/
    ├── main.py          
    └── requirements.txt 
```

# InstaBox

Backend REST para que un fotógrafo reciba fotos y mensajes de los invitados durante un evento y, al final, genere un álbum de polaroids en un `.zip`.

Práctica de la materia **Desarrollo en la Nube — ITESO**.

## Qué hace

El backend expone 4 endpoints construidos con Flask:

| Endpoint | Qué hace |
|---|---|
| `POST /events` | Crea un evento (nombre, tipo, fecha) y regresa su `event_id` |
| `POST /upload` | Recibe `event_id` + foto (multipart) + mensaje; reduce la foto a 128x128, compone la polaroid (marco blanco + mensaje) y sube ambas versiones a S3; guarda el registro en la base de datos |
| `GET /events/{event_id}` | Regresa la información del evento y el número de fotos recibidas |
| `POST /finish` | Junta todas las polaroids del evento en un `.zip` y lo regresa |

## Arquitectura

- **EC2** — corre el backend (Flask), con el `LabInstanceProfile` del Learner Lab asignado. Gracias a eso, boto3 toma las credenciales automáticamente del rol de la instancia — no hay llaves de acceso guardadas en el código ni en el servidor.
- **S3** — bucket `instabox-vicky-2026`, con dos carpetas lógicas: `pictures/` (foto reducida a 128x128) y `polaroids/` (foto compuesta con marco y mensaje).
- **RDS (PostgreSQL)** — instancia `instabox-db`, con las tablas `events` y `photos` relacionadas por `event_id`.
- **Secrets Manager** — secreto `instabox/db-credentials` con host, puerto, usuario y contraseña de RDS; el backend lo lee en tiempo de ejecución con boto3, nunca hardcodeado ni en variables de ambiente.

```

## Cómo correrlo


### 2. Desplegar el código a la EC2

Desde tu máquina, copia el código y conéctate por SSH:

```bash
scp -i instabox-key.pem -r src/ ubuntu@<EC2_PUBLIC_IP>:~/instabox
ssh -i instabox-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### 3. Dentro de la instancia

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv libjpeg-dev zlib1g-dev
cd instabox
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# corre en segundo plano para que sobreviva al cerrar el SSH
nohup flask --app main run --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

La app queda disponible en `http://<EC2_PUBLIC_IP>:8000`. `libjpeg-dev` y `zlib1g-dev` son necesarios para que Pillow se instale bien en Ubuntu.

### Variables / secretos que necesita

No requiere variables de ambiente ni llaves de AWS: la EC2 tiene asignado el `LabInstanceProfile`, así que boto3 toma las credenciales del rol automáticamente.

Lo único que el backend necesita saber es el nombre del secret (ya definido en el código):

```python
client.get_secret_value(SecretId="instabox/db-credentials")
```

Ese secret guarda `host`, `port`, `dbname`, `username` y `password` de la instancia RDS.

## Eliminar los recursos (teardown)

Para no seguir generando cargos en el Learner Lab, corre:

```bash
cd scripts
chmod +x teardown.sh   # solo la primera vez
./teardown.sh
```

El script elimina, en orden inverso a como se crearon: la instancia EC2, la instancia RDS (sin snapshot final), el secret de Secrets Manager, el bucket S3 (con su contenido), los security groups (`instabox-ec2-sg`, `instabox-db-sg`) y el key pair (`instabox-key`).

