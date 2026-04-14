from flask import Blueprint, jsonify
from ..extensions import db
from ..models import PerfilCliente, DatosFinancieros, MetricasFinancieras, AnalisisNecesidades, AlertasCliente
import logging

perfil_bp = Blueprint('perfil', __name__)
logger = logging.getLogger(__name__)


@perfil_bp.route('/clientes', methods=['GET'])
def listar_clientes():
    """
    GET /api/clientes
    Retorna lista de todos los clientes
    """
    try:
        clientes = PerfilCliente.query.all()
        
        resultado = {
            'total': len(clientes),
            'clientes': [
                {
                    'documento_id': c.documento_id,
                    'nombre_completo': c.nombre_completo,
                    'edad': c.edad,
                    'id_institucion': c.id_institucion
                }
                for c in clientes
            ]
        }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error listando clientes: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@perfil_bp.route('/perfil/<documento_id>', methods=['GET'])
def obtener_perfil(documento_id):
    """
    GET /api/perfil/{documento_id}
    Retorna: perfil_cliente + datos_financieros
    """
    try:
        perfil = PerfilCliente.query.filter_by(documento_id=documento_id).first()
        
        if not perfil:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        datos_fin = DatosFinancieros.query.filter_by(documento_id=documento_id).first()
        
        resultado = {
            'perfil': {
                'documento_id': perfil.documento_id,
                'nombre_completo': perfil.nombre_completo,
                'edad': perfil.edad,
                'educacion': perfil.educacion,
                'estado_civil': perfil.estado_civil,
                'sexo': perfil.sex,
                'id_institucion': perfil.id_institucion,
                'created_at': perfil.created_at.isoformat() if perfil.created_at else None,
                'updated_at': perfil.updated_at.isoformat() if perfil.updated_at else None,
            }
        }
        
        if datos_fin:
            resultado['datos_financieros'] = {
                'promedio_pay': float(datos_fin.promedio_pay) if datos_fin.promedio_pay else 0,
                'promedio_bill': float(datos_fin.promedio_bill) if datos_fin.promedio_bill else 0,
                'limit_bal': float(datos_fin.limit_bal) if datos_fin.limit_bal else 0,
                'comportamiento_pagos': datos_fin.comportamiento_pagos,
                'riesgo_default': datos_fin.riesgo_default,
                'version_data': datos_fin.version_data,
                'created_at': datos_fin.created_at.isoformat() if datos_fin.created_at else None,
            }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo perfil: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@perfil_bp.route('/metricas/<documento_id>', methods=['GET'])
def obtener_metricas(documento_id):
    """
    GET /api/metricas/{documento_id}
    Retorna: métricas financieras calculadas
    """
    try:
        metricas = MetricasFinancieras.query.filter_by(documento_id=documento_id).all()
        
        if not metricas:
            return jsonify({'error': 'No hay métricas para este cliente'}), 404
        
        resultado = {
            'documento_id': documento_id,
            'total_registros': len(metricas),
            'metricas': [
                {
                    'id': m.id,
                    'ratio_utilizacion': float(m.ratio_utilizacion) if m.ratio_utilizacion else 0,
                    'ratio_pago': float(m.ratio_pago) if m.ratio_pago else 0,
                    'ciclo_deuda': float(m.ciclo_deuda) if m.ciclo_deuda else 0,
                    'volatilidad_gastos': float(m.volatilidad_gastos) if m.volatilidad_gastos else 0,
                    'tendencia_pagos': m.tendencia_pagos,
                    'created_at': m.created_at.isoformat() if m.created_at else None,
                }
                for m in metricas
            ]
        }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@perfil_bp.route('/necesidades/<documento_id>', methods=['GET'])
def obtener_necesidades(documento_id):
    """
    GET /api/necesidades/{documento_id}
    Retorna: intereses/necesidades detectados del cliente
    """
    try:
        necesidades = AnalisisNecesidades.query.filter_by(documento_id=documento_id).all()
        
        if not necesidades:
            return jsonify({
                'documento_id': documento_id,
                'total': 0,
                'necesidades': []
            }), 200
        
        resultado = {
            'documento_id': documento_id,
            'total': len(necesidades),
            'necesidades': [
                {
                    'id': n.id,
                    'etiqueta_interes': n.etiqueta_interes,
                    'fuente_data': n.fuente_data,
                    'fecha_deteccion': n.fecha_deteccion.isoformat() if n.fecha_deteccion else None,
                }
                for n in necesidades
            ]
        }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo necesidades: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@perfil_bp.route('/alertas/<documento_id>', methods=['GET'])
