from flask import Blueprint, request, jsonify
import requests
import requests
from bs4 import BeautifulSoup
import re

analyze_prerequisites_blueprint = Blueprint('analyze_prerequisites', __name__, url_prefix="/api")

course_names = {
    "Accounting": "ACC",
    "Addiction Studies": "ADS",
    "Advanced Electric Vehicle": "AEV",
    "African-American Studies": "AAS",
    "American Language & Culture": "ALCP",
    "Anesthesiology": "ANE",
    "Arabic": "ARB",
    "Architectural Engineering": "AENG",
    "Architecture": "ARCH",
    "Biology": "BIO",
    "Business Administration": "BUS",
    "Career & Prof Development": "CCPD",
    "Catholic Studies": "CAS",
    "Chemistry": "CHM",
    "Chinese": "CHI",
    "Civil Engineering": "CIVE",
    "Communication Studies": "CST",
    "Community Dentistry": "COM",
    "Community Development": "MCD",
    "Comp Sci/Software Engineering": "CSSE",
    "Computer & Information Systems": "CIS",
    "Counseling": "CNS",
    "Criminal Justice": "CJS",
    "Cybersecurity": "CYBE",
    "Data Analytics": "DATA",
    "Dental General": "DENT",
    "Economics": "ECN",
    "Electrical Engineering": "ELEE",
    "Engineering": "ENGR",
    "Engineering Co-op": "CTA",
    "English": "ENL",
    "Ethical Leadership": "ETHL",
    "Ethics": "ETH",
    "Fine Arts": "FINA",
    "French": "FRE",
    "Geography": "GEO",
    "German": "GER",
    "Graduate Assistant": "GRA",
    "Health Professions": "HLH",
    "Health Services Administration": "HSA",
    "History": "HIS",
    "Honors": "HON",
    "Intelligence Analysis": "INT",
    "Islamic Studies": "ISLM",
    "Japanese": "JPN",
    "Korean": "KOR",
    "Latin": "LAT",
    "Law": "LAW",
    "Leadership": "LEAD",
    "Legal Studies": "LST",
    "Liberal Studies": "MLS",
    "MBA": "MBA",
    "Mathematics": "MTH",
    "Mechanical Engineering": "MENG",
    "Museum Studies": "MUSM",
    "Music": "MUS",
    "Nursing": "NUR",
    "Philosophy": "PHL",
    "Physician Assistant": "PAS",
    "Physics": "PHY",
    "Polish": "PLS",
    "Political Science": "POL",
    "Product Development": "MPD",
    "Psychology": "PYC",
    "Religious Studies": "RELS",
    "Science": "SCIE",
    "Social Work": "SWK",
    "Sociology": "SOC",
    "Spanish": "SPA",
    "Statistics": "STA",
    "Theatre": "TRE",
    "University Academic Services": "UAS",
    "Vehicle Cyber Engineering": "VCE",
    "Women's & Gender Studies": "WGS"
}

