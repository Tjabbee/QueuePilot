from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

import time
import os
import requests
import json
import re


def get_koepoang(driver):
    try:
        session = requests.Session()
        cookies = driver.get_cookies()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        widget_url = (
            "https://www.bostaderiboras.se/widgets/"
            "?callback=callback123"
            "&widgets[]=kontaktuppgifter"
            "&widgets[]=koerochprenumerationer@STD"
        )

        response = session.get(widget_url)
        match = re.search(r'callback123\((.*)\)', response.text, re.DOTALL)
        if not match:
            print("❌ Kunde inte parsa JSONP-svaret")
            return

        json_data = json.loads(match.group(1))
        koepoang = json_data['data']['koerochprenumerationer@STD']['kodagar']
        print(f"🏆 Köpoäng: {koepoang} poäng")
        return koepoang

    except Exception as e:
        print(f"⚠️ Misslyckades att hämta köpoäng: {e}")


def run_ab_bostader():
    username = os.getenv("ABBOSTADER_USERNAME")
    password = os.getenv("ABBOSTADER_PASSWORD")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("🔗 Navigerar till inloggningssidan...")
        driver.get("https://www.bostaderiboras.se/logga-in/")

        # Stäng cookie-popup om den finns
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button[title="Acceptera alla cookies"]'))
            ).click()
            print("🍪 Stänger Cookie-popup")
        except Exception as e:
            print(f"⚠️ Ingen popup hittades: {e}")

        # Växla till personnummer-fliken
        print("🔄 Växlar till användarnamn-läge...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pnr-button"))
        )
        driver.find_element(By.ID, "pnr-button").click()
        time.sleep(1)

        print("🧑 Fyller i personnummer och lösenord...")
        driver.find_element(By.ID, "login-username").send_keys(username)
        driver.find_element(By.ID, "login-password").send_keys(password)

        # Dubbelklick-lösning
        print("🚪 Loggar in...")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[class='login-form__submit ']"))
        )
        login_button = driver.find_element(
            By.CSS_SELECTOR, "button[class='login-form__submit ']")
        login_button.send_keys(Keys.ENTER)
        time.sleep(1)
        login_button.send_keys(Keys.ENTER)  # Dubbeltryck

        time.sleep(5)  # Vänta på eventuell redirect

        print(driver.current_url)
        if "mina-sidor" in driver.current_url.lower():
            print("✅ Inloggning lyckades!")
            get_koepoang(driver)
        else:
            print("❌ Inloggning misslyckades, kontrollera dina uppgifter eller sidan.")

    except Exception as e:
        print(f"⚠️ Ett fel inträffade: {e}")

    finally:
        driver.quit()
