"""
QueuePilot Web API

REST API backend for the QueuePilot React frontend.
All HTML rendering is handled by React; Flask serves JSON + static assets.
"""

import os
import json
import datetime
import docker
import mysql.connector
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet
from flask import Flask, request, jsonify, send_from_directory

_STOCKHOLM = ZoneInfo("Europe/Stockholm")
CONTAINER_NAME = "queuepilot"
CUSTOMER_ID = 1

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "queuepilot-dev-secret-change-me")


def _to_stockholm(dt: datetime.datetime | None) -> datetime.datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(_STOCKHOLM)


def _fernet() -> Fernet:
    key = os.environ["ENCRYPTION_KEY"]
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_password(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def get_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"],
    )


def ensure_schema():
    conn = get_connection()
    cursor = conn.cursor()
    migrations = [
        "ALTER TABLE sites ADD COLUMN IF NOT EXISTS system_type VARCHAR(50) NOT NULL DEFAULT 'momentum'",
        "ALTER TABLE sites MODIFY COLUMN base_url VARCHAR(500) NULL DEFAULT NULL",
        "ALTER TABLE sites ADD COLUMN IF NOT EXISTS momentum_id VARCHAR(100) DEFAULT NULL",
        "ALTER TABLE sites DROP COLUMN IF EXISTS api_key",
        "ALTER TABLE sites DROP COLUMN IF EXISTS momentum_site_id",
        "ALTER TABLE sites DROP COLUMN IF EXISTS momentum_cname",
        "ALTER TABLE credentials ADD COLUMN IF NOT EXISTS queue_points INT DEFAULT NULL",
        "ALTER TABLE credentials ADD COLUMN IF NOT EXISTS queue_details TEXT DEFAULT NULL",
        """CREATE TABLE IF NOT EXISTS settings (
            `key` VARCHAR(100) PRIMARY KEY,
            `value` TEXT NOT NULL
        )""",
        "INSERT IGNORE INTO settings (`key`, `value`) VALUES ('momentum_api_key', '')",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
        except Exception as e:
            app.logger.warning("Schema migration warning: %s", e)
    conn.commit()
    cursor.close()
    conn.close()


def get_setting(key: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT `value` FROM settings WHERE `key` = %s", (key,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (`key`, `value`) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
        (key, value),
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_container_info() -> dict:
    try:
        client = docker.from_env()
        container = client.containers.get(CONTAINER_NAME)
        finished_at = container.attrs["State"]["FinishedAt"]
        if finished_at.startswith("0001"):
            finished_at = None
        else:
            try:
                dt = datetime.datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
                finished_at = dt.astimezone(_STOCKHOLM).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                finished_at = finished_at[:19].replace("T", " ")
        return {"status": container.status, "finished_at": finished_at}
    except docker.errors.NotFound:
        return {"status": "not_found", "finished_at": None}
    except Exception as e:
        return {"status": "error", "finished_at": None, "error": str(e)}


# ── API Routes ────────────────────────────────────────────────────────────────

@app.route("/api/sites", methods=["GET"])
def api_list_sites():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.url_name, s.fullname, s.system_type, s.momentum_id, s.base_url,
               c.username, c.active, c.last_login, c.queue_points, c.queue_details
        FROM sites s
        LEFT JOIN credentials c ON c.site = s.url_name AND c.customer_id = %s
        ORDER BY s.system_type, s.url_name
    """, (CUSTOMER_ID,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    sites = []
    totals: dict = {"all": 0}
    for s in rows:
        raw = s.get("queue_details")
        details = json.loads(raw) if raw else []
        ll = _to_stockholm(s.get("last_login"))
        pts = s.get("queue_points")
        st = s.get("system_type", "momentum")
        if pts is not None:
            totals[st] = totals.get(st, 0) + pts
            totals["all"] += pts
        sites.append({
            "url_name": s["url_name"],
            "fullname": s.get("fullname") or s["url_name"],
            "system_type": st,
            "momentum_id": s.get("momentum_id"),
            "base_url": s.get("base_url"),
            "username": s.get("username"),
            "active": bool(s.get("active")),
            "last_login": ll.strftime("%Y-%m-%d %H:%M") if ll else None,
            "queue_points": pts,
            "queue_details": details,
        })

    has_momentum = any(s["system_type"] == "momentum" for s in sites)
    return jsonify({
        "sites": sites,
        "totals": totals,
        "api_key_missing": has_momentum and not get_setting("momentum_api_key"),
    })


@app.route("/api/sites", methods=["POST"])
def api_create_site():
    data = request.get_json() or {}
    url_name = (data.get("url_name") or "").strip().lower()
    fullname = (data.get("fullname") or "").strip()
    system_type = (data.get("system_type") or "momentum").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    active = int(bool(data.get("active", True)))

    if not url_name or not fullname or not username or not password:
        return jsonify({"error": "Missing required fields"}), 400

    momentum_id = (data.get("momentum_id") or "").strip() or None if system_type == "momentum" else None
    base_url = ((data.get("base_url") or "").strip().rstrip("/") or None) if system_type == "vitec" else None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sites (url_name, fullname, base_url, system_type, momentum_id) VALUES (%s,%s,%s,%s,%s)",
            (url_name, fullname, base_url, system_type, momentum_id),
        )
        cursor.execute(
            "INSERT INTO credentials (site, customer_id, username, password, active) VALUES (%s,%s,%s,%s,%s)",
            (url_name, CUSTOMER_ID, username, encrypt_password(password), active),
        )
        conn.commit()
        return jsonify({"ok": True, "url_name": url_name})
    except mysql.connector.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/sites/<url_name>", methods=["GET"])
def api_get_site(url_name):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.url_name, s.fullname, s.base_url, s.system_type, s.momentum_id,
               c.username, c.active
        FROM sites s
        LEFT JOIN credentials c ON c.site = s.url_name AND c.customer_id = %s
        WHERE s.url_name = %s
    """, (CUSTOMER_ID, url_name))
    site = cursor.fetchone()
    cursor.close()
    conn.close()
    if not site:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "url_name": site["url_name"],
        "fullname": site.get("fullname") or "",
        "system_type": site.get("system_type", "momentum"),
        "momentum_id": site.get("momentum_id") or "",
        "base_url": site.get("base_url") or "",
        "username": site.get("username") or "",
        "active": bool(site.get("active")),
    })


