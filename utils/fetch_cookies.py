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

    chrome_options.binary_location = os.getenv("CHROME_PATH", "/opt/render/project/.render/chrome/chrome")

    service = Service(executable_path=os.getenv('CHROME_DRIVER_PATH', "/opt/render/project/.render/chrome/chromedriver"))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    current_app.logger.info("Launching selenium...")
    
    try:
        # Open the website
        driver.get("https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/registration")
        
        # Wait for the page to load
        driver.implicitly_wait(1)

        browse_classes_button = driver.find_element(By.ID, "classSearch")
        browse_classes_button.click()            
        driver.implicitly_wait(1)

        # Click the select button
        class_search_select = driver.find_element(By.ID, "select2-chosen-1")
        class_search_select.click()
            
        # Clear if there's anything on there, then type the semester and select the first result
        search_input = driver.find_element(by=By.ID,value="s2id_autogen1_search")
        search_input.clear()
        search_input.send_keys(term_name)
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

        driver.implicitly_wait(1)
            
        continue_button = driver.find_element(by=By.ID,value="term-go")
        continue_button.click()
            
        driver.implicitly_wait(1)
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
                raise Exception("")
            
            return cache_data[term_name]
    except Exception as e:
        print(e)
        fetch_cookies(term_name)
        if not cookies:
            print("There was an error fetching the cookies")
            return [], 400
        
        print("Cookies have been fetched pushing through the error...")
            
        cookies_parsed = {cookie["name"]: cookie["value"] for cookie in cookies}
        
        AWSALB = cookies_parsed.get("AWSALB", "")
        AWSALBCORS = cookies_parsed.get("AWSALBCORS", "")
        JSESSIONID = cookies_parsed.get("JSESSIONID", "")
        
        cookies = {
            "AWSALB":  AWSALB,
            "AWSALBCORS": AWSALBCORS,
            "JSESSIONID":  JSESSIONID,
        } 
        
        return cookies
        
    