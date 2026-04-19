# app/routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.institucion import Institucion
from app.models.usuario import Usuario
from app.models.suscripcion import Suscripcion
from app.models.usuario_rol import UsuarioRol
from app.models.rol import Rol
from app.models.plan import Plan
import uuid
from datetime import datetime, timedelta
import jwt

auth_bp = Blueprint('auth', __name__)


# ==================== FUNCIÓN PARA GENERAR TOKEN ====================
def generar_token(usuario_id, correo, institucion_id):
    """Genera un token JWT para el usuario"""
    try:
        payload = {
            'usuario_id': str(usuario_id),
            'correo': correo,
            'institucion_id': str(institucion_id),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        secret_key = current_app.config.get('SECRET_KEY', 'doggycredit-secret-key-2024')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        print(f"Error generando token: {e}")
        return None


# ==================== MANEJO DE CORS PARA OPTIONS ====================
@auth_bp.route('/registro', methods=['OPTIONS'])
@auth_bp.route('/login', methods=['OPTIONS'])
@auth_bp.route('/verificar-token', methods=['OPTIONS'])
def handle_options():
    """Manejar peticiones OPTIONS para CORS"""
    response = jsonify({'message': 'OK'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response, 200


# ==================== ENDPOINT DE REGISTRO ====================
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
        
        response = jsonify({
            'success': True,
            'message': 'Registro completado exitosamente',
            'data': {
                'institucion_id': str(nueva_institucion.id),
                'usuario_id': str(nuevo_usuario.id),
                'suscripcion_id': str(nueva_suscripcion.id)
            }
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 201
        
    except Exception as e:
        db.session.rollback()
        response = jsonify({'success': False, 'message': str(e)})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 500


# ==================== ENDPOINT DE LOGIN ====================
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        
        correo = data.get('correo')
        password = data.get('password')
        
        # 1. Buscar usuario por correo
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        # ========== LOGS PARA DEBUG ==========
        print(f"\n📧 Buscando: {correo}")
        print(f"👤 ¿Usuario existe? {usuario is not None}")
        
        if usuario:
            print(f"📝 Correo en BD: {usuario.correo}")
            print(f"🔑 Hash en BD: {usuario.password[:30]}...")  # Solo primeros 30 caracteres
            print(f"🔐 Contraseña ingresada: {password}")
            
            # Prueba manual de verificación
            from werkzeug.security import check_password_hash
            resultado = check_password_hash(usuario.password, password)
            print(f"✅ ¿Password correcta? {resultado}")
        # ====================================
        
        if not usuario:
            return jsonify({'success': False, 'message': 'Credenciales inválidas'}), 401
        
        if not check_password_hash(usuario.password, password):
            return jsonify({'success': False, 'message': 'Credenciales inválidas'}), 401
        
        if not data:
            response = jsonify({'success': False, 'message': 'No se recibieron datos'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 400
        
        correo = data.get('correo')
        password = data.get('password')
        
        # Validar datos requeridos
        if not correo or not password:
            response = jsonify({'success': False, 'message': 'Correo y contraseña son requeridos'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 400
        
        # 1. Buscar usuario por correo
        usuario = Usuario.query.filter_by(correo=correo).first()
        
        if not usuario:
            response = jsonify({'success': False, 'message': 'Credenciales inválidas'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        # 2. Verificar contraseña
        if not check_password_hash(usuario.password, password):
            response = jsonify({'success': False, 'message': 'Credenciales inválidas'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        # 3. Verificar estado del usuario
        if usuario.estado != 'activo':
            response = jsonify({'success': False, 'message': 'Usuario inactivo. Contacte al administrador'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        # 4. Obtener el rol del usuario (desde usuarios_roles -> roles)
        usuario_rol = UsuarioRol.query.filter_by(usuario_id=usuario.id).first()
        if not usuario_rol:
            response = jsonify({'success': False, 'message': 'Usuario sin rol asignado'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        rol = Rol.query.filter_by(id=usuario_rol.rol_id).first()
        nombre_rol = rol.nombre if rol else None
        
        if not nombre_rol:
            response = jsonify({'success': False, 'message': 'Rol no encontrado'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        # 5. Obtener información de la institución
        institucion = Institucion.query.filter_by(id=usuario.institucion_id).first()
        
        # 6. Obtener el plan de la institución (desde suscripciones -> planes)
        suscripcion = Suscripcion.query.filter_by(institucion_id=usuario.institucion_id, estado='activo').first()
        nombre_plan = None
        if suscripcion:
            plan = Plan.query.filter_by(id=suscripcion.plan_id).first()
            nombre_plan = plan.nombre if plan else None
        
        # 7. Generar token JWT
        token = generar_token(usuario.id, usuario.correo, usuario.institucion_id)
        
        # 8. Determinar la ruta de redirección según el rol
        ruta_redireccion = '/dashboard'  # por defecto
        if nombre_rol == 'super_admin':
            ruta_redireccion = '/admin'
        elif nombre_rol == 'admin_tenant':
            ruta_redireccion = '/banco'
        elif nombre_rol == 'operador':
            ruta_redireccion = '/operador'
        
        # 9. Preparar respuesta completa
        response = jsonify({
            'success': True,
            'message': 'Login exitoso',
            'data': {
                'usuario': {
                    'id': str(usuario.id),
                    'nombre': usuario.nombre,
                    'apellido': usuario.apellido,
                    'correo': usuario.correo,
                    'estado': usuario.estado
                },
                'rol': nombre_rol,
                'institucion': {
                    'id': str(institucion.id) if institucion else None,
                    'tenant_id': str(institucion.tenant_id) if institucion else None,
                    'nombre': institucion.nombre if institucion else None,
                    'tipo_institucion': institucion.tipo_institucion if institucion else None,
                    'email': institucion.email if institucion else None
                },
                'plan': nombre_plan,
                'redirect_to': ruta_redireccion,
                'token': token
            }
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    except Exception as e:
        print(f"Error en login: {str(e)}")
        response = jsonify({'success': False, 'message': f'Error en el servidor: {str(e)}'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 500


# ==================== ENDPOINT PARA VERIFICAR TOKEN ====================
@auth_bp.route('/verificar-token', methods=['POST'])
def verificar_token():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            response = jsonify({'success': False, 'message': 'Token no proporcionado'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        secret_key = current_app.config.get('SECRET_KEY', 'doggycredit-secret-key-2024')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verificar que el usuario aún existe y está activo
        usuario = Usuario.query.filter_by(id=payload['usuario_id']).first()
        if not usuario or usuario.estado != 'activo':
            response = jsonify({'success': False, 'message': 'Usuario no válido'})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
            return response, 401
        
        response = jsonify({
            'success': True,
            'message': 'Token válido',
            'data': payload
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 200
        
    except jwt.ExpiredSignatureError:
        response = jsonify({'success': False, 'message': 'Token expirado'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 401
    except jwt.InvalidTokenError:
        response = jsonify({'success': False, 'message': 'Token inválido'})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 401
    except Exception as e:
        response = jsonify({'success': False, 'message': str(e)})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:4200')
        return response, 500