import requests
import statistics
from typing import Dict, List, Tuple
from datetime import datetime


class LoteProcessor:
    """Procesa lotes de integraciones y calcula métricas, alertas, necesidades"""
    
    INTEGRACIONES_BASE_URL = "http://integraciones:5000"  # En Docker
    # Para local: "http://localhost:5002"
    
    @staticmethod
    def obtener_lote(nro_lote: int) -> Dict:
        """Obtiene un lote de integraciones"""
        try:
            url = f"{LoteProcessor.INTEGRACIONES_BASE_URL}/api/obtener-lote?nro={nro_lote}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise ValueError(f"Error consultando integraciones: {str(e)}")
    
    @staticmethod
    def calcular_metricas(datos_banco: Dict) -> Dict:
        """Calcula métricas financieras a partir de datos_banco_raw"""
        try:
            # Extraer y calcular promedios de BILL_AMT y PAY_AMT
            bills = [
                float(datos_banco.get('BILL_AMT1', 0)),
                float(datos_banco.get('BILL_AMT2', 0)),
                float(datos_banco.get('BILL_AMT3', 0)),
                float(datos_banco.get('BILL_AMT4', 0)),
                float(datos_banco.get('BILL_AMT5', 0)),
                float(datos_banco.get('BILL_AMT6', 0)),
            ]
            
            pays = [
                float(datos_banco.get('PAY_AMT1', 0)),
                float(datos_banco.get('PAY_AMT2', 0)),
                float(datos_banco.get('PAY_AMT3', 0)),
                float(datos_banco.get('PAY_AMT4', 0)),
                float(datos_banco.get('PAY_AMT5', 0)),
                float(datos_banco.get('PAY_AMT6', 0)),
            ]
            
            promedio_bill = sum(bills) / len(bills) if bills else 0
            promedio_pay = sum(pays) / len(pays) if pays else 0
            limit_bal = float(datos_banco.get('LIMIT_BAL', 0))
            
            # Cálculos
            ratio_utilizacion = (promedio_bill / limit_bal * 100) if limit_bal > 0 else 0
            ratio_pago = (promedio_pay / promedio_bill * 100) if promedio_bill > 0 else 0
            ciclo_deuda = promedio_bill - promedio_pay
            
            # Volatilidad (desviación estándar de bills)
            if len(bills) > 1:
                media = sum(bills) / len(bills)
                varianza = sum((x - media) ** 2 for x in bills) / len(bills)
                volatilidad_gastos = varianza ** 0.5  # sqrt
            else:
                volatilidad_gastos = 0.0
            
            # Tendencia (comparar PAY_0 vs PAY_6)
            pay_0 = int(datos_banco.get('PAY_0', 0))
            pay_6 = int(datos_banco.get('PAY_6', 0))
            if pay_0 < pay_6:  # Empeora (más atraso)
                tendencia_pagos = -1
            elif pay_0 > pay_6:  # Mejora (menos atraso)
                tendencia_pagos = 1
            else:
                tendencia_pagos = 0  # Estable
            
            return {
                'ratio_utilizacion': round(ratio_utilizacion, 2),
                'ratio_pago': round(ratio_pago, 2),
                'ciclo_deuda': round(ciclo_deuda, 2),
                'volatilidad_gastos': round(volatilidad_gastos, 2),
                'tendencia_pagos': tendencia_pagos
            }
        except Exception as e:
            raise ValueError(f"Error calculando métricas: {str(e)}")
    
    @staticmethod
    def detectar_necesidades(datos_tienda: List[Dict]) -> List[Dict]:
        """Detecta necesidades/intereses del cliente a partir de historial de tienda"""
        necesidades = []
        
        if not datos_tienda:
            return necesidades
        
        # Mapeo de categorías de producto a etiquetas de interés
        categoria_map = {
            'ropa_deportiva': ['deporte', 'sport', 'zapatilla'],
            'hogar': ['cama_mesa_baño', 'muebles', 'utilidades_domesticas'],
            'electrónica': ['electrónica', 'informatica', 'consolas', 'celular'],
            'automotor': ['automotor', 'auto', 'coche'],
            'viajes': ['viaje', 'hotel', 'pasaje'],
            'belleza': ['belleza', 'cosméticos'],
            'educación': ['educación', 'libro'],
            'entretenimiento': ['deporte_ocio', 'consolas_juegos', 'cosas geniales'],
            'jardinería': ['herramientas_de_jardin', 'jardin'],
        }
        
        # Contar categorías vistas
        categorias_vistas = {}
        for item in datos_tienda:
            categoria = item.get('product_category_name', '').lower()
            if categoria:
                categorias_vistas[categoria] = categorias_vistas.get(categoria, 0) + 1
        
        # Mapear categorías a etiquetas
        etiquetas_detectadas = set()
        for categoria_vista in categorias_vistas.keys():
            for etiqueta, palabras_clave in categoria_map.items():
                for palabra in palabras_clave:
                    if palabra.lower() in categoria_vista.lower():
                        etiquetas_detectadas.add(etiqueta)
                        break
        
        # Crear necesidades
        for etiqueta in etiquetas_detectadas:
            necesidades.append({
                'etiqueta_interes': etiqueta,
                'fuente_data': 'historial_tienda'
            })
        
        return necesidades
    
    @staticmethod
    def detectar_alertas(datos_banco: Dict, datos_financieros: Dict = None) -> List[Dict]:
        """Detecta alertas basadas en comportamiento financiero"""
        alertas = []
        
        # Alerta 1: Sobre-utilización de crédito
        ratio_utilizacion = datos_banco.get('ratio_utilizacion', 0)
        if ratio_utilizacion > 90:
            alertas.append({
                'tipo_alerta': 'sobre_utilizacion',
                'descripcion': f'Cliente utiliza {ratio_utilizacion:.1f}% de su límite de crédito',
                'severidad': 'critical'
            })
        elif ratio_utilizacion > 70:
            alertas.append({
                'tipo_alerta': 'alta_utilizacion',
                'descripcion': f'Cliente utiliza {ratio_utilizacion:.1f}% de su límite de crédito',
                'severidad': 'warning'
            })
        
        # Alerta 2: Ciclo de deuda positivo (gasta más de lo que paga)
        ciclo_deuda = datos_banco.get('ciclo_deuda', 0)
        if ciclo_deuda > 0:
            alertas.append({
                'tipo_alerta': 'deuda_acumulativa',
                'descripcion': f'Cliente acumula deuda: gasta ${ciclo_deuda:.2f} más de lo que paga',
                'severidad': 'warning'
            })
        
        # Alerta 3: Riesgo de impago
        if datos_financieros and datos_financieros.get('riesgo_default') == 1:
            alertas.append({
                'tipo_alerta': 'alto_riesgo_impago',
                'descripcion': 'Predicción: Alto riesgo de impago en el próximo período',
                'severidad': 'critical'
            })
        
        # Alerta 4: Ratio de pago bajo
        ratio_pago = datos_banco.get('ratio_pago', 0)
        if ratio_pago < 50:
            alertas.append({
                'tipo_alerta': 'bajo_ratio_pago',
                'descripcion': f'Cliente paga solo {ratio_pago:.1f}% de lo que gasta',
                'severidad': 'warning'
            })
        
        return alertas
    
    @staticmethod
    def procesar_registro(
        registro: Dict,
        institucion_id: str
    ) -> Tuple[Dict, Dict, Dict, List[Dict], List[Dict]]:
        """
        Procesa un registro del lote y retorna:
        (perfil_cliente, datos_financieros, metricas, necesidades, alertas)
        """
        try:
            # Extraer datos
            identidad = registro.get('identidad', {})
            datos_banco = registro.get('datos_banco_raw', {})
            datos_tienda = registro.get('datos_tienda_raw', [])
            
            documento_id = identidad.get('carnet', '')
            nombre_completo = identidad.get('nombre_completo', 'Sin Nombre')
            
            # 1. Perfil cliente (CON demográficos)
            perfil = {
                'documento_id': documento_id,
                'id_institucion': institucion_id,
                'nombre_completo': nombre_completo,
                'edad': int(datos_banco.get('AGE', 0)) if datos_banco.get('AGE') else None,
                'educacion': str(datos_banco.get('EDUCATION', '')) if datos_banco.get('EDUCATION') else None,
                'estado_civil': str(datos_banco.get('MARRIAGE', '')) if datos_banco.get('MARRIAGE') else None,
                'sex': int(datos_banco.get('SEX', 0)) if datos_banco.get('SEX') else None,
            }
            
            # 2. Datos financieros
            bills = [
                float(datos_banco.get('BILL_AMT1', 0)),
                float(datos_banco.get('BILL_AMT2', 0)),
                float(datos_banco.get('BILL_AMT3', 0)),
                float(datos_banco.get('BILL_AMT4', 0)),
                float(datos_banco.get('BILL_AMT5', 0)),
                float(datos_banco.get('BILL_AMT6', 0)),
            ]
            
            pays = [
                float(datos_banco.get('PAY_AMT1', 0)),
                float(datos_banco.get('PAY_AMT2', 0)),
                float(datos_banco.get('PAY_AMT3', 0)),
                float(datos_banco.get('PAY_AMT4', 0)),
                float(datos_banco.get('PAY_AMT5', 0)),
                float(datos_banco.get('PAY_AMT6', 0)),
            ]
            
            promedio_bill = sum(bills) / len(bills) if bills else 0
            promedio_pay = sum(pays) / len(pays) if pays else 0
            
            comportamiento_pagos = [
                int(datos_banco.get('PAY_0', 0)),
                int(datos_banco.get('PAY_2', 0)),
                int(datos_banco.get('PAY_3', 0)),
                int(datos_banco.get('PAY_4', 0)),
                int(datos_banco.get('PAY_5', 0)),
                int(datos_banco.get('PAY_6', 0)),
            ]
            
            datos_financieros = {
                'documento_id': documento_id,
                'promedio_pay': round(promedio_pay, 2),
                'promedio_bill': round(promedio_bill, 2),
                'limit_bal': float(datos_banco.get('LIMIT_BAL', 0)) if datos_banco.get('LIMIT_BAL') else 0,
                'comportamiento_pagos': comportamiento_pagos,
                'riesgo_default': 0,  # Por defecto, sin info de predicción
            }
            
            # 3. Calcular métricas
            metricas = LoteProcessor.calcular_metricas(datos_banco)
            metricas['documento_id'] = documento_id
            
            # 4. Detectar necesidades
            necesidades = LoteProcessor.detectar_necesidades(datos_tienda)
            for nec in necesidades:
                nec['documento_id'] = documento_id
            
            # 5. Detectar alertas
            alertas = LoteProcessor.detectar_alertas(metricas)
            for alerta in alertas:
                alerta['documento_id'] = documento_id
            
            return perfil, datos_financieros, metricas, necesidades, alertas
        
        except Exception as e:
            raise ValueError(f"Error procesando registro {documento_id}: {str(e)}")
