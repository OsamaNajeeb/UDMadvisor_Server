from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import StaleElementReferenceException
from flask import current_app
from selenium.webdriver.support import expected_conditions as EC
import time
import json 
import os

def fetch_cookies(term_name: str):
    current_app.logger.info("Fetching cookies...")
    
    # Define the environment for the scraper
    chrome_options = Options()
    
    chrome_options.add_argument("--no-sandbox")  
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--window-size=1920,1080")

    # --- 🚨 THE EXTREME LOW-MEMORY DIET FLAGS 🚨 ---
    chrome_options.add_argument("--single-process")       # Forces Chrome to use 1 core instead of splitting
    chrome_options.add_argument("--no-zygote")            # Disables the Chrome sandbox helper to save RAM
    chrome_options.add_argument("--disable-extensions")   # Blocks any hidden extensions from loading
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Tells Chrome NOT to download images!
    
    # --- NEW FIXES FOR RENDER CLOUD ---
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-setuid-sandbox")    
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-data")

    # --- SMART PATH SELECTOR ---
    chrome_path = os.getenv("CHROME_PATH")
    driver_path = os.getenv("CHROME_DRIVER_PATH")

    if chrome_path and driver_path:
        chrome_options.binary_location = chrome_path
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    elif os.path.exists("/opt/render/project/.render/chrome/chrome"):
        chrome_options.binary_location = "/opt/render/project/.render/chrome/chrome"
        service = Service(executable_path="/opt/render/project/.render/chrome/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
        
    current_app.logger.info("Launching selenium...")
    
    try:
        # Open the website
        driver.get("https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/registration")
        
        # 🚨 THE FIX: Wait up to 30 seconds for the slow cloud server! 🚨
        browse_classes_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "classSearch"))
        )
        browse_classes_button.click()            
        
        # Click the select button
        class_search_select = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "select2-chosen-1"))
        )
        class_search_select.click()
        
        time.sleep(1)
            
        # Select the input box
        search_input = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "s2id_autogen1_search"))
        )
        
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(Keys.BACKSPACE)
        search_input.send_keys(term_name)
        time.sleep(0.5) 
        search_input.send_keys(Keys.RETURN)
   
        dropdown = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.XPATH, "//ul[contains(@class, 'select2-results')]"))
        )
            
        time.sleep(1)

        try:
            option = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'select2-results')]//div"))
            )
            option.click()
        except StaleElementReferenceException:
            option = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'select2-results')]//div"))
            )
            driver.execute_script("arguments[0].click();", option)

        continue_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "term-go"))
        )
        continue_button.click()
            
        time.sleep(2) # Added an extra second here for the server to digest the cookies
        cookies = driver.get_cookies()

        cookies_parsed = {cookie["name"]: cookie["value"] for cookie in cookies}
        
        AWSALB = cookies_parsed.get("AWSALB", "")
        AWSALBCORS = cookies_parsed.get("AWSALBCORS", "")
        JSESSIONID = cookies_parsed.get("JSESSIONID", "")
        
        cookies = {
            "AWSALB":  AWSALB,
            "AWSALBCORS": AWSALBCORS,
            "JSESSIONID":  JSESSIONID,
        } 
        
        current_app.logger.info("Cookies fetched successfully")
        return cookies
    except Exception as e:
        current_app.logger.error('There was an error fetching the cookies')
        raise Exception("Failed to fetch cookies") from e
    finally:
        driver.quit()
        

def fetch_cookies_from_cache(term_name: str):
    try:
        with open("term_cookies_cache.json") as cache_file:
            cache_data = json.load(cache_file)
            if term_name not in cache_data:
                raise Exception(f"{term_name} not found in cache")
            return cache_data[term_name]
    except Exception as e:
        print(f"Cache miss or error: {e}")
        cookies = fetch_cookies(term_name)
        if not cookies:
            print("There was an error fetching the cookies")
            return [], 400
        print("Cookies have been fetched, pushing through the error...")
        return cookies