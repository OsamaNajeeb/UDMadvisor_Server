from flask import Blueprint, jsonify, current_app
import requests

fetch_all_terms_blueprint = Blueprint('fetch_all_terms', __name__, url_prefix="/api")

@fetch_all_terms_blueprint.route('/fetch_all_terms', methods=['GET'])
def fetch_all_terms():
    try:
        API_URL = "https://reg-prod.ec.udmercy.edu/StudentRegistrationSsb/ssb/classSearch/getTerms" 
        
        # Forward the request to the terms API
        response = requests.get(API_URL, params={
            "searchTerm": "", 
            "offset": 1, 
            "max": 10, 
        })
                
        # Return the API response as JSON
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        current_app.logger.error("There was an error retrieving the terms")
        current_app.logger.error(e)
        return jsonify({"error": {"message": "There was an error retrieving the terms", "code": "INVALID_FETCH"}}), 500