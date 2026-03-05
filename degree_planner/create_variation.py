


from flask import Blueprint, request, jsonify
import uuid
from database import get_db

create_variation_blueprint = Blueprint('create_variation', __name__, url_prefix="/api")

@create_variation_blueprint.route('/create_variation', methods=['POST'])
def add_variation():
    try:
        data = request.get_json()

        # Get data from frontend
        semesters = data.get('semesters')
        plan_details = data.get('plan_details')
        year = data.get('year')
        plan_id = data.get('plan_id')
        

        print(year)
        # Find the existing plan
        db = get_db()
        plan_query = {
            'plan_id':  plan_id,
        }
        
        plan = db.find_documents('degree_plans', plan_query, limit=1)

        if not plan:
            return jsonify({"message": "Plan not found"}), 404

        # Prepare new variation
        new_year = {
            'id': str(uuid.uuid4()),
            'year': year,
            'semesters': semesters,
        }

   
        update_data = {
            '$push': {'years': new_year}
        }
        
        result = db.get_collection('degree_plans').update_one(plan_query, update_data)

        if result.modified_count == 0:
            return jsonify({"message": "Failed to add variation"}), 400

    except Exception as e:
        print(e)
        return jsonify({"message": "There was an error saving the variation"}), 400
    return jsonify({"message": "Variation added successfully"}), 200