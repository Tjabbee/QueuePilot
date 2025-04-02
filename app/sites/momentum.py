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
from utils.db import get_connection
from utils.momentum_client import MomentumClient

LOG_DIR = "logs"
CUSTOMER_ID = 1
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = datetime.date.today().strftime("%Y-%m-%d") + ".log"
log_path = os.path.join(LOG_DIR, log_filename)
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
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

    return result["username"], result["password"]


def get_site(site: str) -> Tuple[str, str, str]:
    """
    Retrieves base_url and API key for a given site.

    Args:
        site (str): The site's identifier (e.g. 'kbab').

    Returns:
        Tuple[str, str, str]: url_name, base_url, api_key.

    Raises:
        Exception: If the site is not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sites WHERE url_name=%s",
        (site,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise LookupError(f"No data found on site {site}")

    return result["url_name"], result["base_url"], result["api_key"]


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
        url_name (str): Site's subdomain part (e.g. 'kbab').
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


def get_points(client: MomentumClient, url_name: str) -> None:
    """
    Retrieves and prints the user's queue points.

    Args:
        client (MomentumClient): Authenticated API client.
        url_name (str): Site's identifier.
    """
    resp = client.get("/market/applicant/status")
    if resp.status_code != 200:
        logging.error("❌ Could not retrieve points from %s: %s", url_name, resp.status_code)
        logging.error(resp.text)
        return

    data = resp.json()
    logging.info("🔍 Queue Points:")
    for queue in data.get("queues", []):
        name = queue.get("displayName", "Unknown queue")
        points = queue.get("value", "unknown")
        unit = queue.get("valueUnitDisplayName", "")
        logging.info(" - %s: %s %s", name, points, unit)


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


def run(site: str) -> None:
    """
    Main runner for a given site: login, retrieve queue points, logout.

    Args:
        site (str): The site's identifier.
    """
    url_name, base_url, api_key = get_site(site)
    username, password = fetch_credentials(url_name, customer_id=1)
    logging.info("*********** %s ***********", url_name)
    token = login(username, password, url_name, base_url)
    if not token:
        return

    client = MomentumClient(base_url=base_url, api_key=api_key)
    client.set_token(token)

    get_points(client, url_name)
    logout(client, url_name)
    logging.info("*********** %s ***********", url_name)

if __name__ == "__main__":
    run(site="")
