"""Dashboard API server — serves TED data as JSON endpoints."""
import json
import os
import secrets
import sys
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.env_loader import load_env
from src.sync_to_google import normalize_course

load_env()

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

TEST_AUTH_BYPASS = os.environ.get("TEST_AUTH_BYPASS") == "1"

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
DIST_DIR = os.path.join(PROJECT_ROOT, "dashboard-dist")

GOOGLE_CLIENT_ID = "343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"

ALLOWED_EMAILS = {
    "isikkurtx@gmail.com",
    "drmahirkurt@gmail.com",
    "ozlem.murzoglu@gmail.com",
    "huriye.murzoglu@gmail.com",
}

DAY_NAMES = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
    3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
}


# --- Auth ---

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if TEST_AUTH_BYPASS:
            return f(*args, **kwargs)
        if not session.get("user_email"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json()
    token = data.get("credential") if data else None
    if not token:
        return jsonify({"error": "No credential provided"}), 400
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        email = idinfo.get("email", "").lower()
        if email not in ALLOWED_EMAILS:
            return jsonify({"error": "Bu hesapla giris yapilamaz"}), 403
        session["user_email"] = email
        session["user_name"] = idinfo.get("name", "")
        session["user_picture"] = idinfo.get("picture", "")
        return jsonify({
            "email": email,
            "name": session["user_name"],
            "picture": session["user_picture"],
        })
    except ValueError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def auth_me():
    if session.get("user_email"):
        return jsonify({
            "email": session["user_email"],
            "name": session.get("user_name", ""),
            "picture": session.get("user_picture", ""),
        })
    return jsonify({"error": "Not authenticated"}), 401


# --- Data helpers ---

def _load_json(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _scraped():
    return _load_json("scraped_data.json")


# --- API endpoints (all require auth) ---

@app.route("/api/schedule")
@require_auth
def schedule():
    data = _scraped()
    weeks = data.get("ders_programi", [])
    today = DAY_NAMES.get(datetime.now().weekday(), "")
    latest = weeks[-1] if weeks else {}
    return jsonify({"weeks": weeks, "latest": latest, "today": today})


@app.route("/api/homework")
@require_auth
def homework():
    data = _scraped()
    hw = data.get("odevlerim", {})
    rows = hw.get("homework", {}).get("rows", [])
    summary = hw.get("summary", "")
    for r in rows:
        if "Ders Adı" in r:
            r["normalized_course"] = normalize_course(r["Ders Adı"])
    return jsonify({"summary": summary, "homework": rows})


@app.route("/api/sebit")
@require_auth
def sebit():
    return jsonify(_load_json("sebit_homework.json"))


@app.route("/api/grades")
@require_auth
def grades():
    data = _scraped()
    return jsonify(data.get("gelisim_raporu", {}))


@app.route("/api/calendar")
@require_auth
def calendar():
    data = _scraped()
    return jsonify({"events": data.get("takvim", [])})


@app.route("/api/teams")
@require_auth
def teams():
    data = _scraped()
    activities = data.get("takim_calismalari", {}).get("activities", {}).get("rows", [])
    ogep = data.get("ogep", {}).get("sessions", {}).get("rows", [])
    return jsonify({"activities": activities, "ogep": ogep})


@app.route("/api/content")
@require_auth
def content():
    data = _scraped()
    return jsonify(data.get("ders_icerikleri", {}))


@app.route("/api/announcements")
@require_auth
def announcements():
    data = _scraped()
    ann = data.get("duyurular", {}).get("announcements", [])
    return jsonify({"announcements": ann})


@app.route("/api/progress/ec")
@require_auth
def progress_ec():
    return jsonify(_load_json("englishcentral_progress.json"))


@app.route("/api/progress/a3k")
@require_auth
def progress_a3k():
    return jsonify(_load_json("achieve3000_progress.json"))


@app.route("/api/health")
@require_auth
def health():
    return jsonify(_load_json("health.json"))


# --- SPA static serving (production build) ---
@app.route("/")
@app.route("/<path:path>")
def serve_spa(path=""):
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(DIST_DIR, "index.html")
    return jsonify({"error": "Dashboard not built. Run: cd dashboard && npm run build"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=True)
