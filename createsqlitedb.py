import json
import sqlite3
from datetime import datetime


def convert_military_to_standard(time_str):
    return datetime.strptime(time_str, "%H%M").strftime("%I:%M %p")

with open("fall2025.json", "r") as file:
    data = json.load(file) 

conn = sqlite3.connect("fall2025.db")

cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS courses;")

cursor.execute("""
   CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT,
    course_name TEXT,
    pre_requisite TEXT,
    attribute TEXT ,
    credits TEXT,
    section TEXT,
    times TEXT
    );
"""
)

for entry in data:
    insert_query = '''
        INSERT INTO courses (course_code, course_name, pre_requisite, section, credits, times, attribute)
        VALUES (?,?,?,?,?,?,?)
    '''
    
    course_code = entry["subject"] + " " + entry["courseNumber"]
    course_name = entry["courseTitle"]
    pre_requisite = 'None'
    section = entry["sequenceNumber"] 
    credits = entry["creditHours"] if entry["creditHours"] else ""
    attributes = []
    for attribute in entry["sectionAttributes"]:
        attributes.append(attribute["description"])
    course_attributes = "\n\n".join(attributes)
    
    days = []
    course_meeting_times = entry["meetingsFaculty"][0]["meetingTime"]
    
    if(course_meeting_times["monday"]):
        days.append("Monday")
    
    if(course_meeting_times["tuesday"]):
        days.append("Tuesday")
    
    if(course_meeting_times["wednesday"]):
        days.append("Wednesday")
    
    if(course_meeting_times["thursday"]):
        days.append("Thursday")
        
    if(course_meeting_times["friday"]):
        days.append("Friday")
        
    if(course_meeting_times["saturday"]):
        days.append("Saturday")
        
    if(course_meeting_times["sunday"]):
        days.append("Sunday")
    
    course_times = "-".join(days)
    
    course_start_time_military = course_meeting_times["beginTime"]
    course_end_time_military = course_meeting_times["endTime"]
    
    if(not course_start_time_military or not course_end_time_military):
        course_scheduled_time = " , -"
    else:
        course_start_time = convert_military_to_standard(course_start_time_military)
        course_end_time = convert_military_to_standard(course_end_time_military)
        
        course_scheduled_time =f"{course_times} , {course_start_time} - {course_end_time}"
 
    cursor.execute(insert_query,(course_code, course_name, pre_requisite, section, credits, course_scheduled_time, course_attributes))

conn.commit()
conn.close()

print("JSON data successfully inserted into SQLite!")
