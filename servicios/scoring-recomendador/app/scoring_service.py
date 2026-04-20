import logging
from .models import Score, Recomendacion
from ..extensions import db
# Aquí importarías tu modelo entrenado (ejemplo con joblib)
# import joblib
# model = joblib.load('path_to_model/modelo_scoring_pago.pkl')

logger = logging.getLogger(__name__)

class ScoringService:

    @staticmethod
    def calcular_y_guardar(datos_perfil, tenant_plan_pago=False):
        """
        datos_perfil: Diccionario con la info de MetricasFinancieras y DatosFinancieros
        tenant_plan_pago: Booleano que indica si la institución paga o no
        """
        try:
            documento_id = datos_perfil.get('documento_id')
            tenant_id = datos_perfil.get('id_institucion')
            
            # 1. Decidir qué tipo de Scoring aplicar
            if not tenant_plan_pago:
                # LÓGICA PLAN GRATUITO: Score básico basado en reglas
                # Ejemplo: (Ratio Pago * 0.7 + Ratio Utilización * 0.3) * 1000
                ratio_pago = float(datos_perfil.get('ratio_pago', 0))
                ratio_util = float(datos_perfil.get('ratio_utilizacion', 0))
                
                score_final = (ratio_pago * 0.7 + (1 - ratio_util) * 0.3) * 1000
                prob_default = None
                nivel_riesgo = "N/A (Plan Básico)"
                tipo_plan = False
            else:
                # LÓGICA PLAN PAGO: Inferencia con Modelo de IA
                # Extraemos las 'features' para el modelo
                features = [
                    float(datos_perfil.get('ratio_utilizacion', 0)),
                    float(datos_perfil.get('ratio_pago', 0)),
                    float(datos_perfil.get('volatilidad_gastos', 0)),
                    int(datos_perfil.get('tendencia_pagos', 0))
                ]
                
                # Simulación de predicción del modelo (ML Inference)
                # prob_default = model.predict_proba([features])[0][1]
                prob_default = 0.15 # Ejemplo de salida del modelo
                score_final = (1 - prob_default) * 1000
                
                if score_final > 700: nivel_riesgo = "Bajo"
                elif score_final > 400: nivel_riesgo = "Medio"
                else: nivel_riesgo = "Alto"
                
                tipo_plan = True

            # 2. Guardar el Score en la BD
            nuevo_score = Score(
                documento_id=documento_id,
                tenant_id=tenant_id,
                scoring=score_final,
                tipo_plan=tipo_plan,
                probabilidad_default=prob_default,
                nivel_riesgo=nivel_riesgo
            )
            db.session.add(nuevo_score)
            db.session.flush() # Para obtener el ID del score antes del commit

            # 3. Generar Recomendación Automática (Cerebro de IA)
            ScoringService._generar_recomendaciones(nuevo_score, datos_perfil)

            db.session.commit()
            return nuevo_score

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error en el cálculo de scoring: {str(e)}")
            raise e

    @staticmethod
    def _generar_recomendaciones(score_obj, datos_perfil):
        """
        Lógica interna para crear las recomendaciones basadas en el score y necesidades
        """
        necesidades = datos_perfil.get('necesidades', [])
        
        for n in necesidades:
            etiqueta = n.get('etiqueta_interes')
            
            # Lógica simple de recomendación:
            # Si el score es alto y tiene interés en 'PYME', recomendamos con alta prob.
            prob_afinidad = 0.9 if score_obj.scoring > 600 else 0.4
            
            nueva_rec = Recomendacion(
                score_id=score_obj.id,
                categoria=etiqueta,
                probabilidad=prob_afinidad,
                insight_ia=f"Recomendado por afinidad en {etiqueta} y score de {score_obj.nivel_riesgo}"
            )
            db.session.add(nueva_rec)