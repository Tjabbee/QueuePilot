"""
Vitec Arena Housing Queue Handler for QueuePilot

Handles automated login to Vitec Arena-based tenant portals (e.g. bostad.kjellberg.se,
minasidor.vatterhem.se). These sites use a standard ASP.NET Core Razor Pages form POST
with anti-forgery cookie protection — no Selenium required.

Login flow:
  1. GET <base_url>/Account/Login  → receives .AspNetCore.Antiforgery cookie + hidden
     __RequestVerificationToken form field.
  2. POST <base_url>/Account/Login  → form-encoded credentials; 302 redirect = success.
  3. GET <base_url>/Account/Logout  → clears the session.
"""

import datetime
import html as html_module
import logging
import os
import re
from typing import Tuple
from urllib.parse import urljoin

import requests

from utils.db import get_connection
from utils.crypto import decrypt_password

CUSTOMER_ID = 1

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


def fetch_site(site: str) -> str:
    """
    Returns the base_url for the given site identifier.

    Args:
        site (str): The site's url_name.

    Returns:
        str: The base URL (e.g. https://bostad.kjellberg.se).

    Raises:
        LookupError: If the site is not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT base_url FROM sites WHERE url_name=%s", (site,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if not result:
        raise LookupError(f"Site '{site}' not found.")
    return result["base_url"]


def fetch_credentials(site: str) -> Tuple[str, str]:
    """
    Fetches username and decrypted password for the given site from the database.

    Args:
        site (str): The site's url_name identifier.

    Returns:
        Tuple[str, str]: The username (personnummer) and plaintext password.

    Raises:
        LookupError: If no active credentials are found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT username, password FROM credentials "
        "WHERE site=%s AND customer_id=%s AND active=1",
        (site, CUSTOMER_ID)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if not result:
        raise LookupError(f"No active credentials found for site '{site}'.")
    return result["username"], decrypt_password(result["password"])


def _extract_antiforgery_token(html: str) -> str | None:
    """Parses the __RequestVerificationToken hidden field value from a page.
    Handles any attribute order (name before value, or value before name)."""
    tag_match = re.search(
        r'<input[^>]*name="__RequestVerificationToken"[^>]*/?>',
        html, re.IGNORECASE
    )
    if not tag_match:
        return None
    val_match = re.search(r'value="([^"]+)"', tag_match.group(0))
    return val_match.group(1) if val_match else None


