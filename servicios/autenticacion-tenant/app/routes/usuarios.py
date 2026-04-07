from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol
from app.services.serializers import serializar_usuario

usuarios_bp = Blueprint("usuarios", __name__)

def obtener_usuario_actual():
    usuario_id = request.headers.get("X-Usuario-Id")
    if not usuario_id:
        return None, (jsonify({"message": "Falta el header X-Usuario-Id"}), 400)

    usuario = Usuario.query.filter_by(id=usuario_id).first()
    if not usuario:
        return None, (jsonify({"message": "Usuario actual no encontrado"}), 404)

    return usuario, None


def es_admin_tenant(usuario):
    nombres_roles = [rel.rol.nombre for rel in usuario.roles]
    return "admin_tenant" in nombres_roles or "super_admin" in nombres_roles


@usuarios_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    usuarios = Usuario.query.filter_by(institucion_id=usuario_actual.institucion_id).all()
    return jsonify([serializar_usuario(usuario) for usuario in usuarios]), 200


@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["GET"])
def obtener_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    usuario = Usuario.query.filter_by(id=usuario_id, institucion_id=usuario_actual.institucion_id).first()
    if not usuario:
        return jsonify({"message": "Usuario no encontrado en tu institución"}), 404

    return jsonify(serializar_usuario(usuario)), 200


@usuarios_bp.route("/usuarios", methods=["POST"])
def crear_usuario():
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos para crear usuarios"}), 403

    data = request.get_json()

    nombre = data.get("nombre")
    apellido = data.get("apellido")
    correo = data.get("correo")
    password = data.get("password")
    estado = data.get("estado", "activo")

    if not nombre or not apellido or not correo or not password:
        return jsonify({"message": "nombre, apellido, correo y password son obligatorios"}), 400

    existe = Usuario.query.filter_by(correo=correo).first()
    if existe:
        return jsonify({"message": "Ya existe un usuario con ese correo"}), 409

    nuevo_usuario = Usuario(
        institucion_id=usuario_actual.institucion_id,
        nombre=nombre,
        apellido=apellido,
        correo=correo,
        password=generate_password_hash(password),
        estado=estado
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify(serializar_usuario(nuevo_usuario)), 201


@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["PUT"])
def editar_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos para editar usuarios"}), 403

    usuario = Usuario.query.filter_by(id=usuario_id, institucion_id=usuario_actual.institucion_id).first()
    if not usuario:
        return jsonify({"message": "Usuario no encontrado en tu institución"}), 404

    data = request.get_json()

    usuario.nombre = data.get("nombre", usuario.nombre)
    usuario.apellido = data.get("apellido", usuario.apellido)
    usuario.correo = data.get("correo", usuario.correo)
    usuario.estado = data.get("estado", usuario.estado)

    db.session.commit()

    return jsonify(serializar_usuario(usuario)), 200


@usuarios_bp.route("/usuarios/<uuid:usuario_id>", methods=["DELETE"])
def eliminar_usuario(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos para eliminar usuarios"}), 403

    usuario = Usuario.query.filter_by(id=usuario_id, institucion_id=usuario_actual.institucion_id).first()
    if not usuario:
        return jsonify({"message": "Usuario no encontrado en tu institución"}), 404

    db.session.delete(usuario)
    db.session.commit()

    return jsonify({"message": "Usuario eliminado correctamente"}), 200


@usuarios_bp.route("/usuarios/<uuid:usuario_id>/roles", methods=["POST"])
def asignar_rol(usuario_id):
    usuario_actual, error = obtener_usuario_actual()
    if error:
        return error

    if not es_admin_tenant(usuario_actual):
        return jsonify({"message": "No tienes permisos para asignar roles"}), 403

    usuario = Usuario.query.filter_by(id=usuario_id, institucion_id=usuario_actual.institucion_id).first()
    if not usuario:
        return jsonify({"message": "Usuario no encontrado en tu institución"}), 404

    data = request.get_json()
    rol_id = data.get("rol_id")

    if not rol_id:
        return jsonify({"message": "rol_id es obligatorio"}), 400

    rol = Rol.query.filter_by(id=rol_id).first()
    if not rol:
        return jsonify({"message": "Rol no encontrado"}), 404

    existe = UsuarioRol.query.filter_by(usuario_id=usuario.id, rol_id=rol.id).first()
    if existe:
        return jsonify({"message": "El usuario ya tiene ese rol"}), 409

    usuario_rol = UsuarioRol(
        usuario_id=usuario.id,
        rol_id=rol.id
    )

    db.session.add(usuario_rol)
    db.session.commit()

    usuario_actualizado = Usuario.query.filter_by(id=usuario.id).first()
    return jsonify(serializar_usuario(usuario_actualizado)), 200