"""
Hemvist Automation Script

Automates the login process to hemvist-minasidor.se, retrieves queue points,
and logs out. Designed to work headlessly with a requests-based session.

Functions:
    run_hemvist(): Main function to log in, fetch points, and log out.
    get_points(session): Fetches and parses JSONP widget to get queue points.
    logout(session): Performs logout from Hemvist.
"""

import json
import os
import re
import requests
import urllib3
from requests.exceptions import SSLError


def run_hemvist():
    """
    Logs into Hemvist, retrieves queue points, and logs out.

    Username and password are loaded from environment variables.
    Uses SSL verification first, then retries without it if needed.
    """
    username = os.getenv("HEMVIST_USERNAME")
    password = os.getenv("HEMVIST_PASSWORD")

    login_url = "https://hemvist-minasidor.se/wp-login.php"
    payload = {
        "log": username,
        "pwd": password,
        "redirect_to": "https://hemvist-minasidor.se/mina-sidor/"
    }

    session = requests.Session()

    try:
        print("🔐 Attempting to log in to Hemvist with certificate validation...")
        response = session.post(login_url, data=payload, allow_redirects=True)
        response.raise_for_status()
    except SSLError:
        print("⚠️ SSL verification failed. Retrying without certificate validation...")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = session.post(login_url, data=payload,
                                allow_redirects=True, verify=False)

    if "mina-sidor" in response.url.lower():
        print("✅ Login successful!")
        print(f"🏆 Queue points: {get_points(session)} points")
        logout(session)
    else:
        print("❌ Login failed. Please check your credentials or the website.")


def get_points(session):
    """
    Retrieves queue points from the Hemvist JSONP widget.

    Args:
        session (requests.Session): Authenticated session.

    Returns:
        int: The number of queue points.

    Raises:
        Exception: If parsing fails or data is not found.
    """
    url = (
        "https://hemvist-minasidor.se/widgets/?widgets%5B%5D=kontaktuppgifter"
        "&widgets%5B%5D=koerochprenumerationer%40STD"
        "&widgets%5B%5D=intresseerbjudandesummering"
        "&widgets%5B%5D=erbjudande.start"
        "&callback=parseJSONP"
    )

    response = session.get(url, verify=False)
    if response.status_code != 200:
        raise requests.HTTPError("Could not fetch widget data")

    match = re.search(r"^[^(]*\((.*)\)\s*;?\s*$", response.text, re.DOTALL)
    if not match:
        raise ValueError("Could not parse JSONP")

    data = json.loads(match.group(1))
    points = data["data"].get("koerochprenumerationer@STD", {}).get("kodagar")

    if points is None:
        raise KeyError("Points not found in the response")

    return points


def logout(session):
    """
    Logs out from Hemvist by calling the logout endpoint.

    Args:
        session (requests.Session): Authenticated session.
    """
    logout_url = "https://hemvist-minasidor.se/mina-sidor/?event=logout"

    try:
        session.get(logout_url, verify=False)
        print("🚪 Logged out from Hemvist.")
    except requests.RequestException as e:
        print(f"⚠️ Failed to log out: {e}")
