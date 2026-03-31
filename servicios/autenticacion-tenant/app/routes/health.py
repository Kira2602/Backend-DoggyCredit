from flask import Blueprint, jsonify
import os

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": os.getenv("SERVICE_NAME", "service")
    }), 200