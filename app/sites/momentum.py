"""
Momentum Site Handler for QueuePilot

This module handles the full login-flow and data retrieval for Momentum-based
housing queue systems. It supports:
- Fetching site metadata and customer credentials from MariaDB
- Performing OAuth2 login with PKCE
- Retrieving and displaying current queue points
- Logging out after session

Used by main.py to automate queue maintenance across multiple sites.
"""

from typing import Tuple
import os
import base64
import hashlib
import secrets
import datetime
import logging

import requests
from utils.db import get_connection, get_setting
from utils.crypto import decrypt_password
from utils.momentum_client import MomentumClient

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = datetime.date.today().strftime("%Y-%m-%d") + ".log"
log_path = os.path.join(LOG_DIR, log_filename)
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
from zoneinfo import ZoneInfo as _ZI
logging.Formatter.converter = staticmethod(
    lambda ts: datetime.datetime.fromtimestamp(ts, tz=_ZI("Europe/Stockholm")).timetuple()
)

def fetch_credentials(site: str, customer_id: int) -> Tuple[str, str]:
    """
    Fetches username and password for a given customer on a specific site.

    Args:
        site (str): The site's URL-friendly identifier.
        customer_id (int): The customer/user ID.

    Returns:
        Tuple[str, str]: The username and password.

    Raises:
        Exception: If no matching credentials are found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT username, password FROM credentials WHERE site=%s AND customer_id=%s AND active=1",
        (site, customer_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise LookupError(
            f"No data found for customer {customer_id} on site {site}")

    return result["username"], decrypt_password(result["password"])


def get_site(site: str) -> str:
    """
    Retrieves the Momentum API ID for a given site.

    Args:
        site (str): The site's url_name (e.g. 'kbab').

    Returns:
        str: momentum_id (path segment in the API URL, e.g. 'Kar').

    Raises:
        LookupError: If the site is not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT momentum_id FROM sites WHERE url_name=%s",
        (site,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise LookupError(f"No data found on site {site}")

    return result["momentum_id"]


def generate_pkce() -> Tuple[str, str]:
    """
    Generates PKCE code verifier and code challenge.

    Returns:
        Tuple[str, str]: The code_verifier and code_challenge.
    """
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")
    sha256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(
        sha256).rstrip(b"=").decode("utf-8")
    return code_challenge


def login(username: str, password: str, url_name: str, base_url: str) -> str | None:
    """
    Logs in using OAuth2 + PKCE.

    Args:
        username (str): The user's username.
        password (str): The user's password.
        url_name (str): Site's identifier (e.g. 'kbab').
        base_url (str): The Momentum API base URL.

    Returns:
        str | None: The access token if successful, else None.
    """
    code_challenge = generate_pkce()
    nonce = secrets.token_urlsafe(16)
    state = secrets.token_urlsafe(16)

    payload = {
        "method": "password",
        "identifier": username,
        "key": password,
        "returnAddress": f"https://minasidor.{url_name}.se/signin",
        "codeChallenge": code_challenge,
        "codeChallengeMethod": "S256",
        "nonce": nonce,
        "state": state,
        "requestRefreshToken": True
    }

    response = requests.post(f"{base_url}/auth", json=payload, timeout=10)
    data = response.json()

    if "completed" in data:
        logging.info("✅ Login to %s succeeded!", url_name)
        access_token = data["completed"]["accessToken"]
        return access_token
    else:
        logging.error("❌ Login to %s failed: %s", url_name, data)
        return None


def get_points(client: MomentumClient, url_name: str):
    """
    Retrieves and logs the user's queue points.

    Args:
        client (MomentumClient): Authenticated API client.
        url_name (str): Site's identifier.

    Returns:
        Tuple[int | None, list]: Total points (or None) and per-queue detail list.
    """
    resp = client.get("/market/applicant/status")
    if resp.status_code != 200:
        logging.error("❌ Could not retrieve points from %s: %s", url_name, resp.status_code)
        logging.error(resp.text)
        return None, []

    data = resp.json()
    logging.info("🔍 Queue Points:")
    total = 0
    queues = []
    for queue in data.get("queues", []):
        name = queue.get("displayName", "Unknown queue")
        points = None
        unit = "dagar"

        if "value" in queue:
            raw = queue["value"]
            unit = queue.get("valueUnitDisplayName", "")
            try:
                points = int(raw)
            except (TypeError, ValueError):
                points = None
        elif "joined" in queue:
            # /Date(milliseconds+offset)/ format
            import re
            m = re.search(r'/Date\((\d+)', queue["joined"])
            if m:
                ts = int(m.group(1)) / 1000
                joined_date = datetime.date.fromtimestamp(ts)
                points = (datetime.date.today() - joined_date).days

        logging.info(" - %s: %s %s", name, points, unit)
        queues.append({"name": name, "points": points, "unit": unit})
        if points is not None:
            total += points
    return (total if total > 0 else None), queues


def logout(client: MomentumClient, url_name: str) -> None:
    """
    Logs out the current session.

    Args:
        client (MomentumClient): Authenticated API client.
        url_name (str): Site's identifier.
    """
    payload = {
        "returnAddress": f"https://minasidor.{url_name}.se/",
        "global": False,
        "keepSingleSignOn": False
    }
    resp = client.post("/auth/logout", json=payload)
    if resp.status_code == 200:
        logging.info("🚪 Logout from %s successful.", url_name)
    else:
        logging.error("⚠️ Logout from %s failed (%s): %s", url_name, resp.status_code, resp.text)


def run(site: str, customer_id: int = 1) -> None:
    """
    Main runner for a given site: login, retrieve queue points, logout.

    Args:
        site (str): The site's identifier.
        customer_id (int): The user's credential ID. Defaults to 1 for legacy use.
    """
    url_name = site
    momentum_id = get_site(site)
    if not momentum_id:
        logging.error("❌ %s has no Momentum ID configured — edit the site and fill in the Momentum ID.", url_name)
        return
    api_key = get_setting("momentum_api_key")
    if not api_key:
        logging.error("❌ Momentum API key is not set — go to Settings and enter the API key.")
        return
    base_url = f"https://{url_name}-fastighet.momentum.se/Prod/{momentum_id}/PmApi/v2"
    username, password = fetch_credentials(url_name, customer_id=customer_id)
    logging.info("*********** %s ***********", url_name)
    token = login(username, password, url_name, base_url)
    if not token:
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE credentials SET last_login=NOW() WHERE site=%s AND customer_id=%s",
        (url_name, customer_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    client = MomentumClient(base_url=base_url, api_key=api_key)
    client.set_token(token)

    points, queues = get_points(client, url_name)
    if points is not None or queues:
        import json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE credentials SET queue_points=%s, queue_details=%s "
            "WHERE site=%s AND customer_id=%s",
            (points, json.dumps(queues, ensure_ascii=False), url_name, customer_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    logout(client, url_name)
    logging.info("*********** %s ***********", url_name)

if __name__ == "__main__":
    run(site="")
