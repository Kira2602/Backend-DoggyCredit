import pandas as pd
import numpy as np

def extract_features_from_json(data):
    alertas = data.get("alertas", {})
    cliente = data.get("cliente", {})
    financieros = data.get("datos_financieros", {})
    metricas = data.get("metricas", {})

    total_alerts = alertas.get("total", 0)
    warnings = alertas.get("por_severidad", {}).get("warning", 0)

    comportamiento = financieros.get("comportamiento_pagos", [])
    payment_std = np.std(comportamiento) if len(comportamiento) > 0 else 0

    features = {
        "payment_ratio": metricas.get("ratio_pago", 0),
        "utilization_ratio": metricas.get("ratio_utilizacion", 0),
        "debt_cycle": metricas.get("ciclo_deuda", 0),
        "volatility": metricas.get("volatilidad_gastos", 0),
        "num_alerts": total_alerts,
        "num_warnings": warnings,
        "age": cliente.get("edad", 30),
        "avg_bill": financieros.get("promedio_bill", 0),
        "avg_payment": financieros.get("promedio_pay", 0),
        "payment_std": payment_std,
        "limit_bal": financieros.get("limit_bal", 0)
    }
    return pd.DataFrame([features])

class CreditModel:
    def __init__(self, score_model, plan_model):
        self.score_model = score_model
        self.plan_model = plan_model

    def predict(self, input_json):
        X = extract_features_from_json(input_json)
        scoring = float(self.score_model.predict(X)[0])
        prob_default = 1 / (1 + np.exp((scoring - 450) / 100))
        nivel_riesgo = self.get_risk(scoring)
        plan_idx = int(self.plan_model.predict(X)[0])
        categoria = "ecocredit" if plan_idx == 1 else "microcredit"
        prob_afinidad = float(np.max(self.plan_model.predict_proba(X)[0]))

        return {
            "scoring": round(scoring, 2),
            "probabilidad_default": round(prob_default, 4),
            "nivel_riesgo": nivel_riesgo,
            "categoria": categoria,
            "probabilidad_afinidad": round(prob_afinidad, 4)
        }

    def get_risk(self, score):
        if score < 500: return "high"
        elif score < 650: return "medium"
        return "low"
