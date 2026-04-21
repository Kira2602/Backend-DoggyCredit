from flask import Blueprint, request, jsonify
from app.extensions import db
from app.scoring_service import ScoringService
import logging

scoring_bp = Blueprint('scoring', __name__)
logger = logging.getLogger(__name__)

@scoring_bp.route('/procesar-scoring', methods=['POST'])
def procesar_scoring():
    try:
        datos = request.get_json()
        es_pago = datos.get('es_plan_pago', False) or (request.args.get('plan') == 'pago')
        
        score_obj, rec_obj = ScoringService.calcular_y_guardar(datos, tenant_plan_pago=es_pago)
        
        response = {
            'documento_id': score_obj.documento_id,
            'scoring': score_obj.scoring,
            'nivel_riesgo': score_obj.nivel_riesgo,
            'metodo': 'IA Avanzada' if score_obj.tipo_plan else 'Básico'
        }

        if rec_obj:
            response['recomendacion'] = {
                'producto': rec_obj.categoria,
                'afinidad': float(rec_obj.probabilidad_afinidad) # numeric a float para JSON
            }
            
        return jsonify({'status': 'success', 'data': response}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500