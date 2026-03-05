from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 
import uuid

save_plan_link_blueprint = Blueprint('save_plan_link', __name__, url_prefix="/api")

@save_plan_link_blueprint.route('/save_plan_link', methods=['POST'])
def save_plan_link():
    try:
        data = request.get_json()

        plan = data.get('plan')
        plan_id = data.get("id")

        # save the plan to the database
        db = get_db()
                        
        db.update_document(collection_name="shared_plans", query={"plan_id": plan_id}, update_data=plan)
        return jsonify({"message": "Plan saved successfully"}), 200
    except Exception as e:
        print(e)
        return jsonify({"message": "There was an error saving the plan"}), 400