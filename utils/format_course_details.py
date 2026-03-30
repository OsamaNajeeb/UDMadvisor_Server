def format_course(course):
    # Filter for only mcnichols campus or online
    campus = course.get("campusDescription", "")
    if campus not in ["McNichols Campus", "Online", "Online &amp; On-campus"]:
        return {}

    # Select only the fields that are relevant
    course_dict = {}
    course_dict["course_name"] = course.get("courseTitle", "")
    course_dict["course_reference_number"] = course.get("courseReferenceNumber", "")
    course_dict["credits"] = course.get("creditHours") if course.get("creditHours") else course.get("creditHourLow", 0)
    course_dict["current_enrollment"] = course.get("enrollment", 0)
    course_dict["course_id"] = course.get("id", "")
    course_dict["section"] = course.get("sequenceNumber", "")
    course_dict["subject"] = course.get("subject", "")
    course_dict["course_number"] = course.get("courseNumber", "")
    course_dict["course_description"] = course.get("subjectDescription", "")
    course_dict["attributes"] = course.get("sectionAttributes", [])
    course_dict["cross_list"] = course.get("crossListText") or course.get("crossList")
    
    # 🚨 THE FIX: ATTEMPT TO CATCH PREREQUISITES 🚨
    # Banner sometimes uses different names, so we check a few common ones
    course_dict["prerequisites"] = course.get("prerequisite", course.get("prerequisiteText", course.get("prerequisites", "")))

    course_dict["faculty"] = [faculty.get("displayName", "") for faculty in course.get("faculty", [])]

    course_dict["meeting_times"] = []
    
    meetings = course.get("meetingsFaculty", [])

    #Some courses have multiple meeting times
    if len(meetings) > 0:
        for idx, meeting in enumerate(meetings):
            meeting_time = {}
            meeting_time["meeting_begin_time"] = meeting["meetingTime"].get("beginTime")
            meeting_time["meeting_end_time"] = meeting["meetingTime"].get("endTime")
            meeting_time["meeting_hours_weekly"] = meeting["meetingTime"].get("hoursWeek")
            meeting_time["monday"] = meeting["meetingTime"].get("monday")
            meeting_time["tuesday"] = meeting["meetingTime"].get("tuesday")
            meeting_time["wednesday"] = meeting["meetingTime"].get("wednesday")
            meeting_time["thursday"] = meeting["meetingTime"].get("thursday")
            meeting_time["friday"] = meeting["meetingTime"].get("friday")
            meeting_time["saturday"] = meeting["meetingTime"].get("saturday")
            meeting_time["sunday"] = meeting["meetingTime"].get("sunday")
            meeting_time["start_date"] = meeting["meetingTime"].get("startDate")
            meeting_time["end_date"] = meeting["meetingTime"].get("endDate")
            meeting_time["building"] = meeting["meetingTime"].get("building")
            meeting_time["campus_description"] = meeting["meetingTime"].get("campusDescription")
            meeting_time["meeting_type_description"] = meeting["meetingTime"].get("meetingTypeDescription")
            
            course_dict["meeting_times"].append(meeting_time)
        

    maximum_enrollment = course.get("maximumEnrollment", 0)
    current_enrollment = course.get("enrollment", 0)
    
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