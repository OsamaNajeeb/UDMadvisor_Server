import os
import json
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, ValidationError, Field
from utils.format_course_details import format_course
from requests import Session
import concurrent.futures

class RequestDataType(BaseModel):
    term_name: str
    term_code: str
    refresh_course_data: bool = Field(default=False)
    
fetch_courses_blueprint = Blueprint('fetch_courses', __name__, url_prefix="/api")

@fetch_courses_blueprint.route('/fetch_courses', methods=['GET'])
def fetch_courses():
    current_app.logger.info("Fetching courses...")
    
    try:
        request_data = RequestDataType(
            term_name=request.args.get('term_name'),
            term_code=request.args.get('term_code'),
            refresh_course_data=request.args.get('refresh_course_data')
        )
    except ValidationError as e:
        if request.args.get('term_name') in (None, "") or request.args.get('term_code') in (None, ""):
            current_app.logger.error(e)
            return jsonify({"error": {"code": "INPUT_ERROR", "message": "Term code or term name is missing. Try selecting another term"}}), 400

    term_code = request_data.term_code
    term_name = request_data.term_name
    refresh_course_data = request_data.refresh_course_data
    
    term_name = term_name.replace(" (View Only)", "")
    max_page_size = 250
    API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
    
    term_title = term_name.split(" ")
    term_cache_json_file_name = "".join(term_title).lower() + ".json"
    
    current_app.logger.info(f"Reload the course data/cache: {refresh_course_data}")
   
    if not refresh_course_data:
        try:
            current_app.logger.info(f"Checking if {term_cache_json_file_name} is in cache")
            with open(os.path.join("cache", term_cache_json_file_name), "r") as file:
                course_data = json.load(file)
                
                courses = []
                for course in course_data:
                    formatted_course = format_course(course)
                    if formatted_course:
                        courses.append(formatted_course)
                
                current_app.logger.info("%s fetched successfully from cache", term_cache_json_file_name)
                return courses, 200

        except FileNotFoundError:
            current_app.logger.error('No cache file exists for the term the user tried to fetch: %s.', term_cache_json_file_name)
            return jsonify({"error": {"code": "NO_CACHE_FILE_EXISTS", "message": "No data exists for this term. Please click the refresh course data and try again"}}), 404

    # --- 🚨 THE SMART MERGE 🚨 ---
    existing_extras = {}
    try:
        with open(os.path.join("cache", term_cache_json_file_name), "r") as file:
            old_data = json.load(file)
            for old_course in old_data:
                crn = old_course.get("courseReferenceNumber")
                if crn:
                    existing_extras[crn] = {
                        "prerequisiteText": old_course.get("prerequisiteText", ""),
                        "crossListText": old_course.get("crossListText", "")
                    }
    except FileNotFoundError:
        pass 

    # --- 🚨 THE GOD-MODE FIX: NO SELENIUM, NO CHROME, NO CRASHING 🚨 ---
    session = Session()
    try:
        current_app.logger.info("Bypassing Selenium and authenticating directly via Python...")
        
        # 1. Hit the main page to grab the hidden JSESSIONID
        session.get("https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/term/termSelection?mode=search", timeout=10)
        
        # 2. Tell the server exactly which term we want to look at (This replaces the UI dropdown click!)
        term_url = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/term/search?mode=search"
        auth_response = session.post(term_url, data={"term": term_code}, timeout=10)
        
        if not auth_response.ok:
            raise Exception("Failed to set the term in the university system.")
            
        current_app.logger.info("Successfully authenticated via direct POST!")
    except Exception as e:
        current_app.logger.error(f"Direct auth error: {e}")
        return jsonify({"error": {"code": "AUTH_ERROR", "message": "Failed to connect to the university system."}}), 500

    params = {
        "txt_term": term_code,
        "startDatepicker": "",
        "endDatepicker": "",
        "uniqueSessionId": "gro1j1740356345340",
        "sortColumn": "subjectDescription",
        "sortDirection": "asc",
        "enrollmentDisplaySettings": ""
    }
    
    try:
        params.update({'pageOffset': 0, "pageMaxSize": 10})
        response = session.get(API_URL, params=params)  
        response_json = response.json()
        total_courses = response_json.get("totalCount", 0)
        
        current_app.logger.info(f"Total courses: {total_courses}")

        def fetch_page(offset):
            page_params = params.copy()
            page_params.update({'pageOffset': offset, "pageMaxSize": max_page_size})
            res = session.get(API_URL, params=page_params)
            page_data = res.json().get("data", [])
            
            for course in page_data:
                crn = course.get("courseReferenceNumber")
                if crn and crn in existing_extras:
                    course["prerequisiteText"] = existing_extras[crn]["prerequisiteText"]
                    course["crossListText"] = existing_extras[crn]["crossListText"]
                    
            return page_data
        
        num_pages = (total_courses // max_page_size) + 1
        offsets = [i * max_page_size for i in range(num_pages)]
        
        courses_data = []
        courses = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_page, offsets)
            for page_data in results:
                courses_data.extend(page_data)
                for course in page_data:
                    formatted = format_course(course)
                    if formatted:
                        courses.append(formatted)
        
        os.makedirs("cache", exist_ok=True)
        with open(os.path.join("cache", term_cache_json_file_name), "w", encoding="utf-8") as f:
            json.dump(courses_data, f)
        
        current_app.logger.info("Courses fetched successfully")
        return courses, 200

    except Exception as e:
        current_app.logger.error(f"Fetch error: {e}")
        return jsonify({"error": {"code": "FETCH_ERROR", "message": "An unexpected error has occurred."}}), 500
    finally:
        session.close()