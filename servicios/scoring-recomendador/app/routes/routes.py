from flask import Blueprint, request, jsonify
from .services.scoring_service import ScoringService
import logging

scoring_bp = Blueprint('scoring', __name__)
logger = logging.getLogger(__name__)

@scoring_bp.route('/procesar-scoring', methods=['POST'])
def procesar_scoring():
    """
    Endpoint que recibe el perfil completo y dispara el cálculo.
    Se espera el JSON que genera el microservicio de Perfilamiento.
    """
    try:
        datos = request.get_json()
        
        if not datos or 'cliente' not in datos:
            return jsonify({'error': 'Datos de perfil no proporcionados'}), 400
        
        # Extraemos la información necesaria del JSON recibido
        # Basado en la estructura de tu perfil.py
        documento_id = datos['cliente']['documento_id']
        id_institucion = datos['cliente']['id_institucion']
        
        # Simulamos la verificación del plan (esto vendría del Tenant Manager)
        # Por ahora lo decidimos por un campo en el request o lógica de negocio
        es_plan_pago = request.args.get('plan') == 'pago'
        
        # Consolidamos los datos para el servicio
        # Mezclamos datos básicos, métricas y necesidades en un solo diccionario
        payload_proceso = {
            'documento_id': documento_id,
            'id_institucion': id_institucion,
            'ratio_utilizacion': datos.get('metricas', {}).get('ratio_utilizacion', 0),
            'ratio_pago': datos.get('metricas', {}).get('ratio_pago', 0),
            'volatilidad_gastos': datos.get('metricas', {}).get('volatilidad_gastos', 0),
            'tendencia_pagos': datos.get('metricas', {}).get('tendencia_pagos', 0),
            'necesidades': datos.get('necesidades', [])
        }
        
        # Ejecutamos el motor de IA / Reglas
        resultado = ScoringService.calcular_y_guardar(payload_proceso, tenant_plan_pago=es_plan_pago)
        
        return jsonify({
            'status': 'success',
            'message': f'Scoring calculado para cliente {documento_id}',
            'score': resultado.scoring,
            'nivel': resultado.nivel_riesgo
        }), 201

    except Exception as e:
        logger.error(f"Error en endpoint de scoring: {str(e)}")
        return jsonify({'error': 'Error interno al procesar el scoring'}), 500

@scoring_bp.route('/resultado/<documento_id>', methods=['GET'])
def obtener_resultado(documento_id):
    """
    Retorna el último score y recomendaciones para el Dashboard
    """
    from .models import Score
    
    ultimo_score = Score.query.filter_by(documento_id=documento_id)\
                              .order_by(Score.fecha.desc()).first()
    
    if not ultimo_score:
        return jsonify({'error': 'No se encontró scoring para este documento'}), 404
        
    return jsonify({
        'documento_id': ultimo_score.documento_id,
        'scoring': ultimo_score.scoring,
        'riesgo': ultimo_score.nivel_riesgo,
        'plan_aplicado': 'IA Avanzada' if ultimo_score.tipo_plan else 'Básico',
        'recomendaciones': [
            {
                'categoria': r.categoria,
                'probabilidad': float(r.probabilidad),
                'insight': r.insight_ia
            } for r in ultimo_score.recomendaciones
        ]
    }), 200