def login(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    """
    Performs the form-based login for Vitec Arena sites.

    Supports two variants:
    - ASP.NET Core Razor Pages (newer): POSTs UserId/Password to /Account/Login.
    - ASP.NET WebForms (older): POSTs ctl00$...$txtUserID/txtPassword back to the
      login page itself, including all hidden WebForms fields.

    Returns:
        True if login succeeded, False otherwise.
    """
    base_url = base_url.rstrip("/")
    form_page_url = f"{base_url}/mina-sidor/logga-in"

    get_resp = session.get(form_page_url, allow_redirects=True, timeout=15)
    logging.info("GET %s → %s", form_page_url, get_resp.status_code)
    cookie_dict = {c.name: c.value for c in session.cookies}
    logging.info("Cookies after GET: %s", list(cookie_dict.keys()))
    html = get_resp.text

    all_inputs = re.findall(
        r'<input[^>]+name="([^"]+)"[^>]*(?:value="([^"]*)")?',
        html, re.IGNORECASE
    )
    input_dict = dict(all_inputs)

    is_webforms = "__VIEWSTATE" in input_dict

    if is_webforms:
        # --- WebForms postback ---
        # Extract form action (posts back to same page or explicit action)
        action_match = re.search(r'<form[^>]+action="([^"]+)"', html, re.IGNORECASE)
        post_url = urljoin(form_page_url, action_match.group(1)) if action_match else form_page_url

        # Include all hidden fields with their values (VIEWSTATE, EVENTVALIDATION, etc.)
        payload = {name: value for name, value in all_inputs}

        # Find the ctl00$...$txtUserID and txtPassword field names
        user_field = next((n for n in input_dict if n.endswith("$txtUserID")), None)
        pass_field = next((n for n in input_dict if n.endswith("$txtPassword")), None)
        btn_field  = next((n for n in input_dict if n.endswith("$btnLogin")), None)

        if not user_field or not pass_field:
            logging.error("❌ Could not find WebForms login fields on %s", form_page_url)
            return False

        payload[user_field] = username
        payload[pass_field] = password
        if btn_field:
            payload[btn_field] = "Logga in"

        logging.info("WebForms login: POST to %s", post_url)
        post_resp = session.post(post_url, data=payload, allow_redirects=True, timeout=15)
    else:
        # --- ASP.NET Core Razor Pages ---
        login_url = f"{base_url}/Account/Login"

        antiforgery_token = _extract_antiforgery_token(html)
        logging.info("Anti-forgery token found: %s", antiforgery_token is not None)

        payload = {name: value for name, value in all_inputs if value}

        if "Token" in input_dict and not payload.get("Token"):
            af_cookie = next(
                (v for k, v in cookie_dict.items() if "antiforgery" in k.lower()), None
            )
            if af_cookie:
                payload["Token"] = af_cookie
                logging.info("Populated Token from antiforgery cookie.")
            else:
                meta_match = re.search(
                    r'<meta[^>]+name=["\']__RequestVerificationToken["\'][^>]+content=["\']([^"\']+)["\']',
                    html, re.IGNORECASE
                ) or re.search(
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']__RequestVerificationToken["\']',
                    html, re.IGNORECASE
                )
                if meta_match:
                    payload["Token"] = meta_match.group(1)
                    logging.info("Populated Token from meta tag.")
                else:
                    js_match = re.search(
                        r'''(?:token|Token|antiForgery(?:Token)?)\s*[:=]\s*["']([A-Za-z0-9+/=_\-]{20,})["']''',
                        html
                    )
                    if js_match:
                        payload["Token"] = js_match.group(1)
                        logging.info("Populated Token from JS variable.")

        payload.update({"UserId": username, "Password": password, "RememberMe": "false"})

        logging.info("Razor Pages login: POST to %s", login_url)
        post_resp = session.post(login_url, data=payload, allow_redirects=True, timeout=15)

    final_url = post_resp.url.lower()
    logging.info("POST → final URL: %s (status %s)", post_resp.url, post_resp.status_code)

    if "account/login" not in final_url and "logga-in" not in final_url and "bankid" not in final_url:
        logging.info("✅ Login to Vitec Arena (%s) succeeded.", base_url)
        return True

    logging.error("❌ Login to Vitec Arena (%s) failed — final URL: %s", base_url, post_resp.url)
    return False


def _parse_int(s: str) -> int | None:
    """Parses a Swedish-formatted integer string (e.g. '1\xa0520', '2 944')."""
    try:
        return int(s.replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def get_queue_info(session: requests.Session, base_url: str):
    """
    Scrapes queue information from the logged-in Mina sidor page.

    Splits the page into sections by heading tags, then for each section
    extracts the heading name and any Poäng or Ködatum field. Supports
    multiple queues (e.g. normal + student) on the same page.

    Returns:
        Tuple[int | None, list]: (total_points, queue_details list)
    """
    try:
        resp = session.get(f"{base_url}/mina-sidor/", timeout=15)
        html = resp.text

        FIELD_RE = re.compile(
            r'<span[^>]*object-description-type[^>]*>([^<]+)</span>\s*:\s*'
            r'<p[^>]*>\s*([^<]+?)\s*</p>',
            re.IGNORECASE,
        )
        NAME_RE = re.compile(
            r'<p[^>]*user-activity-description-cc[^>]*>\s*([^<]+?)\s*</p>',
            re.IGNORECASE,
        )

        # Each queue is a list-group-object div — split on those boundaries
        chunks = re.split(r'(?=<div[^>]*list-group-object)', html, flags=re.IGNORECASE)

        queues = []
        for chunk in chunks:
            name_match = NAME_RE.search(chunk)
            raw_name = html_module.unescape(name_match.group(1)).strip() if name_match else None
            # "Sök lägenhet" → "Lägenhet", "Sök studentlägenhet" → "Studentlägenhet"
            section_name = re.sub(r'^[Ss]ök\s+', '', raw_name).capitalize() if raw_name else None

            fields = {
                html_module.unescape(k.strip()): html_module.unescape(v.strip())
                for k, v in FIELD_RE.findall(chunk)
            }
            if not fields:
                continue

            # Prefer Poäng
            poang_str = next((v for k, v in fields.items() if "poäng" in k.lower()), None)
            if poang_str:
                pts = _parse_int(poang_str)
                if pts is not None:
                    name = section_name or f"Kö {len(queues) + 1}"
                    logging.info(" - %s: %d poäng", name, pts)
                    queues.append({"name": name, "points": pts, "unit": "poäng"})
                    continue

            # Fall back to days from Ködatum
            kodatum_str = next((v for k, v in fields.items() if "datum" in k.lower()), None)
            if kodatum_str:
                try:
                    kodatum = datetime.date.fromisoformat(kodatum_str)
                    days = (datetime.date.today() - kodatum).days
                    name = section_name or f"Kö {len(queues) + 1}"
                    logging.info(" - %s: %d dagar i kö", name, days)
                    queues.append({"name": name, "points": days, "unit": "dagar i kö"})
                except ValueError:
                    pass

        if not queues:
            logging.info("🔍 No queue data found on /mina-sidor/")
            return None, []

        total = sum(q["points"] for q in queues)
        logging.info("🔍 Total: %d across %d queue(s)", total, len(queues))
        return total, queues

    except requests.RequestException as e:
        logging.warning("⚠️ Could not fetch queue info: %s", e)
        return None, []


def logout(session: requests.Session, base_url: str) -> None:
    """Logs out by calling the logout endpoint."""
    try:
        session.get(f"{base_url}/Account/Logout", timeout=10)
        logging.info("🚪 Logged out from Vitec Arena (%s).", base_url)
    except requests.RequestException as e:
        logging.warning("⚠️ Logout request failed for %s: %s", base_url, e)


def _update_last_login(site: str) -> None:
    """Updates the last_login timestamp in the database for the given site."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE credentials SET last_login=NOW() WHERE site=%s AND customer_id=%s",
        (site, CUSTOMER_ID)
    )
    conn.commit()
    cursor.close()
    conn.close()


def run(site: str) -> None:
    """
    Main runner for a Vitec Arena site: login, record timestamp, logout.

    Args:
        site (str): The site's url_name identifier from the database.
    """
    logging.info("*********** %s (Vitec Arena) ***********", site)

    try:
        base_url = fetch_site(site)
        username, password = fetch_credentials(site)
    except LookupError as e:
        logging.error("❌ %s", e)
        return

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "sv,en-US;q=0.9,en;q=0.8",
    })

    try:
        if login(session, base_url, username, password):
            _update_last_login(site)
            points, details = get_queue_info(session, base_url)
            if points is not None:
                import json
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE credentials SET queue_points=%s, queue_details=%s "
                    "WHERE site=%s AND customer_id=%s",
                    (points, json.dumps(details, ensure_ascii=False), site, CUSTOMER_ID)
                )
                conn.commit()
                cursor.close()
                conn.close()
            logout(session, base_url)
        else:
            logging.error("❌ Skipping %s due to login failure.", site)
    except requests.RequestException as e:
        logging.error("⚠️ Network error for %s: %s", site, e)

    logging.info("*********** %s (Vitec Arena) ***********", site)
