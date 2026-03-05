from flask import Blueprint, request, jsonify
from database import get_db 
import uuid

    
create_plan_blueprint = Blueprint('create_plan', __name__, url_prefix="/api")

@create_plan_blueprint.route('/create_plan', methods=['POST'])
def add_plan():
    try:
        data = request.get_json()
        semesters = data.get('semesters')
        plan_details = data.get('plan_details') 

        formatted_plan = {
            'plan_id': str(uuid.uuid4()),
            "name":  plan_details.get('name', ""), 
            'program': plan_details.get('program', ""),
            'minor': plan_details.get('minor', ""),
            'years': [{
                'id':  str(uuid.uuid4()),
                'year': plan_details.get('year', ""),
                'semesters': semesters,
            }]
        }

        # save the plan to the database
        db = get_db()
                
        db.insert_document('degree_plans', formatted_plan)
    except Exception as e:
        print(e)
        return jsonify({"message": "There was an error saving the plan"}), 400
    return jsonify({"message": "Plan saved successfully"}), 200