@app.route("/api/sites/<url_name>", methods=["PUT"])
def api_update_site(url_name):
    data = request.get_json() or {}
    fullname = (data.get("fullname") or "").strip()
    system_type = (data.get("system_type") or "momentum").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    active = int(bool(data.get("active", True)))

    momentum_id = (data.get("momentum_id") or "").strip() or None if system_type == "momentum" else None
    base_url = ((data.get("base_url") or "").strip().rstrip("/") or None) if system_type == "vitec" else None

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE sites SET fullname=%s, base_url=%s, system_type=%s, momentum_id=%s WHERE url_name=%s",
            (fullname, base_url, system_type, momentum_id, url_name),
        )
        if password:
            cursor.execute(
                "UPDATE credentials SET username=%s, password=%s, active=%s WHERE site=%s AND customer_id=%s",
                (username, encrypt_password(password), active, url_name, CUSTOMER_ID),
            )
        else:
            cursor.execute(
                "UPDATE credentials SET username=%s, active=%s WHERE site=%s AND customer_id=%s",
                (username, active, url_name, CUSTOMER_ID),
            )
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/sites/<url_name>", methods=["DELETE"])
def api_delete_site(url_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM credentials WHERE site=%s", (url_name,))
        cursor.execute("DELETE FROM sites WHERE url_name=%s", (url_name,))
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/sites/<url_name>/toggle-active", methods=["POST"])
def api_toggle_active(url_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE credentials SET active = 1 - active WHERE site=%s AND customer_id=%s",
            (url_name, CUSTOMER_ID),
        )
        conn.commit()
        cursor.execute("SELECT active FROM credentials WHERE site=%s AND customer_id=%s", (url_name, CUSTOMER_ID))
        row = cursor.fetchone()
        return jsonify({"active": bool(row[0]) if row else False})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/api/status", methods=["GET"])
def api_status():
    info = get_container_info()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT site, last_login FROM credentials WHERE customer_id=%s", (CUSTOMER_ID,))
    logins = {}
    for row in cursor.fetchall():
        ll = _to_stockholm(row["last_login"])
        logins[row["site"]] = ll.strftime("%Y-%m-%d %H:%M") if ll else None
    cursor.close()
    conn.close()
    return jsonify({
        "container_status": info["status"],
        "finished_at": info.get("finished_at"),
        "last_logins": logins,
    })


@app.route("/api/run", methods=["POST"])
def api_run():
    try:
        client = docker.from_env()
        container = client.containers.get(CONTAINER_NAME)
        if container.status == "running":
            return jsonify({"ok": False, "message": "Already running"})
        container.start()
        return jsonify({"ok": True, "message": "Queue update started"})
    except docker.errors.NotFound:
        return jsonify({"error": f"Container '{CONTAINER_NAME}' not found — run docker compose up first"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    key = get_setting("momentum_api_key")
    return jsonify({"momentum_api_key": key, "api_key_missing": not key})


@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    data = request.get_json() or {}
    set_setting("momentum_api_key", (data.get("momentum_api_key") or "").strip())
    return jsonify({"ok": True})


# ── SPA catch-all ─────────────────────────────────────────────────────────────

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    candidate = os.path.join(_STATIC_DIR, path) if path else None
    if candidate and os.path.isfile(candidate):
        return send_from_directory(_STATIC_DIR, path)
    return send_from_directory(_STATIC_DIR, "index.html")


ensure_schema()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
