import os
import json
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, ValidationError, Field
from utils.format_course_details import format_course
from utils.fetch_cookies import fetch_cookies
from requests import Session
import concurrent.futures

class RequestDataType(BaseModel):
    term_name: str
    term_code: str
    subject: str  # <--- NEW: Catches the "ACC,BIO" string from the app
    refresh_course_data: bool = Field(default=False)
    
fetch_courses_blueprint = Blueprint('fetch_courses', __name__, url_prefix="/api")

@fetch_courses_blueprint.route('/fetch_courses', methods=['GET'])
def fetch_courses():
    current_app.logger.info("Fetching courses...")
    
    # 1. Validate the input from the React Native app
    try:
        request_data = RequestDataType(
            term_name=request.args.get('term_name'),
            term_code=request.args.get('term_code'),
            subject=request.args.get('subject'),
            refresh_course_data=str(request.args.get('refresh_course_data')).lower() == 'true' 
        )
    except ValidationError as e:
        current_app.logger.error(e)
        return jsonify({"error": {"code": "INPUT_ERROR", "message": "Term, term code, or subject is missing."}}), 400

    term_code = request_data.term_code
    term_name = request_data.term_name
    
    # 2. Chop "ACC,BIO" into a Python list: ["ACC", "BIO"]
    subject_list = request_data.subject.split(',')
    
    refresh_course_data = request_data.refresh_course_data
    
    # Format term name
    term_name = term_name.replace(" (View Only)", "")
    max_page_size = 250
    
    # API for fetching the courses
    API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
    
    # 3. Make a safe cache file name using the joined list (e.g., fall2024_acc_bio.json)
    term_title = term_name.split(" ")
    safe_subject_str = "_".join(subject_list)[:50] # Limits length for the OS
    term_cache_json_file_name = f"{''.join(term_title).lower()}_{safe_subject_str}.json"
    
    current_app.logger.info(f"Reload the course data/cache: {refresh_course_data}")
   
    # 4. Check Cache First
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
            current_app.logger.info(f'No cache exists for {term_cache_json_file_name}. Fetching live instead.')

    # 5. FETCH LIVE FROM THE UNIVERSITY
    try:          
        cookies = fetch_cookies(term_name=term_name)
    except Exception as e:
        current_app.logger.error(f"Cookie fetch error: {e}")
        return jsonify({"error": {"code": "COOKIES_ERROR", "message": "There was an error fetching cookies, please try again"}}), 500

    session = Session()
    session.cookies.update(cookies)
    
    params = {
        "txt_term": term_code,
        "txt_subject": subject_list, # <--- THE MAGIC FIX: The whole array gets passed here
        "startDatepicker": "",
        "endDatepicker": "",
        "uniqueSessionId": "gro1j1740356345340",
        "sortColumn": "subjectDescription",
        "sortDirection": "asc",
        "enrollmentDisplaySettings": ""
    }
    
    try:
        # Initial fetch to get total courses count
        params_copy = params.copy()
        params_copy.update({
            'pageOffset': 0,
            "pageMaxSize": 10
        })
                
        response = session.get(API_URL, params=params_copy)  
        response_json = response.json()
        
        # Safely grab totalCount just in case the university server glitches
        total_courses = response_json.get("totalCount", 0) 
        
        current_app.logger.info(f"Total courses: {total_courses}")
        
        # Parallel fetch function
        def fetch_page(offset):
            page_params = params.copy()
            page_params.update({
                'pageOffset': offset,
                "pageMaxSize": max_page_size
            })
            res = session.get(API_URL, params=page_params)
            return res.json().get("data", [])
        
        # Calculate offsets
        num_pages = (total_courses // max_page_size) + 1
        offsets = [i * max_page_size for i in range(num_pages)]
        
        # Fetch pages in parallel (max 5 concurrent)
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
        
        # Cache the raw data specifically for this exact combination of subjects
        os.makedirs("cache", exist_ok=True) # Ensure cache folder exists
        with open(os.path.join("cache", term_cache_json_file_name), "w", encoding="utf-8") as f:
            json.dump(courses_data, f)
        
        current_app.logger.info("Courses fetched successfully")
        return courses, 200

    except Exception as e:
        current_app.logger.error(f"Fetch error: {e}")
        return jsonify({"error": {"code": "FETCH_ERROR", "message": "An unexpected error has occurred. Please try again later"}}), 500
    
    finally:
        session.close()