import os
import json
from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, ValidationError, Field
from utils.format_course_details import format_course
from utils.fetch_cookies import fetch_cookies
from requests import Session
import concurrent.futures
import time

class RequestDataType(BaseModel):
    term_name: str
    term_code: str
    refresh_course_data: bool = Field(default=False)
    
fetch_courses_blueprint = Blueprint('fetch_courses', __name__, url_prefix="/api")

@fetch_courses_blueprint.route('/fetch_courses', methods=['GET'])
def fetch_courses():
    current_app.logger.info("Fetching courses...")
    
    # Validate the input
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
    
    # Format term name
    term_name = term_name.replace(" (View Only)", "")
    max_page_size = 250
    
    # API for fetching the courses
    API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/searchResults"
    
    term_title = term_name.split(" ")
    term_cache_json_file_name = "".join(term_title).lower() + ".json"
    
    current_app.logger.info(f"Reload the course data/cache: {refresh_course_data}")
   
    # If the user doesn't want to refresh the course data, fetch from cache
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

    try:          
        cookies = fetch_cookies(term_name=term_name)
    except Exception as e:
        current_app.logger.error(f"Cookie fetch error: {e}")
        return jsonify({"error": {"code": "COOKIES_ERROR", "message": "There was an error fetching cookies, please try again"}}), 500

    session = Session()
    session.cookies.update(cookies)
    
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
        # Initial fetch to get total courses count
        params.update({
            'pageOffset': 0,
            "pageMaxSize": 10
        })
                
        response = session.get(API_URL, params=params)  
        response_json = response.json()
        total_courses = response_json["totalCount"]
        
        current_app.logger.info(f"Total courses: {total_courses}")
        
        # Parallel fetch function
        def fetch_page(offset):
            page_params = params.copy()
            page_params.update({
                'pageOffset': offset,
                "pageMaxSize": max_page_size
            })
            response = session.get(API_URL, params=page_params)
            return response.json()["data"]
        
        # Calculate offsets
        num_pages = (total_courses // max_page_size) + 1
        offsets = [i * max_page_size for i in range(num_pages)]
        
        # Fetch pages in parallel (max 5 concurrent)
        courses_data = []
        courses = []
        
        # start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_page, offsets)
            
            for page_data in results:
                courses_data.extend(page_data)
                
                for course in page_data:
                    formatted = format_course(course)
                    if formatted:
                        courses.append(formatted)
        
        # end = time.perf_counter()
        # print(f"Time: {end - start}")
        
        # Cache the raw data
        with open(os.path.join("cache", term_cache_json_file_name), "w", encoding="utf-8") as f:
            json.dump(courses_data, f)
        
        current_app.logger.info("Courses fetched successfully")
        return courses, 200

    except Exception as e:
        current_app.logger.error(f"Fetch error: {e}")
        return jsonify({"error": {"code": "FETCH_ERROR", "message": "An unexpected error has occurred. Please try again later"}}), 500
    
    finally:
        session.close()