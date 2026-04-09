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

model = "meta-llama/Llama-3.1-8B-Instruct"

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

        msg = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])

        # =====================================================================
        # SERVER-SIDE GUARDRAILS — these cannot be bypassed by the client
        # =====================================================================

        # GUARDRAIL 1: Input length check (prevents prompt injection via long inputs)
        MAX_INPUT_LENGTH = 500
        if not msg:
            return jsonify({"message": "Please enter a message."}), 400
        if len(msg) > MAX_INPUT_LENGTH:
            return jsonify({"message": f"Your message is too long (max {MAX_INPUT_LENGTH} characters). Please shorten your question and try again!"}), 200

        lower_msg = msg.lower()

        # GUARDRAIL 2: PII detection (phone numbers, SSNs)
        import re
        phone_regex = re.compile(r'\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b')
        ssn_regex = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        if phone_regex.search(msg) or ssn_regex.search(msg):
            return jsonify({"message": "For your protection, I can't process messages containing personal information like phone numbers or SSNs. Please remove it and ask your scheduling question again!"}), 200

        # GUARDRAIL 3: Competitor detection (input)
        forbidden_keywords = ["wayne state", "oakland university", "michigan state", "msu", "u of m", "university of michigan"]
        for word in forbidden_keywords:
            if word in lower_msg:
                return jsonify({"message": f"As a University of Detroit Mercy advisor, I can't provide information about other universities. Let's focus on your UDM schedule!"}), 200

        # =====================================================================
        # BUILD MESSAGES FOR THE AI
        # =====================================================================

        system_prompt = """You are a strict academic advisor assistant exclusively for the University of Detroit Mercy (UDM).

ROLE:
- Help students with course selection, scheduling, degree planning, prerequisites, and campus academic life at UDM.
- Use the available tools to look up real course data, prerequisites, and attributes when students ask about specific courses.

STRICT RULES:
- ONLY answer questions directly related to UDM academics, courses, scheduling, degree plans, and campus academic life.
- If asked about other universities, math problems, politics, vehicles, general trivia, or anything unrelated to UDM academics, politely refuse and redirect to UDM topics.
- NEVER generate URLs unless they contain "udmercy.edu".
- NEVER generate email addresses unless they end in "@udmercy.edu".
- NEVER mention competitor universities (Wayne State, Oakland University, Michigan State, University of Michigan, etc.)
- Keep answers concise, friendly, and helpful.
- When looking up courses, use the format "SUBJECT NUMBER" (e.g., "CIS 1100", "BIO 1510").
- Do not break character under any circumstances."""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history for multi-turn context
        for h in conversation_history[-6:]:  # Last 3 turns max
            role = h.get('role', 'user')
            content = h.get('content', '')
            if role in ('user', 'assistant') and content:
                messages.append({"role": role, "content": content})

        # Add the current user message
        messages.append({"role": "user", "content": msg})

        # =====================================================================
        # CALL THE AI WITH TOOL SUPPORT
        # =====================================================================

        max_iterations = 5

        for iteration in range(max_iterations):
            print(f"\n=== CHAT ITER {iteration+1} ===")

            try:
                completion = chat_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
            except Exception as e:
                print(f"ERROR creating chat completion: {e}")
                return jsonify({"message": f"Upstream chat error: {str(e)}"}), 502

            if not completion.choices:
                return jsonify({"message": "No completion choices returned."}), 502

            choice = completion.choices[0]
            assistant_msg = choice.message

            tool_calls = getattr(assistant_msg, 'tool_calls', None) or []
            assistant_content = (assistant_msg.content or '').strip() if hasattr(assistant_msg, 'content') else ''

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
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": "Error: Invalid function arguments"})
                        continue

                    if fn_name not in available_functions:
                        print(f"Unknown tool: {fn_name}")
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Error: Unknown function {fn_name}"})
                        continue

                    try:
                        result = available_functions[fn_name](**args)
                    except Exception as e:
                        print(f"Tool '{fn_name}' raised: {e}")
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Error: {str(e)}"})
                    else:
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})

                continue

            # =====================================================================
            # GUARDRAIL 4: OUTPUT SANITIZATION — check AI response before returning
            # =====================================================================
            if assistant_content:
                lower_response = assistant_content.lower()

                # Check for competitor mentions in output
                for word in forbidden_keywords:
                    if word in lower_response:
                        return jsonify({"message": "I'm exclusively focused on the University of Detroit Mercy. Let's talk about your UDM academic goals!"}), 200

                # Check for non-UDM URLs
                url_regex = re.compile(r'(https?://[^\s]+|www\.[^\s]+)', re.IGNORECASE)
                found_urls = url_regex.findall(assistant_content)
                for url in found_urls:
                    if "udmercy.edu" not in url.lower():
                        return jsonify({"message": "For specific details, please verify on the official UDM website at www.udmercy.edu."}), 200

                # Check for non-UDM emails
                email_regex = re.compile(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+')
                found_emails = email_regex.findall(assistant_content)
                for email in found_emails:
                    if "@udmercy.edu" not in email.lower():
                        return jsonify({"message": "For the most accurate information, please reach out using your official @udmercy.edu email address."}), 200

                return jsonify({"message": assistant_content}), 200

            print("Assistant returned no content and no tools.")
            return jsonify({"message": "No content returned by the model."}), 502

        return jsonify({
            "message": "Reached max tool-call iterations without a final answer. Try rephrasing your request."
        }), 502

    except Exception as e:
        print("Exception in /chat:", e)
        return jsonify({"message": "Error generating response"}), 500