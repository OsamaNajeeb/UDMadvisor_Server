import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv
from course_viewer.fetch_course_with_subject_and_number import fetch_courses_with_subject_and_number_blueprint
from course_viewer.fetch_all_terms import fetch_all_terms_blueprint
from course_viewer.fetch_courses import fetch_courses_blueprint
from cron.fetch_courses_daily import fetch_courses_daily_cron_blueprint
from cron.fetch_past_terms_courses_weekly_cronjob import fetch_courses_weekly_cron_blueprint
from degree_planner.create_plan import create_plan_blueprint
from degree_planner.get_all_plans import get_all_plans_blueprint
from degree_planner.get_plan import get_plan_blueprint
from degree_planner.delete_plan import delete_plan_blueprint
from degree_planner.create_variation import create_variation_blueprint
from degree_planner.edit_plan import edit_plan_blueprint
from degree_planner.analyze_prerequisites import analyze_prerequisites_blueprint
from degree_planner.export_plan_as_pdf import export_plan_blueprint
from degree_planner.create_plan_link import create_plan_link_blueprint
from degree_planner.chatbot import chatbot_blueprint
from degree_planner.export_customized_plan_as_pdf import export_customized_plan_to_pdf_blueprint
from degree_planner.save_plan_link import save_plan_link_blueprint
from degree_planner.duplicate_plan import duplicate_plan_blueprint
from utils import fetch_cookies
from logging.config import dictConfig

from database import get_db 

# Load the variables in the .env file
load_dotenv()

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

CORS(app=app)

app.register_blueprint(fetch_courses_with_subject_and_number_blueprint)
app.register_blueprint(fetch_all_terms_blueprint)
app.register_blueprint(fetch_courses_blueprint)
app.register_blueprint(create_plan_blueprint)
app.register_blueprint(get_all_plans_blueprint)
app.register_blueprint(delete_plan_blueprint)
app.register_blueprint(edit_plan_blueprint)
app.register_blueprint(analyze_prerequisites_blueprint)
app.register_blueprint(chatbot_blueprint)
app.register_blueprint(create_variation_blueprint)
app.register_blueprint(export_plan_blueprint)
app.register_blueprint(create_plan_link_blueprint)
app.register_blueprint(duplicate_plan_blueprint)
app.register_blueprint(save_plan_link_blueprint)
app.register_blueprint(export_customized_plan_to_pdf_blueprint)

# Cron Jobs
app.register_blueprint(fetch_courses_daily_cron_blueprint)
app.register_blueprint(fetch_courses_weekly_cron_blueprint)
app.register_blueprint(get_plan_blueprint)

@app.route('/health', methods=['GET'])
def health():
    db_status = "connected" if get_db().is_connected() else "disconnected"
    return jsonify({
        "status": "The app is running!",
        "database": db_status
    })

MAILGUN_API_URL = os.getenv("MAILGUN_API_URL")
api_key = os.getenv("MAILGUN_API_KEY")

@app.route("/send_feedback", methods=['POST'])
def send_feedback():
    try:
        data = request.get_json()
        if not data:
            return "No JSON data provided", 400
        
        feedback_message = data.get("feedback_message")
        if not feedback_message:
            return "feedback_message is required", 400
        
        print(feedback_message)
        
        # Check if environment variables are set
        if not MAILGUN_API_URL or not api_key:
            return "Mailgun configuration not set", 500
        
        resp = requests.post(MAILGUN_API_URL, auth=("api", api_key),
                             data={"from": "oladipoeyiara@gmail.com",
                                   "to": "oladipoeyiara@gmail.com", "subject": "Course Viewer Feedback", "text": feedback_message})
        
        print(resp)
        return "Feedback sent successfully", 200
    except Exception as ex: 
        print(ex)
        return "Error", 500

@app.route("/db/status", methods=['GET'])
def db_status():
    """Check database connection status"""
    db = get_db()
    is_connected = db.is_connected()
    return jsonify({
        "connected": is_connected,
        "message": "Database connected" if is_connected else "Database disconnected"
    })

@app.route("/db/collections", methods=['GET'])
def list_collections():
    """List all collections in the database"""
    try:
        db = get_db()
        if not db.is_connected() or db.db is None:
            return jsonify({"error": "Database not connected"}), 500
        
        collections = db.db.list_collection_names()
        return jsonify({
            "collections": collections,
            "count": len(collections)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)