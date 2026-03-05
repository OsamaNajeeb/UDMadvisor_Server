from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 
import uuid

create_plan_link_blueprint = Blueprint('create_plan_link', __name__, url_prefix="/api")

@create_plan_link_blueprint.route('/create_plan_link', methods=['POST'])
def create_plan_link():
    try:
        data = request.get_json()

        plan = data.get('plan')
       
        plan['plan_id'] = str(uuid.uuid4())
        plan['public'] = True 
        
        print(plan)

        # save the plan to the database
        db = get_db()
                
        db.insert_document('shared_plans', plan)
    except Exception as e:
        print(e)
        return jsonify({"message": "There was an error saving the plan"}), 400
    return jsonify({"message": "Plan saved successfully", 'plan_id': plan['plan_id']}), 200