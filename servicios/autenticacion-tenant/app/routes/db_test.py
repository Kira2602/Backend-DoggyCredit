from flask import Blueprint, jsonify
from sqlalchemy import text
from app.extensions import db

db_test_bp = Blueprint("db_test", __name__)

@db_test_bp.route("/db-test", methods=["GET"])
def db_test():
    try:
        result = db.session.execute(text("SELECT 1"))
        value = result.scalar()
        return jsonify({
            "status": "ok",
            "database": "connected",
            "result": value
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500