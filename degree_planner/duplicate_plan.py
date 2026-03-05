from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 
import uuid
    
duplicate_plan_blueprint = Blueprint('duplicate_plan', __name__, url_prefix="/api")

def remove_ids(obj):
    if isinstance(obj, dict):
        obj.pop('_id', None)
        for value in obj.values():
            remove_ids(value)
    elif isinstance(obj, list):
        for item in obj:
            remove_ids(item)
            
@duplicate_plan_blueprint.route('/duplicate_plan', methods=['POST'])
def duplicate_plan():
    try:
        data = request.json 
        plan_id = data['plan_id']
        
        db = get_db()
        
        plans = db.get_collection('degree_plans')
        
        if plans is None:
            return jsonify({"message": "No plans found"}), 404

        plan = plans.find_one({'plan_id': plan_id})
        if not plan:
            return jsonify({"message": "Plan not found"}), 404
        
        remove_ids(plan)
        
        print(plan)
        # generate new UUIDs
        plan['plan_id'] = str(uuid.uuid4())
        plan['name'] = plan['name'] + ' (Copy)'
        
        for variation in plan.get('variations', []):
            variation['variation_id'] = str(uuid.uuid4())
        
        db.insert_document('degree_plans', plan)

        return jsonify({"message": "Plan duplicated successfully"}), 200
    except Exception as e:
        print(e)
    return jsonify({"message": "Error duplicating plan"}), 500