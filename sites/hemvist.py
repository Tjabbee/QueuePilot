import os
import requests
import urllib3
import re
import json
from requests.exceptions import SSLError


def run_hemvist():
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
        print("🔐 Försöker logga in på Hemvist med certifikatvalidering...")
        response = session.post(login_url, data=payload, allow_redirects=True)
        response.raise_for_status()
    except SSLError:
        print("⚠️ SSL-verifiering misslyckades. Försöker igen utan certifikatkontroll...")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = session.post(login_url, data=payload,
                                allow_redirects=True, verify=False)

    if "mina-sidor" in response.url.lower():
        print("✅ Inloggning lyckades!")
        print(f"🏆 Köpoäng: {get_points(session)} poäng")
        logout(session)
    else:
        print("❌ Inloggning misslyckades. Kontrollera dina uppgifter eller sidan.")


def get_points(session):
    url = ("https://hemvist-minasidor.se/widgets/?widgets%5B%5D=kontaktuppgifter"
           "&widgets%5B%5D=koerochprenumerationer%40STD"
           "&widgets%5B%5D=intresseerbjudandesummering"
           "&widgets%5B%5D=erbjudande.start"
           "&callback=parseJSONP"
    )

    response = session.get(url, verify=False)
    if response.status_code != 200:
        raise Exception("Kunde inte hämta widget-data")

    match = re.search(r"^[^(]*\((.*)\)\s*;?\s*$", response.text, re.DOTALL)
    if not match:
        raise Exception("Kunde inte tolka JSONP")

    data = json.loads(match.group(1))
    points = data["data"].get("koerochprenumerationer@STD", {}).get("kodagar")
    
    if points is None:
        raise Exception("Poängen hittades inte i svaret")
    
    return points

def logout(session):
    logout_url = "https://hemvist-minasidor.se/mina-sidor/?event=logout"
    
    try:
        session.get(logout_url, verify=False)
        print("🚪 Loggade ut från Hemvist.")
    except Exception as e:
        print(f"⚠️ Kunde inte logga ut: {e}")