from flask import Blueprint, jsonify
from app.models.rol import Rol
from app.services.serializers import serializar_rol

roles_bp = Blueprint("roles", __name__)

@roles_bp.route("/roles", methods=["GET"])
def listar_roles():
    roles = Rol.query.order_by(Rol.nombre.asc()).all()
    return jsonify([serializar_rol(rol) for rol in roles]), 200