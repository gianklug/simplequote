from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
from os import getenv

app = Flask(__name__)
CORS(app)

# --- Database Setup ---
DATABASE = "data/quotes.db"
PASSWORD_HASH = hashlib.sha256(getenv("PASSWORD", "12345678").encode()).hexdigest()


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                person TEXT NOT NULL,
                context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# --- Authentication Middleware ---
def authenticate_request():
    token = request.headers.get("Authorization")
    if not token or token != PASSWORD_HASH:
        return False
    return True


# --- Routes ---
@app.route("/")
def serve_index():
    return send_from_directory("static", "index.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data:
        return jsonify({"error": "Unprocessable Entity"}), 422
    if (
        data["password"]
        and hashlib.sha256(data["password"].encode()).hexdigest() == PASSWORD_HASH
    ):
        return jsonify({"token": PASSWORD_HASH})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/quotes", methods=["GET"])
def get_quotes():
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    cur = get_db().cursor()
    cur.execute(
        "SELECT text, person, context, timestamp FROM quotes ORDER BY timestamp DESC"
    )
    quotes = cur.fetchall()
    return jsonify(
        [
            {"text": row[0], "person": row[1], "context": row[2], "timestamp": row[3]}
            for row in quotes
        ]
    )


@app.route("/quotes", methods=["POST"])
def add_quote():
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not data:
        return jsonify({"error": "Unprocessable Entity"}), 422
    db = get_db()
    db.execute(
        "INSERT INTO quotes (text, person, context) VALUES (?, ?, ?)",
        (data["text"], data["person"], data.get("context", "")),
    )
    db.commit()
    return jsonify({"success": True}), 201


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0")
