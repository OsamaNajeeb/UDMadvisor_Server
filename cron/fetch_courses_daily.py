import sys
import os
import requests
from flask import jsonify, Blueprint
import json
import time
import re
import html
from utils.fetch_cookies import fetch_cookies

# Tell Python to look in the main root folder so it can find 'utils'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 🚨 THE PREREQUISITE SCRAPER (Using Session) 🚨 ---
def get_prerequisites(session, crn, term_code):
    prereq_url = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/getSectionPrerequisites"
    try:
        res = session.post(prereq_url, data={"term": term_code, "courseReferenceNumber": crn}, timeout=3)
        if res.ok:
            clean_text = re.sub('<[^<]+>', ' ', res.text).strip()
            clean_text = html.unescape(clean_text)
            clean_text = " ".join(clean_text.split())
            if "No prerequisite" in clean_text or "No corequisite" in clean_text:
                return ""
            return clean_text
    except:
        pass
    return ""

# --- 🚨 THE CROSS-LIST SCRAPER (Using Session) 🚨 ---
def get_crosslist(session, crn, term_code):
    xlst_url = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/getXlstSections"
    try:
        res = session.post(xlst_url, data={"term": term_code, "courseReferenceNumber": crn}, timeout=3)
        if res.ok and res.text.strip():
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', res.text, re.DOTALL | re.IGNORECASE)
            if tbody_match:
                rows = re.findall(r'<tr>(.*?)</tr>', tbody_match.group(1), re.DOTALL | re.IGNORECASE)
                cross_lists = []
                for row in rows:
                    cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                    if len(cols) >= 3:
                        subject_text = html.unescape(cols[1].strip())
                        course_number = cols[2].strip()
                        cross_lists.append(f"{subject_text} {course_number}")
                if cross_lists:
                    return "Cross-listed with: " + ", ".join(cross_lists)
    except:
        pass
    return ""


fetch_courses_daily_cron_blueprint = Blueprint('fetch_current_terms_courses_daily_cronjob', __name__, url_prefix="/api")

@fetch_courses_daily_cron_blueprint.route('/fetch_current_terms_courses_daily_cronjob', methods=['POST'])
def fetch_courses_daily():
    print("Fetching courses daily run started")
    
    API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/classSearch/getTerms" 
        
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

        print(f"\n--- Starting Data Fetch for: {term_name} ---")
        time.sleep(3)
        
        cookies = fetch_cookies(term_name=term_name)
        print("Cookies fetched")
        
        # 🚨 THE MAGIC FIX: Create a persistent "Browser Session" so we don't get blocked! 🚨
        session = requests.Session()
        session.cookies.update(cookies)
        
        term_name = term_name.replace(" (View Only)", "")
        max_page_size = 500
        
        API_URL_SEARCH = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
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
                
        response = session.get(API_URL_SEARCH, params=params)
        response_json = response.json()
        total_courses = response_json["totalCount"]

        print(f"Total courses length: {total_courses}")
        courses_data = [] 
    
        print("Fetching all courses... (This will take a while because it is getting prerequisites and cross-lists!)")
    
        for i in range((total_courses//max_page_size) + 1):
            params.update({
                'pageOffset': i * max_page_size,
                "pageMaxSize": max_page_size
            })
        
            response = session.get(API_URL_SEARCH, params=params)
            response_json = response.json()
            
            page_data = response_json.get("data", [])
            
            for course in page_data:
                crn = course.get("courseReferenceNumber")
                if crn:
                    course["prerequisiteText"] = get_prerequisites(session, crn, term_code)
                    course["crossListText"] = get_crosslist(session, crn, term_code)
            
            courses_data.extend(page_data)
            print(f"Finished a page of {len(page_data)} courses...")
        
        print("Courses have been fetched")      

        with open(os.path.join("cache", term_cache_json_file), "w", encoding="utf-8") as f:
            json.dump(courses_data, f, indent=4)

        print("Saved file successfully")

    return jsonify({"message": "Fetched and saved courses successfully"}), 200