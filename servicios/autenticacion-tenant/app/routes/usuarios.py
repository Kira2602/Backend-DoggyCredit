# app/routes/usuarios.py
from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.services.serializers import serializar_usuario
import jwt
import uuid

usuarios_bp = Blueprint("usuarios", __name__)

# ==================== OBTENER USUARIO DESDE JWT ====================
def obtener_usuario_actual():
    """Obtiene el usuario desde JWT (compatible con auth.py)"""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"message": "Token requerido"}), 401)

    token = auth_header.replace("Bearer ", "")

    try:
        secret_key = current_app.config.get('SECRET_KEY', 'doggycredit-secret-key-2024')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])

        usuario_id = uuid.UUID(payload['usuario_id'])
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return None, (jsonify({"message": "Usuario no encontrado"}), 404)

        return usuario, None

    except jwt.ExpiredSignatureError:
        return None, (jsonify({"message": "Token expirado"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"message": "Token inválido"}), 401)
    except Exception:
        return None, (jsonify({"message": "Error procesando el token"}), 401)


# ==================== VALIDAR ADMIN ====================
def es_admin_tenant(usuario):
    """Verifica si el usuario tiene permisos de administrador"""
    nombres_roles = [rel.rol.nombre for rel in usuario.roles]
    return "admin_tenant" in nombres_roles or "super_admin" in nombres_roles


# ==================== LISTAR USUARIOS ====================
@usuarios_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    usuarios = Usuario.query.filter_by(
        institucion_id=usuario_actual.institucion_id
    ).all()

    return jsonify([serializar_usuario(u) for u in usuarios]), 200


# ==================== OBTENER USUARIO ====================
@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["GET"])
def obtener_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    usuario = Usuario.query.filter_by(
        id=usuario_id,
        institucion_id=usuario_actual.institucion_id
    ).first()

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    return jsonify(serializar_usuario(usuario)), 200


# ==================== CREAR USUARIO ====================
@usuarios_bp.route("/usuarios", methods=["POST"])
def crear_usuario():
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos para crear usuarios"}), 403

    data = request.get_json()

    if not data:
        return jsonify({"message": "No se enviaron datos"}), 400

    nombre = data.get("nombre")
    apellido = data.get("apellido")
    correo = data.get("correo")
    password = data.get("password")
    rol_id_recibido = data.get("rol_id")

    if not nombre or not apellido or not correo or not password:
        return jsonify({"message": "Datos incompletos"}), 400

    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({"message": "El correo ya está registrado"}), 409

    # Crear usuario
    nuevo_usuario = Usuario(
        institucion_id=usuario_actual.institucion_id,
        nombre=nombre,
        apellido=apellido,
        correo=correo,
        password=generate_password_hash(password),
        estado=data.get("estado", "activo")
    )
    db.session.add(nuevo_usuario)
    db.session.flush()

    # Asignar rol
    if rol_id_recibido:
        try:
            rol_uuid = uuid.UUID(rol_id_recibido)
            rol = Rol.query.get(rol_uuid)
        except Exception:
            return jsonify({"message": "rol_id inválido"}), 400

        if not rol:
            return jsonify({"message": "Rol no válido"}), 400
    else:
        rol = Rol.query.filter_by(nombre='operador').first()
        if not rol:
            rol = Rol(nombre='operador')
            db.session.add(rol)
            db.session.flush()

    usuario_rol = UsuarioRol(
        usuario_id=nuevo_usuario.id,
        rol_id=rol.id
    )
    db.session.add(usuario_rol)

    db.session.commit()

    return jsonify(serializar_usuario(nuevo_usuario)), 201


# ==================== EDITAR USUARIO ====================
@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["PUT"])
def editar_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "Permiso denegado"}), 403

    usuario = Usuario.query.filter_by(
        id=usuario_id,
        institucion_id=usuario_actual.institucion_id
    ).first()

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    if usuario.id == usuario_actual.id:
        return jsonify({"message": "No puedes editarte a ti mismo"}), 400

    data = request.get_json()

    if not data:
        return jsonify({"message": "No se enviaron datos"}), 400

    usuario.nombre = data.get("nombre", usuario.nombre)
    usuario.apellido = data.get("apellido", usuario.apellido)
    usuario.correo = data.get("correo", usuario.correo)
    usuario.estado = data.get("estado", usuario.estado)

    db.session.commit()

    return jsonify(serializar_usuario(usuario)), 200


# ==================== ELIMINAR USUARIO ====================
@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["DELETE"])
def eliminar_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "Permiso denegado"}), 403

    usuario = Usuario.query.filter_by(
        id=usuario_id,
        institucion_id=usuario_actual.institucion_id
    ).first()

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    if usuario.id == usuario_actual.id:
        return jsonify({"message": "No puedes eliminarte a ti mismo"}), 400

    db.session.delete(usuario)
    db.session.commit()

    return jsonify({"message": "Usuario eliminado correctamente"}), 200


# ==================== ASIGNAR ROL ====================
@usuarios_bp.route("/usuarios/<uuid:usuario_id>/roles", methods=["POST"])
def asignar_rol(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error: return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos"}), 403

    usuario = Usuario.query.filter_by(
        id=usuario_id,
        institucion_id=usuario_actual.institucion_id
    ).first()

    if not usuario:
        return jsonify({"message": "Usuario no encontrado"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"message": "No se enviaron datos"}), 400

    rol_id = data.get("rol_id")

    if not rol_id:
        return jsonify({"message": "rol_id es requerido"}), 400

    try:
        rol_uuid = uuid.UUID(rol_id)
        rol = Rol.query.get(rol_uuid)
    except Exception:
        return jsonify({"message": "rol_id inválido"}), 400

    if not rol:
        return jsonify({"message": "Rol no encontrado"}), 404

    # Forzar un solo rol por usuario
    UsuarioRol.query.filter_by(usuario_id=usuario.id).delete()

    nuevo_rol = UsuarioRol(
        usuario_id=usuario.id,
        rol_id=rol.id
    )
    db.session.add(nuevo_rol)
    db.session.commit()

    return jsonify(serializar_usuario(usuario)), 200