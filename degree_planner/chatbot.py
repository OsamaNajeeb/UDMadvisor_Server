from flask import Blueprint, request, jsonify, Response, stream_with_context
from openai import OpenAI
from database import get_db
import re
import requests
from utils.format_course_details import format_course
import json 
import os

chat_client = OpenAI(
    api_key=os.environ["HF_TOKEN"],
    base_url="https://router.huggingface.co/v1"
)

model = "openai/gpt-oss-20b:nebius"

chatbot_blueprint = Blueprint('chat', __name__, url_prefix="/api")

# Define your tool functions
def prerequisites_corequisites_search(course_name):
    url = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/courseSearchResults/getCorequisites"

    session = requests.Session()
    response = session.get(url)

    cookies = session.cookies.get_dict()  # Extract cookies

    AWSALB = cookies.get("AWSALB", "")
    AWSALBCORS = cookies.get("AWSALBCORS", "")
    JSESSIONID = cookies.get("JSESSIONID", "")

    API_URL_PREREQS = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/courseSearchResults/getPrerequisites"
    API_URL_COREQS = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/courseSearchResults/getCorequisites"

    params = {
        "term": "202610",
        "subjectCode": course_name.split(" ")[0],
        "courseNumber": course_name.split(" ")[1]
    }

    cookies = {
            "AWSALB":  AWSALB,
            "AWSALBCORS": AWSALBCORS,
            "JSESSIONID":  JSESSIONID,
    }

    prereqs_response = requests.post(API_URL_PREREQS, params=params, cookies=cookies)
    coreqs_response = requests.post(API_URL_COREQS, params=params, cookies=cookies)

    course_prereqs = prereqs_response.text
    course_coreqs = coreqs_response.text

    return course_prereqs, course_coreqs


def fetch_course_info(course_name):
    # Define term cache file name - Hardcoded so people can make future plans
    term_cache_file_fall = F"fall2025.json"
    term_cache_file_winter = F"winter2025.json"
    
    subject  = course_name.split(" ")[0]
    number = course_name.split(" ")[1]
    
    #Open the cache file 
    try:
        with open(os.path.join("cache", term_cache_file_fall), "r") as file:
            courses_fall = json.load(file)
    
        with open(os.path.join("cache", term_cache_file_winter), "r") as file:
            courses_winter = json.load(file)
        
    except FileNotFoundError:
        print(f"Cache file not found.")
        
        return jsonify({
            "message": "There was an error fetching the course cache file. Please run the course viewer on this term and try again"
        })
        
    # Fetch the course data from the term cache file
    matching_courses_fall = [
        course for course in courses_fall
        if course.get("subject") == subject.strip() and
        str(course.get("courseNumber")) == number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]
    
    matching_courses_winter = [
        course for course in courses_winter
        if course.get("subject") == subject.strip() and
        str(course.get("courseNumber")) == number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]

    # Combine and deduplicate courses based on a unique key (e.g., CRN or subject+number+section)
    seen = set()
    unique_courses = []
    for course in matching_courses_winter + matching_courses_fall:
        # Use a tuple of (subject, courseNumber, section) as a unique identifier
        key = (
            course.get("subject"),
            str(course.get("courseNumber")),
            course.get("section", "")
        )
        if key not in seen:
            seen.add(key)
            unique_courses.append(course)

    processed_courses = []
    for course in unique_courses:
        processed_course = format_course(course)
        if len(processed_course) != 0:
            processed_courses.append(processed_course)
            
            
    return f"Information about {processed_courses}"

def fetch_course_attributes(course_name):
     # Define term cache file name - Hardcoded so people can make future plans
    term_cache_file_fall = F"fall2025.json"
    term_cache_file_winter = F"winter2025.json"
    
    subject  = course_name.split(" ")[0]
    number = course_name.split(" ")[1]
    
    #Open the cache file 
    try:
        with open(os.path.join("cache", term_cache_file_fall), "r") as file:
            courses_fall = json.load(file)
    
        with open(os.path.join("cache", term_cache_file_winter), "r") as file:
            courses_winter = json.load(file)
        
    except FileNotFoundError:
        print(f"Cache file not found.")
        
        return jsonify({
            "message": "There was an error fetching the course cache file. Please run the course viewer on this term and try again"
        })

    # Fetch the course data from the term cache file
    matching_courses_fall = [
        course for course in courses_fall
        if course.get("subject") == subject.strip() and
        str(course.get("courseNumber")) == number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]
    
    matching_courses_winter = [
        course for course in courses_winter
        if course.get("subject") == subject.strip() and
        str(course.get("courseNumber")) == number.strip() and 
        (str(course.get("campusDescription")) == "McNichols Campus" or str(course.get("campusDescription")) == "Online"  or  str(course.get("campusDescription")) == "Online &amp; On-campus" )
    ]

    processed_courses = []
    
    # Returns all the courses that match
    for course in matching_courses_winter + matching_courses_fall:
        processed_course = format_course(course)
        if(len(processed_course) != 0):
            processed_courses.append(processed_course)
           
    return f"Information about {processed_courses}"
    

