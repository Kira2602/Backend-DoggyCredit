# app/services/registro_service.py
from app.extensions import db
from app.models.institucion import Institucion
from app.models.usuario import Usuario
from app.models.suscripcion import Suscripcion
from app.models.usuario_rol import UsuarioRol
from app.models.rol import Rol
from app.models.plan import Plan
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
import uuid

class RegistroService:
    """
    Servicio que maneja el registro completo de una nueva institución y su usuario administrador
    """
    
    @staticmethod
    def registrar_institucion_y_usuario(data):
        """
        Registra una nueva institución, su usuario admin y la suscripción inicial
        
        Args:
            data (dict): Diccionario con los datos del registro
            
        Returns:
            tuple: (exito: bool, mensaje: str, datos: dict)
        """
        
        try:
            # 1. Extraer datos del JSON
            datos_institucion = data.get('institucion')
            datos_usuario = data.get('usuario')
            plan_id = data.get('plan_id')
            
            # Validar datos requeridos
            if not datos_institucion or not datos_usuario or not plan_id:
                return False, "Faltan datos requeridos: institucion, usuario o plan_id", None
            
            # Convertir plan_id a UUID
            try:
                plan_uuid = uuid.UUID(plan_id)
            except ValueError:
                return False, "El plan_id no es un UUID válido", None
            
            # 2. Verificar que el plan existe
            plan = Plan.query.filter_by(id=plan_uuid).first()
            if not plan:
                return False, f"El plan con id {plan_id} no existe", None
            
            # 3. Verificar que el email de la institución no esté registrado
            institucion_existente = Institucion.query.filter_by(email=datos_institucion.get('email')).first()
            if institucion_existente:
                return False, "Ya existe una institución registrada con ese email", None
            
            # 4. Verificar que el correo del usuario no esté registrado
            usuario_existente = Usuario.query.filter_by(correo=datos_usuario.get('correo')).first()
            if usuario_existente:
                return False, "Ya existe un usuario registrado con ese correo electrónico", None
            
            # 5. Crear la institución (con tenant_id automático)
            nueva_institucion = Institucion(
                nombre=datos_institucion.get('nombre'),
                tipo_institucion=datos_institucion.get('tipo_institucion'),
                telefono=datos_institucion.get('telefono'),
                email=datos_institucion.get('email'),
                estado='activo'  # tenant_id se genera automáticamente
            )
            db.session.add(nueva_institucion)
            db.session.flush()  # Para obtener el ID sin commitear aún
            
            # 6. Crear el usuario administrador
            nuevo_usuario = Usuario(
                institucion_id=nueva_institucion.id,
                nombre=datos_usuario.get('nombre'),
                apellido=datos_usuario.get('apellido'),
                correo=datos_usuario.get('correo'),
                password=generate_password_hash(datos_usuario.get('password')),
                estado='activo'
            )
            db.session.add(nuevo_usuario)
            db.session.flush()  # Para obtener el ID
            
            # 7. Asignar rol de 'admin_tenant' al usuario
            rol_admin = Rol.query.filter_by(nombre='admin_tenant').first()
            if not rol_admin:
                # Si no existe el rol, crearlo
                rol_admin = Rol(nombre='admin_tenant')
                db.session.add(rol_admin)
                db.session.flush()
            
            usuario_rol = UsuarioRol(
                usuario_id=nuevo_usuario.id,
                rol_id=rol_admin.id
            )
            db.session.add(usuario_rol)
            
            # 8. Crear la suscripción
            nueva_suscripcion = Suscripcion(
                institucion_id=nueva_institucion.id,
                plan_id=plan_uuid,
                estado='activo'
            )
            db.session.add(nueva_suscripcion)
            
            # 9. Commitear todo (si todo está bien)
            db.session.commit()
            
            # 10. Retornar éxito con los datos creados
            return True, "Registro completado exitosamente", {
                'institucion': {
                    'id': str(nueva_institucion.id),
                    'tenant_id': str(nueva_institucion.tenant_id),
                    'nombre': nueva_institucion.nombre,
                    'tipo_institucion': nueva_institucion.tipo_institucion,
                    'telefono': nueva_institucion.telefono,
                    'email': nueva_institucion.email,
                    'estado': nueva_institucion.estado
                },
                'usuario': {
                    'id': str(nuevo_usuario.id),
                    'nombre': nuevo_usuario.nombre,
                    'apellido': nuevo_usuario.apellido,
                    'correo': nuevo_usuario.correo,
                    'estado': nuevo_usuario.estado,
                    'rol': 'admin_tenant'
                },
                'suscripcion': {
                    'id': str(nueva_suscripcion.id),
                    'institucion_id': str(nueva_suscripcion.institucion_id),
                    'plan_id': str(nueva_suscripcion.plan_id),
                    'estado': nueva_suscripcion.estado,
                    'fecha_inicio': nueva_suscripcion.fecha_inicio.isoformat() if nueva_suscripcion.fecha_inicio else None
                }
            }
            
        except IntegrityError as e:
            db.session.rollback()
            return False, f"Error de integridad en la base de datos: {str(e)}", None
        except Exception as e:
            db.session.rollback()
            return False, f"Error inesperado: {str(e)}", None