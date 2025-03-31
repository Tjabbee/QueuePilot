# For momentum sites
import os
import base64
import hashlib
import secrets
import requests
import mysql.connector
from dotenv import load_dotenv
from utils.momentum_client import MomentumClient

load_dotenv(dotenv_path="app/config/.env")


def fetch_credentials(site, customer_id):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT username, password FROM credentials WHERE site=%s AND customer_id=%s AND active=1",
        (site, customer_id)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise Exception(
            f"Inga uppgifter hittades för kund {customer_id} på site {site}")

    return result["username"], result["password"]

def get_site(site):
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM sites WHERE url_name=%s",
        (site,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise Exception(
            f"Inga uppgifter hittades på site {site}")

    return result["url_name"], result["base_url"], result["api_key"]


def generate_pkce():
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")
    sha256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(
        sha256).rstrip(b"=").decode("utf-8")
    return code_verifier, code_challenge


def login(username, password, url_name, base_url):
    code_verifier, code_challenge = generate_pkce()
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

    response = requests.post(f"{base_url}/auth", json=payload, timeout=5)
    data = response.json()

    if "completed" in data:
        print("✅ Inloggning lyckades!")
        access_token = data["completed"]["accessToken"]
        return access_token
    else:
        print("❌ Inloggning misslyckades:", data)
        return None


def get_points(client: MomentumClient):
    resp = client.get("/market/applicant/status")
    if resp.status_code != 200:
        print("❌ Kunde inte hämta poäng:", resp.status_code)
        print(resp.text)
        return

    data = resp.json()
    print("🔍 Köpoäng:")
    for queue in data.get("queues", []):
        name = queue.get("displayName", "Okänd kö")
        points = queue.get("value", "okänt")
        unit = queue.get("valueUnitDisplayName", "")
        print(f" - {name}: {points} {unit}")

    return points


def logout(client: MomentumClient, url_name):
    payload = {
        "returnAddress": f"https://minasidor.{url_name}.se/",
        "global": False,
        "keepSingleSignOn": False
    }
    resp = client.post("/auth/logout", json=payload)
    if resp.status_code == 200:
        print("🚪 Utloggning lyckades.")
    else:
        print(f"⚠️ Utloggning misslyckades ({resp.status_code}): {resp.text}")


def run(site):
    url_name, base_url, api_key = get_site(site)
    username, password = fetch_credentials(url_name, 1)
    token = login(username, password, url_name, base_url)
    if not token:
        return

    client = MomentumClient(
        base_url=base_url,
        api_key=api_key
    )
    client.set_token(token)

    get_points(client)
    logout(client, url_name)


if __name__ == "__main__":
    run(site="")