def obtener_alertas(documento_id):
    """
    GET /api/alertas/{documento_id}
    Retorna: alertas/banderas detectadas del cliente
    """
    try:
        alertas = AlertasCliente.query.filter_by(documento_id=documento_id).all()
        
        if not alertas:
            return jsonify({
                'documento_id': documento_id,
                'total': 0,
                'alertas': []
            }), 200
        
        # Contar por severidad
        severidad_count = {
            'info': 0,
            'warning': 0,
            'critical': 0
        }
        
        alertas_list = []
        for a in alertas:
            severidad_count[a.severidad] = severidad_count.get(a.severidad, 0) + 1
            alertas_list.append({
                'id': a.id,
                'tipo_alerta': a.tipo_alerta,
                'descripcion': a.descripcion,
                'severidad': a.severidad,
                'created_at': a.created_at.isoformat() if a.created_at else None,
            })
        
        resultado = {
            'documento_id': documento_id,
            'total': len(alertas),
            'por_severidad': severidad_count,
            'alertas': alertas_list
        }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@perfil_bp.route('/perfil-completo/<documento_id>', methods=['GET'])
def obtener_perfil_completo(documento_id):
    """
    GET /api/perfil-completo/{documento_id}
    Retorna: Perfil COMPLETO del cliente en una sola respuesta:
    - Datos demográficos y generales
    - Datos financieros
    - Métricas calculadas
    - Necesidades/intereses detectados
    - Alertas activas
    """
    try:
        perfil = PerfilCliente.query.filter_by(documento_id=documento_id).first()
        
        if not perfil:
            return jsonify({'error': 'Cliente no encontrado'}), 404
        
        # 1. Datos básicos del perfil
        resultado = {
            'status': 'success',
            'cliente': {
                'documento_id': perfil.documento_id,
                'nombre_completo': perfil.nombre_completo,
                'edad': perfil.edad,
                'educacion': perfil.educacion,
                'estado_civil': perfil.estado_civil,
                'sexo': perfil.sex,
                'id_institucion': perfil.id_institucion,
                'fecha_creacion': perfil.created_at.isoformat() if perfil.created_at else None,
                'ultima_actualizacion': perfil.updated_at.isoformat() if perfil.updated_at else None,
            }
        }
        
        # 2. Datos financieros
        datos_fin = DatosFinancieros.query.filter_by(documento_id=documento_id).first()
        if datos_fin:
            resultado['datos_financieros'] = {
                'promedio_pay': float(datos_fin.promedio_pay) if datos_fin.promedio_pay else 0,
                'promedio_bill': float(datos_fin.promedio_bill) if datos_fin.promedio_bill else 0,
                'limit_bal': float(datos_fin.limit_bal) if datos_fin.limit_bal else 0,
                'comportamiento_pagos': datos_fin.comportamiento_pagos,
                'riesgo_default': datos_fin.riesgo_default,
                'version_data': datos_fin.version_data,
            }
        else:
            resultado['datos_financieros'] = None
        
        # 3. Métricas
        metricas = MetricasFinancieras.query.filter_by(documento_id=documento_id).first()
        if metricas:
            resultado['metricas'] = {
                'ratio_utilizacion': float(metricas.ratio_utilizacion) if metricas.ratio_utilizacion else 0,
                'ratio_pago': float(metricas.ratio_pago) if metricas.ratio_pago else 0,
                'ciclo_deuda': float(metricas.ciclo_deuda) if metricas.ciclo_deuda else 0,
                'volatilidad_gastos': float(metricas.volatilidad_gastos) if metricas.volatilidad_gastos else 0,
                'tendencia_pagos': metricas.tendencia_pagos,
            }
        else:
            resultado['metricas'] = None
        
        # 4. Necesidades/intereses
        necesidades = AnalisisNecesidades.query.filter_by(documento_id=documento_id).all()
        resultado['necesidades'] = [
            {
                'etiqueta_interes': n.etiqueta_interes,
                'fuente_data': n.fuente_data,
                'fecha_deteccion': n.fecha_deteccion.isoformat() if n.fecha_deteccion else None,
            }
            for n in necesidades
        ]
        
        # 5. Alertas
        alertas = AlertasCliente.query.filter_by(documento_id=documento_id).all()
        severidad_count = {'info': 0, 'warning': 0, 'critical': 0}
        alertas_list = []
        
        for a in alertas:
            severidad_count[a.severidad] = severidad_count.get(a.severidad, 0) + 1
            alertas_list.append({
                'tipo_alerta': a.tipo_alerta,
                'descripcion': a.descripcion,
                'severidad': a.severidad,
                'fecha': a.created_at.isoformat() if a.created_at else None,
            })
        
        resultado['alertas'] = {
            'total': len(alertas),
            'por_severidad': severidad_count,
            'lista': alertas_list
        }
        
        return jsonify(resultado), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo perfil completo: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
