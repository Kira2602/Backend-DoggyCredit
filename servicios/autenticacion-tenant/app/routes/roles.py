from flask import Blueprint, jsonify, request, current_app
import jwt
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.services.serializers import serializar_rol

roles_bp = Blueprint("roles", __name__)

def obtener_usuario_actual():
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"message": "Token requerido"}), 401)

    token = auth_header.replace("Bearer ", "")

    try:
        secret_key = current_app.config.get('SECRET_KEY', 'doggycredit-secret-key-2024')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])

        usuario = Usuario.query.get(payload['usuario_id'])

        if not usuario:
            return None, (jsonify({"message": "Usuario no encontrado"}), 404)

        return usuario, None

    except Exception:
        return None, (jsonify({"message": "Token inválido"}), 401)


@roles_bp.route("/roles", methods=["GET"])
def listar_roles():
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    roles = Rol.query.order_by(Rol.nombre.asc()).all()
    return jsonify([serializar_rol(rol) for rol in roles]), 200