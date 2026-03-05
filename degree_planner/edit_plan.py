from flask import Blueprint, request, jsonify
from database import get_db 

    
edit_plan_blueprint = Blueprint('edit_plan', __name__, url_prefix="/api")

@edit_plan_blueprint.route('/edit_plan', methods=['POST'])
def edit_plan():
    try:
        data = request.get_json()   
        plan_id = data["plan_id"]
        year_id = data["year_id"]

            
        db = get_db()
        
        variation_updated_data = {
            "semesters": data.get('semesters'),
        }
        
        plan_details = data.get("plan_details", {})

        db.update_document(
            collection_name="degree_plans",
            query={"plan_id": plan_id},
            update_data={
                "year": plan_details.get("year"),
                "program": plan_details.get("program"),
                "minor": plan_details.get("minor"),
                "name": plan_details.get("name")
            }
        )

        db.update_plan_variation(
            collection_name="degree_plans",
            plan_id=plan_id,
            year_id=year_id,
            update_data=variation_updated_data
        )
        

        return jsonify({"message": "Plan edited successfully"}), 200
    except Exception as e:
        print(e)
    return jsonify({"message": "Plan saved successfully"}), 200