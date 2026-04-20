from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import PerfilCliente, DatosFinancieros, MetricasFinancieras, AnalisisNecesidades, AlertasCliente, Institucion
from ..lote_processor import LoteProcessor
import logging
import uuid

lote_bp = Blueprint('lote', __name__)
logger = logging.getLogger(__name__)

def obtener_institucion_id(nombre_banco):
    """Obtiene el UUID del banco desde BD. Si no existe, crea uno nuevo."""
    institucion = Institucion.query.filter_by(nombre_fintech=nombre_banco).first()
    if institucion:
        return institucion.id
    
    # Si no existe, crear nuevo
    nuevo_id = str(uuid.uuid4())
    nueva_inst = Institucion(id=nuevo_id, nombre_fintech=nombre_banco)
    db.session.add(nueva_inst)
    db.session.flush()
    return nuevo_id


@lote_bp.route('/procesar-lote', methods=['POST'])
def procesar_lote():
    """
    POST /api/procesar-lote?nro=1
    
    Procesa un lote de integraciones (hardcoded: Banco Test):
    1. Consulta GET /api/integraciones/obtener-lote?nro=X
    2. Por cada registro:
       - Crea/actualiza perfil cliente
       - Calcula métricas financieras
       - Detecta necesidades/intereses
       - Detecta alertas
    """
    try:
        nro_lote = request.args.get('nro', default=1, type=int)
        institucion_id = '550e8400-e29b-41d4-a716-446655440000'  # Banco Test (hardcoded)
        
        # Obtener lote de integraciones
        lote_data = LoteProcessor.obtener_lote(nro_lote)
        
        if lote_data.get('status') != 'success':
            return jsonify({'error': 'No se pudo obtener lote de integraciones'}), 400
        
        registros = lote_data.get('registros', [])
        if not registros:
            return jsonify({'error': 'Lote vacío'}), 400
        
        # Procesar cada registro
        stats = {
            'perfiles_creados': 0,
            'perfiles_actualizados': 0,
            'metricas_creadas': 0,
            'necesidades_detectadas': 0,
            'alertas_creadas': 0,
            'errores': []
        }
        
        try:
            for registro in registros:
                try:
                    # Procesar registro
                    perfil_data, datos_fin_data, metricas_data, necesidades_list, alertas_list = \
                        LoteProcessor.procesar_registro(registro, institucion_id)
                    
                    documento_id = perfil_data['documento_id']
                    
                    # 1. Guardar/actualizar perfil
                    perfil_existente = PerfilCliente.query.filter_by(
                        documento_id=documento_id,
                        id_institucion=institucion_id
                    ).first()
                    
                    if perfil_existente:
                        for key, value in perfil_data.items():
                            if key not in ['documento_id', 'id_institucion']:
                                setattr(perfil_existente, key, value)
                        stats['perfiles_actualizados'] += 1
                    else:
                        perfil = PerfilCliente(**perfil_data)
                        db.session.add(perfil)
                        stats['perfiles_creados'] += 1
                    
                    db.session.flush()  # Asegurar que perfil existe
                    
                    # 2. Guardar/actualizar datos financieros
                    if datos_fin_data:
                        datos_fin_existentes = DatosFinancieros.query.filter_by(
                            documento_id=documento_id
                        ).first()
                        
                        if datos_fin_existentes:
                            datos_fin_existentes.version_data = (datos_fin_existentes.version_data or 0) + 1
                            for key, value in datos_fin_data.items():
                                if key != 'documento_id':
                                    setattr(datos_fin_existentes, key, value)
                        else:
                            datos_fin = DatosFinancieros(**datos_fin_data)
                            db.session.add(datos_fin)
                    
                    # 3. Guardar métricas
                    if metricas_data:
                        metricas_existentes = MetricasFinancieras.query.filter_by(
                            documento_id=documento_id
                        ).first()
                        
                        if metricas_existentes:
                            for key, value in metricas_data.items():
                                if key != 'documento_id':
                                    setattr(metricas_existentes, key, value)
                        else:
                            metricas = MetricasFinancieras(**metricas_data)
                            db.session.add(metricas)
                        
                        stats['metricas_creadas'] += 1
                    
                    # 4. Guardar necesidades
                    for nec_data in necesidades_list:
                        necesidad = AnalisisNecesidades(**nec_data)
                        db.session.add(necesidad)
                        stats['necesidades_detectadas'] += 1
                    
                    # 5. Guardar alertas
                    for alerta_data in alertas_list:
                        alerta = AlertasCliente(**alerta_data)
                        db.session.add(alerta)
                        stats['alertas_creadas'] += 1
                
                except Exception as e:
                    error_msg = f"Error procesando registro: {str(e)}"
                    logger.error(error_msg)
                    stats['errores'].append(error_msg)
            
            # Commit de todo
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'lote': nro_lote,
                'stats': stats
            }), 201
        
        except Exception as db_error:
            db.session.rollback()
            logger.error(f"Database error: {str(db_error)}")
            return jsonify({'error': f'Error guardando en BD: {str(db_error)}'}), 500
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@lote_bp.route('/procesar-lote-desde-integraciones', methods=['POST'])
def procesar_lote_desde_integraciones():
    """
    POST /api/procesar-lote-desde-integraciones
    
    Recibe el JSON completo de /sincronizar-lote de Integraciones.
    Por cada registro, procesa y guarda en PostgreSQL.
    
    Body esperado: El JSON completo devuelto por POST /sincronizar-lote
    {
        "mensaje": "...",
        "registros": [ {...}, {...} ],
        "registros_procesados": 10,
        "status": "success"
    }
    """
    try:
        data = request.get_json() or {}
        registros = data.get('registros', [])
        
        if not registros:
            return jsonify({'error': 'No hay registros en la solicitud'}), 400
        
        # Obtener nombre del banco del primer registro
        nombre_banco = registros[0].get('identidad', {}).get('entidad_origen')
        if not nombre_banco:
            return jsonify({'error': 'No se pudo determinar el banco'}), 400
        
        # Obtener o crear institución dinámicamente
        institucion_id = obtener_institucion_id(nombre_banco)
        
        # Estadísticas
        stats = {
            'perfiles_creados': 0,
            'perfiles_actualizados': 0,
            'datos_financieros_creados': 0,
            'datos_financieros_actualizados': 0,
            'metricas_creadas': 0,
            'necesidades_detectadas': 0,
            'alertas_creadas': 0,
            'errores': []
        }
        
        try:
            for registro in registros:
                try:
                    # Procesar registro usando la lógica existente
                    perfil_data, datos_fin_data, metricas_data, necesidades_list, alertas_list = \
                        LoteProcessor.procesar_registro(registro, institucion_id)
                    
                    documento_id = perfil_data['documento_id']
                    
                    # 1. Guardar/actualizar perfil
                    perfil_existente = PerfilCliente.query.filter_by(
                        documento_id=documento_id,
                        id_institucion=institucion_id
                    ).first()
                    
                    if perfil_existente:
                        for key, value in perfil_data.items():
                            if key not in ['documento_id', 'id_institucion']:
                                setattr(perfil_existente, key, value)
                        stats['perfiles_actualizados'] += 1
                    else:
                        perfil = PerfilCliente(**perfil_data)
                        db.session.add(perfil)
                        stats['perfiles_creados'] += 1
                    
                    db.session.flush()  # Asegurar que perfil existe
                    
                    # 2. Guardar/actualizar datos financieros
                    if datos_fin_data:
                        datos_fin_existentes = DatosFinancieros.query.filter_by(
                            documento_id=documento_id
                        ).first()
                        
                        if datos_fin_existentes:
                            datos_fin_existentes.version_data = (datos_fin_existentes.version_data or 0) + 1
                            for key, value in datos_fin_data.items():
                                if key != 'documento_id':
                                    setattr(datos_fin_existentes, key, value)
                            stats['datos_financieros_actualizados'] += 1
                        else:
                            datos_fin = DatosFinancieros(**datos_fin_data)
                            db.session.add(datos_fin)
                            stats['datos_financieros_creados'] += 1
                    
                    # 3. Guardar métricas
                    if metricas_data:
                        metricas_existentes = MetricasFinancieras.query.filter_by(
                            documento_id=documento_id
                        ).first()
                        
                        if metricas_existentes:
                            for key, value in metricas_data.items():
                                if key != 'documento_id':
                                    setattr(metricas_existentes, key, value)
                        else:
                            metricas = MetricasFinancieras(**metricas_data)
                            db.session.add(metricas)
                        
                        stats['metricas_creadas'] += 1
                    
                    # 4. Guardar necesidades
                    for nec_data in necesidades_list:
                        necesidad = AnalisisNecesidades(**nec_data)
                        db.session.add(necesidad)
                        stats['necesidades_detectadas'] += 1
                    
                    # 5. Guardar alertas
                    for alerta_data in alertas_list:
                        alerta = AlertasCliente(**alerta_data)
                        db.session.add(alerta)
                        stats['alertas_creadas'] += 1
                
                except Exception as e:
                    error_msg = f"Error procesando registro {documento_id if 'documento_id' in locals() else 'desconocido'}: {str(e)}"
                    logger.error(error_msg)
                    stats['errores'].append(error_msg)
            
            # Commit de todo
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'banco': nombre_banco,
                'institucion_id': institucion_id,
                'registros_procesados': len(registros),
                'stats': stats
            }), 201
        
        except Exception as db_error:
            db.session.rollback()
            logger.error(f"Database error: {str(db_error)}")
            return jsonify({'error': f'Error guardando en BD: {str(db_error)}'}), 500
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
