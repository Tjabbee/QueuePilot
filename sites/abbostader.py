import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

import time



def run_ab_bostader():
    username = os.getenv("ABBOSTADER_USERNAME")  # t.ex. personnummer
    password = os.getenv("ABBOSTADER_PASSWORD")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    service = Service()
    driver = webdriver.Chrome(service=service)

    try:
        print("🔗 Navigerar till inloggningssidan...")
        driver.get("https://www.bostaderiboras.se/logga-in/")
        time.sleep(2)
        
        # Vänta på cookie-banner och stäng den om den finns
        print("🍪 Stänger Cookie-popup")
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[title="Acceptera alla cookies"]'))
        )
        cookies_button = driver.find_element(
            By.CSS_SELECTOR, 'button[title="Acceptera alla cookies"]')
        driver.execute_script("arguments[0].click();", cookies_button)
        time.sleep(2)

        print("🔄 Växlar till användarnamn-läge...")
        pnr_tab = driver.find_element(By.ID, "pnr-button")
        pnr_tab.click()
        time.sleep(1)

        print("🧑 Fyller i personnummer och lösenord...")
        driver.find_element(By.ID, "login-username").send_keys(username)
        driver.find_element(By.ID, "login-password").send_keys(password)


        print("🚪 Loggar in...")
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login-form__submit"))
        )
        login_button = driver.find_element(
            By.CSS_SELECTOR, "button.login-form__submit")
        driver.execute_script("arguments[0].click();", login_button)

        time.sleep(5)  # Vänta på inloggning, kan justeras
        print(driver.current_url.lower())

        if "mina-sidor" in driver.current_url.lower():
            print("✅ Inloggning lyckades!")
        else:
            print("❌ Inloggning misslyckades, kontrollera dina uppgifter eller sidan.")

    except Exception as e:
        print(f"⚠️ Ett fel inträffade: {e}")

    finally:
        driver.quit()
