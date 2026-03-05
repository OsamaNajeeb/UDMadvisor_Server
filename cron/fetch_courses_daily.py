import requests
import os
from flask import jsonify, Blueprint
import json
from utils.fetch_cookies import fetch_cookies

fetch_courses_daily_cron_blueprint = Blueprint('fetch_current_terms_courses_daily_cronjob', __name__, url_prefix="/api")

# Takes all the requirements satisfied + those not satisfied , and fetches all the data
@fetch_courses_daily_cron_blueprint.route('/fetch_current_terms_courses_daily_cronjob', methods=['POST'])
def fetch_courses_daily():
    print("Fetching courses daily run started")
    
    API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/classSearch/getTerms" 
        
        # Forward the request to the terms API
    response = requests.get(API_URL, params={
        "searchTerm": "", 
        "offset": 1, 
        "max": 10, 
    })
    
    terms = response.json()
    
    current_terms = [term for term in terms if '(View Only)' not in term['description']]
    
    print(current_terms)

    for term in current_terms:
        term_code = term['code']
        term_name = term['description']
        
        cookies = fetch_cookies(term_name=term_name, driver_executable_path="chromedriver-linux64/chromedriver")
        print("Cookies fetched")
        
        # Format term name
        term_name = term_name.replace(" (View Only)", "")
        max_page_size = 500
        
        # API for fetching the courses
        API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
        
        # Fall 2025 -> fall2025.json
        term_cache_json_file =  term_name.replace(" ", "").lower() + ".json"

        params = {
            "txt_term": term_code,
            "startDatepicker": "",
            "endDatepicker": "",
            "uniqueSessionId": "gro1j1740356345340",
            "sortColumn": "subjectDescription",
            "sortDirection": "asc",
            "enrollmentDisplaySettings": ""
        }

        params.update({
            'pageOffset': 0,
            "pageMaxSize": 10
        })
                
        # Fetch total count - will be used to know how many times to fetch while offsetting
        response = requests.get(API_URL, params=params, cookies=cookies)
        
        response_json = response.json()
        
        total_courses = response_json["totalCount"]

        print(f"Total courses length: {total_courses}")
                
        # Start fetching the actual courses        
        courses_data = [] 
    
        print("Fetching all courses...")
    
        for i in range((total_courses//max_page_size) + 1):
            params.update({
                'pageOffset': i * max_page_size,
                "pageMaxSize": max_page_size
            })
        
            response = requests.get(API_URL, params=params, cookies=cookies)
        
            response_json = response.json()
        
            courses_data.extend(response_json["data"])
        
        print("Courses have been fetched")      

        # After the courses have been fetched, store the course data in the cache file
        with open(os.path.join("cache", term_cache_json_file), "w", encoding="utf-8") as f:
            json.dump(courses_data, f, indent=4)

        print("Saved file successfully")

    # Return the API response as JSON
    return jsonify({"message": "Fetched and saved courses successfully"}), response.status_code
