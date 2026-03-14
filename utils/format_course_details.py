def format_course(course):
    # Filter for only mcnichols campus or online
    if(course["campusDescription"] != "McNichols Campus" and course["campusDescription"] != "Online" and course["campusDescription"] != "Online &amp; On-campus" ):
        return {}

    # Select only the fields that are relevant
    course_dict = {}
    course_dict["course_name"] = course["courseTitle"]
    course_dict["course_reference_number"] = course["courseReferenceNumber"]
    course_dict["credits"] = course["creditHours"] if course["creditHours"] else course["creditHourLow"]
    course_dict["current_enrollment"] = course["enrollment"]
    course_dict["course_id"] = course["id"]
    course_dict["section"] = course["sequenceNumber"]
    course_dict["subject"] = course["subject"]
    course_dict["course_number"] = course["courseNumber"]
    course_dict["course_description"] = course["subjectDescription"]
    course_dict["attributes"] = course["sectionAttributes"]
    course_dict["faculty"] = [faculty["displayName"] for faculty in course["faculty"]]

    course_dict["meeting_times"] = []
    
    meetings = course["meetingsFaculty"]

    #Some courses have multiple meeting times
    if len(meetings) > 0:
        for idx, meeting in enumerate(meetings):
            meeting_time = {}
            meeting_time["meeting_begin_time"] = meeting["meetingTime"]["beginTime"]
            meeting_time["meeting_end_time"] = meeting["meetingTime"]["endTime"]
            meeting_time["meeting_hours_weekly"] = meeting["meetingTime"]["hoursWeek"]
            meeting_time["monday"] = meeting["meetingTime"]["monday"]
            meeting_time["tuesday"] = meeting["meetingTime"]["tuesday"]
            meeting_time["wednesday"] = meeting["meetingTime"]["wednesday"]
            meeting_time["thursday"] = meeting["meetingTime"]["thursday"]
            meeting_time["friday"] = meeting["meetingTime"]["friday"]
            meeting_time["saturday"] = meeting["meetingTime"]["saturday"]
            meeting_time["sunday"] = meeting["meetingTime"]["sunday"]
            meeting_time["start_date"] = meeting["meetingTime"]["startDate"]
            meeting_time["end_date"] = meeting["meetingTime"]["endDate"]
            meeting_time["building"] = meeting["meetingTime"]["building"]
            meeting_time["campus_description"] = meeting["meetingTime"]["campusDescription"]
            meeting_time["meeting_type_description"] = meeting["meetingTime"]["meetingTypeDescription"]
            
            course_dict["meeting_times"].append(meeting_time)
        

    maximum_enrollment = course.get("maximumEnrollment", 0)
    current_enrollment = course.get("enrollment", 0)
    
    # 🚨 THE FIX: Inject the missing data into the dictionary so React can see it! 🚨
    course_dict["maximum_enrollment"] = maximum_enrollment
    course_dict["seats_available"] = course.get("seatsAvailable", 0)
    
    # Keep the existing logic for waitlists and "Full" status
    if maximum_enrollment == current_enrollment:
        course_dict["enrollment_is_full"] = True
        course_dict["wait_count"] = course.get("waitCount", 0)
        course_dict["wait_capacity"] = course.get("waitCapacity", 0)
    else:
        course_dict["enrollment_is_full"] = False
        
    return course_dict
