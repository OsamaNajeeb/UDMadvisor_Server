from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 

    
delete_plan_blueprint = Blueprint('delete_plan', __name__, url_prefix="/api")

@delete_plan_blueprint.route('/delete_plan', methods=['POST'])
def delete_plan():
    try:
        data = request.json
        plan_id = data['plan_id']
        db = get_db()
        
        print(plan_id)
        db.delete_document('degree_plans', {
            'plan_id': plan_id
        })

        return jsonify({"message": "Plan deleted successfully"}), 200
    except Exception as e:
        print(e)
    return jsonify({"message": "Plan deleted successfully"}), 500