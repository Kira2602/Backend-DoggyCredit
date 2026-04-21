import joblib
import os
import pandas as pd
from app.models import Score, Recomendacion
from app.extensions import db
from datetime import datetime
# Es vital importar la definición para que joblib sepa qué es un CreditModel
from model_definitions import CreditModel 

class ScoringService:
    MODEL_PATH = '/app/app/ai_models/modelo_credito.pkl'
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if os.path.exists(cls.MODEL_PATH):
                cls._model = joblib.load(cls.MODEL_PATH)
            else:
                raise FileNotFoundError(f"Modelo no encontrado en {cls.MODEL_PATH}")
        return cls._model

    # app/services/scoring_service.py

    @staticmethod
    def calcular_y_guardar(json_perfil, tenant_plan_pago=False):
        model = ScoringService.get_model()
        
        if tenant_plan_pago:
            res = model.predict(json_perfil)
            
            # --- CORRECCIÓN AQUÍ: Convertir de NumPy a Python native ---
            scoring_val = float(res['scoring'])
            prob_def_val = float(res['probabilidad_default'])
            prob_afin_val = float(res['probabilidad_afinidad'])
            categoria_val = str(res['categoria'])
            # ---------------------------------------------------------

            nuevo_score = Score(
                tenant_id=json_perfil['cliente'].get('id_institucion'),
                documento_id=json_perfil['cliente']['documento_id'],
                scoring=scoring_val,
                tipo_plan=True,
                probabilidad_default=prob_def_val,
                nivel_riesgo=res['nivel_riesgo']
            )
            
            db.session.add(nuevo_score)
            db.session.flush()

            nueva_rec = Recomendacion(
                score_id=nuevo_score.id,
                categoria=str(res['categoria']), # Aseguramos que sea string
                probabilidad_afinidad=prob_afin_val
            )
            db.session.add(nueva_rec)
            
        else:
            # Lógica básica (ya suele ser float de Python)
            score_base = float(json_perfil.get('metricas', {}).get('ratio_pago', 0) * 10)
            nuevo_score = Score(
                tenant_id=json_perfil['cliente'].get('id_institucion'),
                documento_id=json_perfil['cliente']['documento_id'],
                scoring=round(score_base, 2),
                tipo_plan=False,
                nivel_riesgo="medium" if score_base > 500 else "high"
            )
            db.session.add(nuevo_score)
            nueva_rec = None

        db.session.commit()
        return nuevo_score, nueva_rec

    @staticmethod
    def _predecir_score(payload, es_plan_pago):
        if es_plan_pago:
            model = ScoringService.get_model()
            # El DataFrame debe usar los nombres exactos que espera el v1.0.2
            data_input = pd.DataFrame([{
                'payment_ratio': payload.get('ratio_pago', 0),
                'utilization_ratio': payload.get('ratio_utilizacion', 0),
                'debt_cycle': payload.get('ciclo_deuda', 0),
                'volatility': payload.get('volatilidad_gastos', 0),
                'num_alerts': payload.get('total_alerts', 0),
                'num_warnings': payload.get('total_warnings', 0),
                'age': payload.get('edad', 0),
                'avg_bill': payload.get('avg_bill', 0),
                'avg_payment': payload.get('avg_payment', 0),
                'payment_std': payload.get('volatilidad_gastos', 0),
                'limit_bal': payload.get('limit_bal', 0)
            }])

            try:
                prob_default = model.predict_proba(data_input)[0][1]
                return round((1 - prob_default) * 1000, 2)
            except Exception as e:
                print(f"Error IA: {e}")
                return round(payload.get('ratio_pago', 0) * 10, 2)
        
        return round(payload.get('ratio_pago', 0) * 10, 2)