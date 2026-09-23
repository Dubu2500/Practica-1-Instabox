from flask import Flask, request, jsonify, send_file
import boto3, json, io, uuid, zipfile
import psycopg2
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

BUCKET = "instabox-vicky-2026"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)


def get_db_credentials():
    client = boto3.client("secretsmanager", region_name=REGION)
    response = client.get_secret_value(SecretId="instabox/db-credentials")
    return json.loads(response["SecretString"])


def get_db_connection():
    creds = get_db_credentials()
    return psycopg2.connect(
        host=creds["host"],
        port=creds["port"],
        dbname=creds["dbname"],
        user=creds["username"],
        password=creds["password"],
    )
@app.route("/events", methods=["POST"])
def create_event():
    data = request.get_json()
    event_id = str(uuid.uuid4())

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (event_id, client_name, event_type, event_date) VALUES (%s, %s, %s, %s)",
        (event_id, data["client_name"], data["event_type"], data["event_date"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"event_id": event_id}), 201

def make_polaroid(photo: Image.Image, message: str) -> Image.Image:
    photo = photo.resize((128, 128))
    frame = Image.new("RGB", (148, 178), "white")
    frame.paste(photo, (10, 10))
    draw = ImageDraw.Draw(frame)
    draw.text((10, 148), message[:40], fill="black")
    return frame


@app.route("/upload", methods=["POST"])
def upload_photo():
    event_id = request.form["event_id"]
    message = request.form.get("message", "")
    file = request.files["photo"]

    photo_id = str(uuid.uuid4())
    original = Image.open(file.stream).convert("RGB")

    resized = original.resize((128, 128))
    picture_key = f"pictures/{photo_id}.jpg"
    buffer1 = io.BytesIO()
    resized.save(buffer1, format="JPEG")
    buffer1.seek(0)
    s3.put_object(Bucket=BUCKET, Key=picture_key, Body=buffer1)

    polaroid = make_polaroid(original, message)
    polaroid_key = f"polaroids/{photo_id}.jpg"
    buffer2 = io.BytesIO()
    polaroid.save(buffer2, format="JPEG")
    buffer2.seek(0)
    s3.put_object(Bucket=BUCKET, Key=polaroid_key, Body=buffer2)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO photos (photo_id, event_id, message, picture_key, polaroid_key) VALUES (%s, %s, %s, %s, %s)",
        (photo_id, event_id, message, picture_key, polaroid_key),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"photo_id": photo_id, "picture_key": picture_key, "polaroid_key": polaroid_key}), 201

@app.route("/events/<event_id>", methods=["GET"])
def get_event(event_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT client_name, event_type, event_date FROM events WHERE event_id = %s",
        (event_id,),
    )
    event = cur.fetchone()
    if event is None:
        cur.close()
        conn.close()
        return jsonify({"error": "event not found"}), 404

    cur.execute("SELECT COUNT(*) FROM photos WHERE event_id = %s", (event_id,))
    photo_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    return jsonify({
        "event_id": event_id,
        "client_name": event[0],
        "event_type": event[1],
        "event_date": str(event[2]),
        "photo_count": photo_count,
    })