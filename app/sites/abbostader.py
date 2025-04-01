"""
AB Bostäder Automation Script

This module uses Selenium and Requests to automate the login process to
AB Bostäder's tenant portal, retrieve queue points from a JSONP widget,
and log out. Designed to run headlessly in a container or cron-based system.

Functions:
    run_ab_bostader(): Entry point for logging in and retrieving points.
    get_points(driver): Parses the JSONP response to extract queue points.
    logout(driver): Logs out the user by navigating to the logout URL.
"""

import time
import os
import re
import json
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def get_points(driver):
    """
    Extracts queue points from the JSONP widget using session cookies.

    Args:
        driver (webdriver.Chrome): Selenium driver with logged-in session.

    Returns:
        int: Number of queue points (kodagar) if successful.
    """
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
            print("❌ Failed to parse JSONP response")
            return

        json_data = json.loads(match.group(1))
        koepoang = json_data['data']['koerochprenumerationer@STD']['kodagar']
        return koepoang

    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"⚠️ Failed to retrieve queue points: {e}")


def run_ab_bostader():
    """
    Main function to log in to AB Bostäder, fetch queue points, and log out.

    Uses headless Selenium to simulate a login and navigates through
    the tenant portal. Credentials are loaded from environment variables.
    """
    username = os.getenv("ABBOSTADER_USERNAME")
    password = os.getenv("ABBOSTADER_PASSWORD")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("🔗 Navigating to login page...")
        driver.get("https://www.bostaderiboras.se/logga-in/")

        # Try to close cookie popup if available
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button[title="Acceptera alla cookies"]'))
            ).click()
            print("🍪 Closing cookie popup")
        except (TimeoutException, NoSuchElementException) as e:
            print(f"⚠️ No popup found: {e}")

        # Switch to personnummer login
        print("🔄 Switching to username login mode...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pnr-button"))
        )
        driver.find_element(By.ID, "pnr-button").click()
        time.sleep(1)

        print("🧑 Entering username and password...")
        driver.find_element(By.ID, "login-username").send_keys(username)
        driver.find_element(By.ID, "login-password").send_keys(password)

        print("🚪 Logging in...")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[class='login-form__submit ']"))
        )
        login_button = driver.find_element(
            By.CSS_SELECTOR, "button[class='login-form__submit ']")
        login_button.send_keys(Keys.ENTER)
        time.sleep(1)
        login_button.send_keys(Keys.ENTER)  # Double-click workaround

        time.sleep(5)  # Wait for redirect

        if "mina-sidor" in driver.current_url.lower():
            print("✅ Login successful!")
            print(f"🏆 Queue points: {get_points(driver)} points")
            logout(driver)
        else:
            print("❌ Login failed. Please check your credentials or the website.")
    except (TimeoutException, NoSuchElementException, requests.RequestException) as e:
        print(f"⚠️ An error occurred: {e}")

    finally:
        driver.quit()


def logout(driver):
    """
    Logs out from AB Bostäder by redirecting to login page again.

    Args:
        driver (webdriver.Chrome): Active Selenium driver session.
    """
    driver.get("https://www.bostaderiboras.se/logga-in/")
    print("🚪 Logged out from AB Bostäder.")
