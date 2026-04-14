import pandas as pd
import json
from typing import Tuple, List, Dict
from io import BytesIO


class DatasetParser:
    """Parsea archivos CSV/XLSX y mapea datos al formato esperado"""
    
    REQUIRED_COLUMNS = {
        'ID': 'documento_id',
        'SEX': 'sex',
        'EDUCATION': 'educacion',
        'MARRIAGE': 'estado_civil',
        'AGE': 'edad',
        'LIMIT_BAL': 'limit_bal',
        'PAY_0': 'pay_0',
        'PAY_2': 'pay_2',
        'PAY_3': 'pay_3',
        'PAY_4': 'pay_4',
        'PAY_5': 'pay_5',
        'PAY_6': 'pay_6',
        'BILL_AMT1': 'bill_amt1',
        'BILL_AMT2': 'bill_amt2',
        'BILL_AMT3': 'bill_amt3',
        'BILL_AMT4': 'bill_amt4',
        'BILL_AMT5': 'bill_amt5',
        'BILL_AMT6': 'bill_amt6',
        'PAY_AMT1': 'pay_amt1',
        'PAY_AMT2': 'pay_amt2',
        'PAY_AMT3': 'pay_amt3',
        'PAY_AMT4': 'pay_amt4',
        'PAY_AMT5': 'pay_amt5',
        'PAY_AMT6': 'pay_amt6',
        'default.payment.next.month': 'riesgo_default'
    }
    
    @staticmethod
    def parse_file(file_content: bytes, filename: str) -> pd.DataFrame:
        """Lee CSV o XLSX y retorna DataFrame"""
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(file_content))
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(BytesIO(file_content))
            else:
                raise ValueError("Solo se aceptan archivos .csv o .xlsx")
            
            return df
        except Exception as e:
            raise ValueError(f"Error al parsear archivo: {str(e)}")
    
    @staticmethod
    def validate_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Valida que el DataFrame tenga todas las columnas requeridas (excepto la de predicción que es opcional)"""
        required_cols = [col for col in DatasetParser.REQUIRED_COLUMNS.keys() 
                        if col != 'default.payment.next.month']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return False, missing_cols
        return True, []
    
    @staticmethod
    def map_to_models(df: pd.DataFrame, institucion_id: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Mapea datos del DataFrame a estructura de perfiles_clientes y datos_financieros
        
        Returns:
            Tuple (perfiles_list, datos_financieros_list)
        """
        perfiles = []
        datos_financieros = []
        
        for _, row in df.iterrows():
            try:
                documento_id = str(row['ID']).strip()
                
                # Mapeo para perfiles_clientes
                perfil = {
                    'documento_id': documento_id,
                    'id_institucion': institucion_id,
                    'nombre_completo': f"Cliente #{documento_id}",
                    'edad': int(row['AGE']) if pd.notna(row['AGE']) else None,
                    'educacion': str(row['EDUCATION']) if pd.notna(row['EDUCATION']) else None,
                    'estado_civil': str(row['MARRIAGE']) if pd.notna(row['MARRIAGE']) else None,
                    'sex': int(row['SEX']) if pd.notna(row['SEX']) else None,
                }
                
                # Cálculos para datos_financieros
                bill_amounts = [
                    float(row['BILL_AMT1']) if pd.notna(row['BILL_AMT1']) else 0,
                    float(row['BILL_AMT2']) if pd.notna(row['BILL_AMT2']) else 0,
                    float(row['BILL_AMT3']) if pd.notna(row['BILL_AMT3']) else 0,
                    float(row['BILL_AMT4']) if pd.notna(row['BILL_AMT4']) else 0,
                    float(row['BILL_AMT5']) if pd.notna(row['BILL_AMT5']) else 0,
                    float(row['BILL_AMT6']) if pd.notna(row['BILL_AMT6']) else 0,
                ]
                
                pay_amounts = [
                    float(row['PAY_AMT1']) if pd.notna(row['PAY_AMT1']) else 0,
                    float(row['PAY_AMT2']) if pd.notna(row['PAY_AMT2']) else 0,
                    float(row['PAY_AMT3']) if pd.notna(row['PAY_AMT3']) else 0,
                    float(row['PAY_AMT4']) if pd.notna(row['PAY_AMT4']) else 0,
                    float(row['PAY_AMT5']) if pd.notna(row['PAY_AMT5']) else 0,
                    float(row['PAY_AMT6']) if pd.notna(row['PAY_AMT6']) else 0,
                ]
                
                promedio_bill = sum(bill_amounts) / len(bill_amounts) if bill_amounts else 0
                promedio_pay = sum(pay_amounts) / len(pay_amounts) if pay_amounts else 0
                
                # Comportamiento de pagos
                comportamiento_pagos = [
                    int(row['PAY_0']) if pd.notna(row['PAY_0']) else 0,
                    int(row['PAY_2']) if pd.notna(row['PAY_2']) else 0,
                    int(row['PAY_3']) if pd.notna(row['PAY_3']) else 0,
                    int(row['PAY_4']) if pd.notna(row['PAY_4']) else 0,
                    int(row['PAY_5']) if pd.notna(row['PAY_5']) else 0,
                    int(row['PAY_6']) if pd.notna(row['PAY_6']) else 0,
                ]
                
                datos_fin = {
                    'documento_id': documento_id,
                    'promedio_pay': promedio_pay,
                    'promedio_bill': promedio_bill,
                    'limit_bal': float(row['LIMIT_BAL']) if pd.notna(row['LIMIT_BAL']) else 0,
                    'comportamiento_pagos': comportamiento_pagos,
                    'riesgo_default': int(row['default.payment.next.month']) if 'default.payment.next.month' in df.columns and pd.notna(row['default.payment.next.month']) else 0,
                }
                
                perfiles.append(perfil)
                datos_financieros.append(datos_fin)
                
            except Exception as e:
                raise ValueError(f"Error procesando fila {documento_id}: {str(e)}")
        
        return perfiles, datos_financieros
