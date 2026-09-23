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