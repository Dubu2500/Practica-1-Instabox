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