"""
QueuePilot Web Interface

Flask application for managing housing queue sites.
Provides CRUD operations on the `sites` and `credentials` MariaDB tables.
Supports multiple platform types (Momentum, Kjellberg, etc.) with
filtering by system_type on the dashboard.
"""

import os
import json
import datetime
import docker
import mysql.connector
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

_STOCKHOLM = ZoneInfo("Europe/Stockholm")


def _to_stockholm(dt: datetime.datetime | None) -> datetime.datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(_STOCKHOLM)

CONTAINER_NAME = "queuepilot"

SYSTEM_TYPES = [
    ("momentum", "Momentum"),
    ("vitec", "Vitec Arena"),
]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "queuepilot-dev-secret-change-me")

CUSTOMER_ID = 1


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
        database=os.environ["DB_NAME"]
    )


def ensure_schema():
    """Applies missing schema migrations (idempotent)."""
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
        (key, value)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_container_info() -> dict:
    """Returns status and last-finished time for the queuepilot container."""
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


@app.route("/")
def index():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.url_name, s.fullname, s.system_type, s.momentum_id,
               c.username, c.active, c.last_login, c.queue_points, c.queue_details
        FROM sites s
        LEFT JOIN credentials c ON c.site = s.url_name AND c.customer_id = %s
        ORDER BY s.system_type, s.url_name
    """, (CUSTOMER_ID,))
    sites = cursor.fetchall()
    for s in sites:
        raw = s.get("queue_details")
        s["queue_details"] = json.loads(raw) if raw else []
        s["last_login"] = _to_stockholm(s.get("last_login"))
    cursor.close()
    conn.close()
    container = get_container_info()

    system_labels = dict(SYSTEM_TYPES)
    all_system_types = sorted({s["system_type"] for s in sites if s.get("system_type")})

    # Total points per system type and across all sites
    totals = {}
    for s in sites:
        pts = s.get("queue_points")
        if pts is not None:
            st = s.get("system_type", "momentum")
            totals[st] = totals.get(st, 0) + pts
    totals["all"] = sum(totals.values())

    has_momentum = any(s.get("system_type") == "momentum" for s in sites)
    api_key_missing = has_momentum and not get_setting("momentum_api_key")

    return render_template(
        "index.html",
        sites=sites,
        container=container,
        all_system_types=all_system_types,
        system_labels=system_labels,
        totals=totals,
        api_key_missing=api_key_missing,
    )


@app.route("/sites/add", methods=["GET", "POST"])
def add_site():
    if request.method == "POST":
        url_name = request.form["url_name"].strip().lower()
        fullname = request.form["fullname"].strip()
        system_type = request.form.get("system_type", "momentum").strip()
        username = request.form["username"].strip()
        password = request.form["password"]
        active = 1 if request.form.get("active") else 0

        if system_type == "momentum":
            momentum_id = request.form.get("momentum_id", "").strip()
            base_url = None
        else:
            momentum_id = None
            base_url = request.form.get("base_url", "").strip().rstrip("/")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO sites (url_name, fullname, base_url, system_type, momentum_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (url_name, fullname, base_url, system_type, momentum_id)
            )
            cursor.execute(
                "INSERT INTO credentials (site, customer_id, username, password, active) "
                "VALUES (%s, %s, %s, %s, %s)",
                (url_name, CUSTOMER_ID, username, encrypt_password(password), active)
            )
            conn.commit()
            flash(f"Site '{url_name}' added successfully.", "success")
            return redirect(url_for("index"))
        except mysql.connector.IntegrityError as e:
            conn.rollback()
            flash(f"Could not add site: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("site_form.html", site=None, title="Add Site", system_types=SYSTEM_TYPES)


@app.route("/sites/<url_name>/edit", methods=["GET", "POST"])
def edit_site(url_name):
    if request.method == "POST":
        fullname = request.form["fullname"].strip()
        system_type = request.form.get("system_type", "momentum").strip()
        username = request.form["username"].strip()
        password = request.form["password"]
        active = 1 if request.form.get("active") else 0

        if system_type == "momentum":
            momentum_id = request.form.get("momentum_id", "").strip()
            base_url = None
        else:
            momentum_id = None
            base_url = request.form.get("base_url", "").strip().rstrip("/")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE sites SET fullname=%s, base_url=%s, system_type=%s, "
                "momentum_id=%s WHERE url_name=%s",
                (fullname, base_url, system_type, momentum_id, url_name)
            )
            if password:
                cursor.execute(
                    "UPDATE credentials SET username=%s, password=%s, active=%s "
                    "WHERE site=%s AND customer_id=%s",
                    (username, encrypt_password(password), active, url_name, CUSTOMER_ID)
                )
            else:
                cursor.execute(
                    "UPDATE credentials SET username=%s, active=%s "
                    "WHERE site=%s AND customer_id=%s",
                    (username, active, url_name, CUSTOMER_ID)
                )
            conn.commit()
            flash(f"Site '{url_name}' updated.", "success")
            return redirect(url_for("index"))
        except Exception as e:
            conn.rollback()
            flash(f"Could not update site: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.url_name, s.fullname, s.base_url, s.system_type,
               s.momentum_id,
               c.username, c.active
        FROM sites s
        LEFT JOIN credentials c ON c.site = s.url_name AND c.customer_id = %s
        WHERE s.url_name = %s
    """, (CUSTOMER_ID, url_name))
    site = cursor.fetchone()
    cursor.close()
    conn.close()

    if not site:
        flash(f"Site '{url_name}' not found.", "danger")
        return redirect(url_for("index"))

    return render_template("site_form.html", site=site, title="Edit Site", system_types=SYSTEM_TYPES)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        api_key = request.form.get("momentum_api_key", "").strip()
        set_setting("momentum_api_key", api_key)
        flash("Settings saved.", "success")
        return redirect(url_for("settings"))

    current_api_key = get_setting("momentum_api_key")
    return render_template("settings.html", momentum_api_key=current_api_key, api_key_missing=not current_api_key)


