from flask import Blueprint, request, jsonify
import requests
from pydantic import BaseModel, ValidationError
from  utils.format_course_details import format_course
from database import get_db 

    
get_plan_blueprint = Blueprint('get_plan', __name__, url_prefix="/api")

@get_plan_blueprint.route('/get_plan', methods=['GET'])
def get_plan():
    try:
        plan_id = request.args.get('plan_id', None)
        year_id = request.args.get('year_id', None)
 
        if not plan_id:
            return jsonify({"message": "plan_id is required"}), 400
        
        if not year_id:
            return jsonify({"message": "year_id is required"}), 400
        
        db = get_db()
        
        plans = db.get_collection('degree_plans')
        
        if plans is None:
            return jsonify({"message": "No plans found"}), 404

        plan = plans.find_one({'plan_id': plan_id})
        
        year = next((var for var in plan.get('years', []) if var['id'] == year_id), None)
        
        if year:
            return jsonify({"plan": year, "program": plan["program"], "plan_id": plan["plan_id"], "minor": plan.get("minor", ""), "name": plan.get("name", "")}), 200
        else:
            return jsonify({"message": "Plan year not found"}), 404

    except Exception as e:
        print(e)
        return jsonify({"message": "Error getting plan"}), 500



@get_plan_blueprint.route('/get_plan_for_new_year', methods=['GET'])
def get_plan_for_new_year():
    try:
        plan_id = request.args.get('plan_id', None)
        new_year = request.args.get('new_year', None)
 
        if not plan_id:
            return jsonify({"message": "plan_id is required"}), 400
         
      
        db = get_db()
        
        plans = db.get_collection('degree_plans')
        
        if plans is None:
            return jsonify({"message": "No plans found"}), 404

        plan = plans.find_one({'plan_id': plan_id})
        
        # Adding a new year just uses the first year as a base, so this gets the first year added
        year = next((var for var in plan.get('years', [])), None)            
        
        year['year'] = new_year
        if year:
            return jsonify({"plan": year, "program": plan["program"], "plan_id": plan["plan_id"], "minor": plan.get("minor", ""), "name": plan.get("name", "")}), 200
        else:
            return jsonify({"message": "Plan year not found"}), 404

    except Exception as e:
        print(e)
        return jsonify({"message": "Error getting plan"}), 500


@get_plan_blueprint.route('/get_customized_plan', methods=['GET'])
def get_customized_plan():
    try:
        plan_id = request.args.get('plan_id', None)
 
        if not plan_id:
            return jsonify({"message": "plan_id is required"}), 400

        db = get_db()
        
        plans = db.get_collection('shared_plans')
        
        if plans is None:
            return jsonify({"message": "No plans found"}), 404

        plan = plans.find_one({'plan_id': plan_id})
        
        del plan['_id']  # Remove MongoDB ObjectId if present
        return jsonify({"plan": plan}), 200

    except Exception as e:
        print(e)
        return jsonify({"message": "Error getting plan"}), 500



@get_plan_blueprint.route('/get_plan_from_plan_information', methods=['GET'])
def get_plan_from_plan_information():
    try:
        year = request.args.get('year')
        program = request.args.get('program')

        db = get_db()
        plans = db.get_collection('degree_plans')
        if plans is None:
            return jsonify({"message": "No plans found"}), 404

        plan = plans.find_one({
            'year': year,
            'program': program,
        })

        if not plan:
            return jsonify({"message": "Plan not found"}), 404

        # Convert ObjectId to string
        if '_id' in plan:
            plan['_id'] = str(plan['_id'])

        return jsonify({"plan": plan}), 200
    except Exception as e:
        print(e)
    return jsonify({"message": "Error getting plan"}), 500