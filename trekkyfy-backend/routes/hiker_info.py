import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import HikerRequest
from extensions import db

hiker_info_bp = Blueprint("Hiker Information For Pricing", __name__)

@hiker_info_bp.route("/avl-price-req", methods=["POST"])
def price_avl_req():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    required_fields = ["hiker_id", "guide_id","hiker_username", "trek_place", "hiking_members", "trek_date", "trek_time"]
    if any(field not in data for field in required_fields):
        return jsonify({"Error": "All fields are required."}), 400

    try:
        trek_date = datetime.strptime(data["trek_date"], "%Y-%m-%d").date()

        trek_time_str = data["trek_time"]
        trek_time = None

        try:
            trek_time = datetime.strptime(trek_time_str, "%H:%M").time()
        except ValueError:
            try:
                trek_time = datetime.strptime(trek_time_str, "%H:%M:%S").time()
            except ValueError:
                return jsonify({"Error": "Invalid trek_time format. Use HH:MM or HH:MM:SS"}), 400

        hiker_req = HikerRequest(
            hiker_id=data["hiker_id"],
            guide_id=data["guide_id"],
            hiker_username=data["hiker_username"],
            trek_place=data["trek_place"],
            hiking_members=data["hiking_members"],
            trek_date=trek_date,
            trek_time=trek_time,
            created_at=datetime.utcnow(),
        )

        db.session.add(hiker_req)
        db.session.commit()
        return jsonify({"Success": "Request has been stored in the database!"}), 200

    except Exception as e:
        print("🚨 ERROR OCCURRED:", str(e))
        traceback.print_exc()
        return jsonify({"Error": str(e)}), 500
