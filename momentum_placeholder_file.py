# For PLACEHOLDER.se (Momentum)
import os
import base64
import hashlib
import secrets
import requests
from dotenv import load_dotenv
from utils.momentum_client import MomentumClient

load_dotenv(dotenv_path="config/.env")

USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

BASE_URL = "https://LOWERCASE-fastighet.momentum.se/Prod/FIRSTUPPERCASE/PmApi/v2"
API_KEY = "APINUMBER"
DEVICE_KEY = "DEVICENUMBER"

def generate_pkce():
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")
    sha256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(
        sha256).rstrip(b"=").decode("utf-8")
    return code_verifier, code_challenge

def login(username, password):
    code_verifier, code_challenge = generate_pkce()
    nonce = secrets.token_urlsafe(16)
    state = secrets.token_urlsafe(16)

    payload = {
        "method": "password",
        "identifier": username,
        "key": password,
        "returnAddress": "https://minasidor.LOWERCASE.se/signin",
        "codeChallenge": code_challenge,
        "codeChallengeMethod": "S256",
        "nonce": nonce,
        "state": state,
        "requestRefreshToken": True
    }

    response = requests.post(f"{BASE_URL}/auth", json=payload, timeout=5)
    try:
        data = response.json()
    except Exception as e:
        print("⚠️ Kunde inte tolka svaret som JSON:")
        print(response.text)
        raise e

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

def logout(client: MomentumClient):
    payload = {
        "returnAddress": "https://minasidor.LOWERCASE.se/",
        "global": False,
        "keepSingleSignOn": False
    }
    resp = client.post("/auth/logout", json=payload)
    if resp.status_code == 200:
        print("🚪 Utloggning lyckades.")
    else:
        print(f"⚠️ Utloggning misslyckades ({resp.status_code}): {resp.text}")

def run_LOWERCASE():
    token = login(USERNAME, PASSWORD)
    if not token:
        return

    client = MomentumClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        device_key=DEVICE_KEY
    )
    client.set_token(token)

    get_points(client)
    logout(client)

if __name__ == "__main__":
    run_LOWERCASE()
