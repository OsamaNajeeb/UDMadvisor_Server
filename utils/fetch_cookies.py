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
    
    # 🚨 THE FIX 1: Force a full 1080p invisible window so the UI doesn't squish! 🚨
    chrome_options.add_argument("--window-size=1920,1080")
    
    # --- NEW FIXES FOR RENDER CLOUD ---
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-setuid-sandbox")    
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-data")

    # --- SMART PATH SELECTOR ---
    chrome_path = os.getenv("CHROME_PATH")
    driver_path = os.getenv("CHROME_DRIVER_PATH")

    if chrome_path and driver_path:
        # 1. We are running on Render! Use the cloud paths.
        chrome_options.binary_location = chrome_path
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    elif os.path.exists("/opt/render/project/.render/chrome/chrome"):
        # 2. Backup Render fallback
        chrome_options.binary_location = "/opt/render/project/.render/chrome/chrome"
        service = Service(executable_path="/opt/render/project/.render/chrome/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        # 3. We are running locally on Windows! Let Selenium handle it automatically.
        driver = webdriver.Chrome(options=chrome_options)
        
    current_app.logger.info("Launching selenium...")
    
    try:
        # Open the website
        driver.get("https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/registration")
        
        # Wait for the page to load
        driver.implicitly_wait(1)

        # 🚨 THE FIX 2: Upgraded all clicks to wait for the element to be clickable! 🚨
        browse_classes_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "classSearch"))
        )
        browse_classes_button.click()            
        
        # Click the select button
        class_search_select = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "select2-chosen-1"))
        )
        class_search_select.click()
        
        # 🚨 THE FIX: Wait 1 full second for the dropdown animation to finish opening! 🚨
        time.sleep(1)
            
        # Select the input box
        search_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "s2id_autogen1_search"))
        )
        
        # 🚨 THE FIX 2: Use backspaces instead of .clear() so the box doesn't lose focus
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(Keys.BACKSPACE)
        
        # Now type the term safely
        search_input.send_keys(term_name)
        
        # Wait a tiny bit for the search results to populate before hitting enter
        time.sleep(0.5) 
        search_input.send_keys(Keys.RETURN)
   
        dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//ul[contains(@class, 'select2-results')]"))
        )
            
        time.sleep(1)

        try:
            option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'select2-results')]//div"))
            )
            option.click()
            
        except StaleElementReferenceException:
            # Re-find the element if it went stale
            option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//ul[contains(@class, 'select2-results')]//div"))
            )
 
            driver.execute_script("arguments[0].click();", option)

        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "term-go"))
        )
        continue_button.click()
            
        time.sleep(1) # Give the university server a second to actually set the cookies!
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
        # Close the driver
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