# Define tools schema
from openai.types.chat import ChatCompletionFunctionToolParam

tools = [
    ChatCompletionFunctionToolParam(
        type="function",
        function={
            "name": "prerequisites_corequisites_search",
            "description": "Get prerequisites and corequisites information for a course",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "The name or code of the course (e.g., 'CSSE 1710')"
                    }
                },
                "required": ["course_name"]
            }
        }
    ),
    ChatCompletionFunctionToolParam(
        type="function",
        function={
            "name": "fetch_course_info",
            "description": "Get detailed information about a course including description, credits, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "The name or code of the course"
                    }
                },
                "required": ["course_name"]
            }
        }
    ),
    ChatCompletionFunctionToolParam(
        type="function",
        function={
            "name": "fetch_course_attributes",
            "description": "Get the section attributes for a course (e.g., C1, B1, Core)",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "The name or code of the course"
                    }
                },
                "required": ["course_name"]
            }
        }
    )
]

# Map function names to actual functions
available_functions = {
    "prerequisites_corequisites_search": prerequisites_corequisites_search,
    "fetch_course_info": fetch_course_info,
    "fetch_course_attributes": fetch_course_attributes
}


@chatbot_blueprint.route('/chat', methods=['POST'])
def chatbot():
    try:
        data = request.json
        if data is None:
            return jsonify({"message": "Invalid or missing JSON in request body"}), 400

        
        msg = data.get('message')
        year = data.get('year')
        program = data.get('program')
        
        
        print(msg, year, program)
        # if not msg or not year or not program:
        #     return jsonify({"message": "Missing required fields: message, year, or program"}), 400

        messages = [
            {
                "role": "system",
                "content": f"""
                    You are an academic advisor assistant. You help students by answering questions about their degree plan.

                    Here is the student's degree plan information:

                    Year: {year}
                    Program: {program}

                    {data.get('plan_information', {})}

                    Answer questions based only on this plan information.
                    Format your answers using newlines and bullet points where appropriate.
                    Use Markdown-style formatting if needed.

                    When you need course-specific information like prerequisites, detailed course info,
                    or attributes, use the available tools to fetch this data.
                """
            },
            {"role": "user", "content": msg},
        ]

        max_iterations = 5  # Prevent infinite tool-call loops

        for iteration in range(max_iterations):
            print(f"\n=== NON-STREAM CALL ITER {iteration+1} ===")

            try:
                completion = chat_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    reasoning_effort="low",
                    tool_choice="auto"
                )
                
            except Exception as e:
                print(f"ERROR creating chat completion: {e}")
                return jsonify({"message": f"Upstream chat error: {str(e)}"}), 502

            if not completion.choices:
                return jsonify({"message": "No completion choices returned."}), 502

            choice = completion.choices[0]
            assistant_msg = choice.message
            
            print("assistant msg", assistant_msg)

            # If the model wants to call tools, execute them synchronously, then loop
            tool_calls = getattr(assistant_msg, 'tool_calls', None) or []
            assistant_content = (assistant_msg.content or '').strip() if hasattr(assistant_msg, 'content') else ''

            # Append assistant step to the transcript BEFORE executing tools
            messages.append({
                "role": "assistant",
                "content": assistant_content if assistant_content else None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name if tc.function else None,
                            "arguments": tc.function.arguments if tc.function else "{}",
                        },
                    }
                    for tc in tool_calls
                ] if tool_calls else None,
            })

            if tool_calls:
                print(f"Executing {len(tool_calls)} tool call(s)...")
                for tc in tool_calls:
                    fn_name = tc.function.name if tc.function else None
                    raw_args = tc.function.arguments if tc.function else "{}"

                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError as e:
                        print(f"Tool args JSON error: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": "Error: Invalid function arguments",
                        })
                        continue

                    if fn_name not in available_functions:
                        print(f"Unknown tool: {fn_name}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: Unknown function {fn_name}",
                        })
                        continue

                    try:
                        result = available_functions[fn_name](**args)
                    except Exception as e:
                        print(f"Tool '{fn_name}' raised: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: {str(e)}",
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })

                # Continue loop: model will now see tool outputs and (ideally) produce final text
                continue

            # No tool calls -> we have our final answer
            if assistant_content:
                return jsonify({"message": assistant_content}), 200

            # Safety: if we get here with no content and no tools, bail
            print("Assistant returned no content and no tools.")
            return jsonify({"message": "No content returned by the model."}), 502

        # If max iterations exhausted
        return jsonify({
            "message": "Reached max tool-call iterations without a final answer. Try rephrasing your request."
        }), 502

    except Exception as e:
        print("Exception in /chat:", e)
        return jsonify({"message": "Error generating response"}), 500



    