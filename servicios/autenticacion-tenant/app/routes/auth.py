from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.institucion import Institucion
from app.models.usuario import Usuario
from app.models.suscripcion import Suscripcion
from app.models.usuario_rol import UsuarioRol
from app.models.rol import Rol
from app.models.plan import Plan
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/registro', methods=['POST'])
def registrar():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
        
        datos_institucion = data.get('institucion')
        datos_usuario = data.get('usuario')
        plan_id_str = data.get('plan_id')
        
        # Validar datos requeridos
        if not datos_institucion or not datos_usuario or not plan_id_str:
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
        
        # Convertir plan_id a UUID
        try:
            plan_id = uuid.UUID(plan_id_str)
        except ValueError:
            return jsonify({'success': False, 'message': 'plan_id no es válido'}), 400
        
        # Verificar que el plan existe
        plan = Plan.query.filter_by(id=plan_id).first()
        if not plan:
            return jsonify({'success': False, 'message': 'El plan no existe'}), 400
        
        # Verificar emails duplicados
        if Institucion.query.filter_by(email=datos_institucion.get('email')).first():
            return jsonify({'success': False, 'message': 'Email de institución ya registrado'}), 409
        
        if Usuario.query.filter_by(correo=datos_usuario.get('correo')).first():
            return jsonify({'success': False, 'message': 'Correo de usuario ya registrado'}), 409
        
        # Crear institución
        nueva_institucion = Institucion(
            nombre=datos_institucion.get('nombre'),
            tipo_institucion=datos_institucion.get('tipo_institucion'),
            telefono=datos_institucion.get('telefono'),
            email=datos_institucion.get('email'),
            estado='activo'
        )
        db.session.add(nueva_institucion)
        db.session.flush()
        
        # Crear usuario
        nuevo_usuario = Usuario(
            institucion_id=nueva_institucion.id,
            nombre=datos_usuario.get('nombre'),
            apellido=datos_usuario.get('apellido'),
            correo=datos_usuario.get('correo'),
            password=generate_password_hash(datos_usuario.get('password')),
            estado='activo'
        )
        db.session.add(nuevo_usuario)
        db.session.flush()
        
        # Asignar rol admin_tenant
        rol_admin = Rol.query.filter_by(nombre='admin_tenant').first()
        if not rol_admin:
            rol_admin = Rol(nombre='admin_tenant')
            db.session.add(rol_admin)
            db.session.flush()
        
        usuario_rol = UsuarioRol(usuario_id=nuevo_usuario.id, rol_id=rol_admin.id)
        db.session.add(usuario_rol)
        
        # Crear suscripción
        nueva_suscripcion = Suscripcion(
            institucion_id=nueva_institucion.id,
            plan_id=plan_id,
            estado='activo'
        )
        db.session.add(nueva_suscripcion)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registro completado exitosamente',
            'data': {
                'institucion_id': str(nueva_institucion.id),
                'usuario_id': str(nuevo_usuario.id),
                'suscripcion_id': str(nueva_suscripcion.id)
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500