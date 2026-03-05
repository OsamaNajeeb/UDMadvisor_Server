from flask import Blueprint, request, jsonify
import json
import os
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course

class RequestDataType(BaseModel):
    subject: str
    course_number: str
    
fetch_courses_with_subject_and_number_blueprint = Blueprint('fetch_course_with_subject_and_number', __name__, url_prefix="/api")

@fetch_courses_with_subject_and_number_blueprint.route('/fetch_course_with_subject_and_number', methods=['GET'])
def fetch_course_with_subject_and_number():
    # Validate request
    try:
        request_data = RequestDataType(
            subject=request.args.get('subject'),
            course_number=request.args.get('number'),
        )
    except ValidationError as e:
        if request.args.get('subject') in (None, "") or request.args.get('number') in (None, ""):
            return jsonify({"message": "No subject or course number was passed"}), 400
     
    # Define term cache file name - Hardcoded so people can make future plans
    # Fetching from all the terms since course terms can change
    term_cache_file_fall = F"fall2025.json"
    term_cache_file_winter = F"winter2025.json"
    term_cache_file_summer = F"summer2025.json"
    
    #Open the cache file 
    try:
        with open(os.path.join("cache", term_cache_file_fall), "r") as file:
            courses_fall = json.load(file)
    
        with open(os.path.join("cache", term_cache_file_winter), "r") as file:
            courses_winter = json.load(file)
        
        with open(os.path.join("cache", term_cache_file_summer), "r") as file:
            courses_summer = json.load(file)
    except FileNotFoundError:
        print(f"Cache file not found.")
        
        return jsonify({
            "message": "There was an error fetching the course cache file. Please run the course viewer on this term and try again"
        })

    # Fetch the course data from the term cache file
    matching_courses_fall = [
        course for course in courses_fall
        if course.get("subject") == request_data.subject.strip() and
        str(course.get("courseNumber")) == request_data.course_number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]
    
    matching_courses_winter = [
        course for course in courses_winter
        if course.get("subject") == request_data.subject.strip() and
        str(course.get("courseNumber")) == request_data.course_number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]

    matching_courses_summer = [
        course for course in courses_summer
        if course.get("subject") == request_data.subject.strip() and
        str(course.get("courseNumber")) == request_data.course_number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]


    processed_courses = []
    
    # Returns all the courses that match
    for course in matching_courses_summer + matching_courses_winter + matching_courses_fall:
        processed_course = format_course(course)
        if(len(processed_course) != 0):
            processed_courses.append(processed_course)
    
    return processed_courses, 200
    