def parse_prerequisites(html):
    """Parses prerequisites from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    section = soup.find("section", {"aria-labelledby": "preReqs"})
    if not section:
        return []

    table = section.find("table")
    if not table:
        return []

    course_names = []
    for td in table.find_all("td"):
        text = td.get_text(strip=True)
        # Try to extract course info using a regex
        match = re.search(r'Course or Test:\s*(.+?)\s{2,}', text)
        if match:
            course_names.append(match.group(1))
    return course_names


def fetch_prerequisites(subject, number):  
    url = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/searchResults/getSectionPrerequisites"

    session = requests.Session()  # Maintain session
    response = session.get(url)

    cookies = session.cookies.get_dict()  # Extract cookies

    AWSALB = cookies.get("AWSALB", "")
    AWSALBCORS = cookies.get("AWSALBCORS", "")
    JSESSIONID = cookies.get("JSESSIONID", "")

    API_URL_PREREQS = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/courseSearchResults/getPrerequisites"

    params_fall = {
        "term": "202610",
        "subjectCode": subject,
        "courseNumber": number
    }
    
    # params_winter = {
    #     "term": "202520",
    #     "subjectCode": subject,
    #     "courseNumber": number
    # }
    
    cookies = {
            "AWSALB":  AWSALB,
            "AWSALBCORS": AWSALBCORS,
            "JSESSIONID":  JSESSIONID,
    }
    
    prereqs_response_fall = requests.post(API_URL_PREREQS, params=params_fall, cookies=cookies)
    # prereqs_response_winter = requests.post(API_URL_PREREQS, params=params_winter, cookies=cookies)

    course_prereqs_fall = prereqs_response_fall.text
    # course_prereqs_winter = prereqs_response_winter.text
    
    
    prerequisites_fall = parse_prerequisites(course_prereqs_fall)
    # prerequisites_winter = parse_prerequisites(course_prereqs_winter)
    
    # prerequisites = prerequisites_fall + prerequisites_winter
        
    return prerequisites_fall


@analyze_prerequisites_blueprint.post('/analyze_prerequisites')
def analyze_prerequisites():
    try:
        data = request.json
        current_semester = data['semester']
        past_semesters = data['past_semesters']

        prereqs = []
        
        # Return the API response as JSON        
        for course in current_semester['courses']:
            prereqs.extend(fetch_prerequisites(course.get('subject'), course.get('number')))

        prereqs = set(prereqs)
        
        formatted_prereqs = []
        
        for prereq in prereqs:
            course_name_unformatted= ' '.join(prereq.split(' ')[:-1])
            parsed_subject = course_names[course_name_unformatted]
            formatted_prereqs.append(f"{parsed_subject} {prereq.split(' ')[-1]}")       
 
        # TODO: Prerequisites for past group courses
 
        for past_sem in past_semesters:
            for course in past_sem['courses']:
                if f"{course.get('subject')} {course.get('number')}" in formatted_prereqs:
                    formatted_prereqs.remove(f"{course['subject']} {course['number']}")

  
        return jsonify(list(set(formatted_prereqs))), 200
    except Exception as e:
        print(f"{e}")
        return jsonify({"error": {"code": "PREREQUISITES_ERROR", "message": "There was an error fetching prerequisites"}}), 500
    
@analyze_prerequisites_blueprint.route('/analyze_all_prerequisites', methods=['POST'])
def analyze_all_prerequisites():
    try:
        data = request.json
        semesters = data['semesters']
        
        completed_courses = set()
        semester_prereq_issues = []

        for idx, semester in enumerate(semesters):
            term = semester.get("term", f"Term {idx}")
            level = semester.get("level", "")
            label = f"{level} {term}"
            missing_prereqs = []

            for course in semester.get("courses", []):
                course_id = f"{course['subject']} {course['number']}"
                prereqs = fetch_prerequisites(course['subject'], course['number'])

                for prereq in prereqs:
                    parts = prereq.split(' ')
                    prereq_course_name = ' '.join(parts[:-1])
                    prereq_number = parts[-1]

                    if prereq_course_name not in course_names:
                        continue  # skip if unknown subject

                    prereq_subject = course_names[prereq_course_name]
                    prereq_full = f"{prereq_subject} {prereq_number}"

                    if prereq_full not in completed_courses:
                        missing_prereqs.append({
                            "course": course_id,
                            "missing_prereq": prereq_full
                        })

            semester_prereq_issues.append({
                "semester": label,
                "unresolved_prerequisites": missing_prereqs
            })

            # Only after checking prerequisites do we "complete" this semester's courses
            for course in semester.get("courses", []):
                completed_courses.add(f"{course['subject']} {course['number']}")

        return jsonify(semester_prereq_issues), 200

    except Exception as e:
        print(f"analyze_all_prerequisites error: {e}")
        return jsonify({"message": "error"}), 500
