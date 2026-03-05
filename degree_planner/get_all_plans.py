from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 

    
get_all_plans_blueprint = Blueprint('get_all_plans', __name__, url_prefix="/api")

@get_all_plans_blueprint.route('/get_all_plans', methods=['GET'])
def get_all_plans():
    try:
        db = get_db()
        plans = db.get_collection('degree_plans')
        if plans is None:
            return jsonify({"message": "No plans found"}), 404
        
        plans = plans.find({})  
        plans = list(plans)

        # Convert ObjectId to string
        for plan in plans:
            if '_id' in plan:
                plan['_id'] = str(plan['_id'])

        return jsonify({"plans": plans}), 200
    except Exception as e:
        print(e)
    return jsonify({"message": "Error getting all plans"}), 500