@app.route("/api/status")
def api_status():
    info = get_container_info()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT site, last_login FROM credentials WHERE customer_id=%s", (CUSTOMER_ID,))
    logins = {
        row["site"]: _to_stockholm(row["last_login"]).strftime("%Y-%m-%d %H:%M") if row["last_login"] else None
        for row in cursor.fetchall()
    }
    cursor.close()
    conn.close()
    return jsonify({"container_status": info["status"], "last_logins": logins})


@app.route("/run", methods=["POST"])
def run_now():
    try:
        client = docker.from_env()
        container = client.containers.get(CONTAINER_NAME)
        if container.status == "running":
            flash("Queue update is already running.", "warning")
        else:
            container.start()
            flash("Queue update started.", "success")
    except docker.errors.NotFound:
        flash(
            f"Container '{CONTAINER_NAME}' not found. "
            "Make sure it has been created with docker compose up.",
            "danger"
        )
    except Exception as e:
        flash(f"Could not start container: {e}", "danger")
    return redirect(url_for("index"))


@app.route("/sites/<url_name>/toggle-active", methods=["POST"])
def toggle_active(url_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE credentials SET active = 1 - active "
            "WHERE site=%s AND customer_id=%s",
            (url_name, CUSTOMER_ID)
        )
        conn.commit()
        cursor.execute(
            "SELECT active FROM credentials WHERE site=%s AND customer_id=%s",
            (url_name, CUSTOMER_ID)
        )
        row = cursor.fetchone()
        return jsonify({"active": row[0] if row else 0})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/sites/<url_name>/delete", methods=["POST"])
def delete_site(url_name):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM credentials WHERE site=%s", (url_name,))
        cursor.execute("DELETE FROM sites WHERE url_name=%s", (url_name,))
        conn.commit()
        flash(f"Site '{url_name}' deleted.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not delete site: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("index"))


ensure_schema()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
