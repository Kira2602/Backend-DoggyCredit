import csv
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient

integracion_bp = Blueprint('integracion', __name__)

# --- FUNCIONES DE APOYO ---

def cargar_estado():
    path_estado = os.path.join(current_app.root_path, '..', 'data', 'estado.json')
    if not os.path.exists(path_estado):
        return {"offset_banco": 0}
    with open(path_estado, 'r') as f:
        return json.load(f)

def calcular_nro_lote(offset):
    """Convierte el offset (0, 10, 20) en número de lote (1, 2, 3)"""
    # Si el offset es 0, es el Lote 1. Si es 10, es el Lote 2, etc.
    return (offset // 10) + 1

def guardar_estado(estado):
    path_estado = os.path.join(current_app.root_path, '..', 'data', 'estado.json')
    with open(path_estado, 'w') as f:
        json.dump(estado, f)

def cargar_datos_tienda(dias_relevancia=90):
    tienda_dict = {}
    path = os.path.join(current_app.root_path, '..', 'data', 'dataset_tienda.csv')
    if not os.path.exists(path): return None

    hoy = datetime.now()
    fecha_limite = hoy - timedelta(days=dias_relevancia)

    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                fecha_busqueda = datetime.strptime(row['fecha_busqueda'], '%Y-%m-%d')
                if fecha_limite <= fecha_busqueda <= hoy:
                    carnet = row['carnet']
                    if carnet not in tienda_dict:
                        tienda_dict[carnet] = []
                    tienda_dict[carnet].append(dict(row))
            except (ValueError, KeyError):
                continue
    return tienda_dict

# --- ENDPOINTS ---

@integracion_bp.route('/sincronizar-lote', methods=['POST'])
def sincronizar_lote():
    client = None
    try:
        # 1. Cargar estado y calcular el número de lote actual
        estado = cargar_estado()
        offset = estado.get("offset_banco", 0)
        nro_lote_actual = calcular_nro_lote(offset)
        limit = 10

        client = MongoClient(current_app.config['MONGO_URI'])
        db = client[current_app.config['DB_NAME']]
        coleccion = db.perfiles_centralizados

        tienda_data = cargar_datos_tienda(dias_relevancia=30)
        path_banco = os.path.join(current_app.root_path, '..', 'data', 'dataset_bancario.csv')
        
        if not os.path.exists(path_banco):
            return jsonify({"error": "Archivo bancario no encontrado"}), 404

        with open(path_banco, mode='r', encoding='utf-8') as file:
            reader = list(csv.DictReader(file))

        lote_csv = reader[offset:offset + limit]
        if not lote_csv:
            return jsonify({"status": "fin", "mensaje": "No hay más datos"}), 200

        perfiles_enriquecidos = []

        for row in lote_csv:
            carnet_cliente = row.get('carnet')
            if not carnet_cliente: continue

            # Limpieza de Tienda
            historial_tienda = tienda_data.get(carnet_cliente, [])
            for item in historial_tienda:
                item.pop('carnet', None)
                item.pop('nombre_completo', None)
                item.pop('customer_id', None)

            # Limpieza de Banco
            datos_banco_raw = dict(row)
            nombre = datos_banco_raw.pop('nombre_completo', 'Sin Nombre')
            entidad = datos_banco_raw.pop('nombre_banco', 'Entidad Desconocida')
            datos_banco_raw.pop('carnet', None)

            perfil_360 = {
                "identidad": {
                    "nombre_completo": nombre,
                    "carnet": carnet_cliente,
                    "entidad_origen": entidad
                },
                "datos_banco_raw": datos_banco_raw,
                "datos_tienda_raw": historial_tienda,
                "metadata": {
                    "estado": "ingestado_crudo",
                    "fecha_sincronizacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "num_interacciones_tienda": len(historial_tienda),
                    "nro_lote": nro_lote_actual # Guardamos 1, 2, 3...
                }
            }
            perfiles_enriquecidos.append(perfil_360)

        # Guardado con Upsert
        for perfil in perfiles_enriquecidos:
            coleccion.update_one(
                {"identidad.carnet": perfil['identidad']['carnet']},
                {"$set": perfil},
                upsert=True
            )

        # Actualizar offset para la siguiente ejecución
        estado["offset_banco"] = offset + limit
        guardar_estado(estado)

        return jsonify({
            "status": "success",
            "mensaje": f"Lote {nro_lote_actual} procesado con éxito",
            "registros_procesados": len(perfiles_enriquecidos)
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    finally:
        if client: client.close()

@integracion_bp.route('/obtener-lote', methods=['GET'])
def obtener_lote_db():
    """
    Obtiene los registros de un lote específico (1, 2, 3...)
    Uso: /obtener-lote?nro=1
    """
    client = None
    try:
        # Por defecto intenta traer el lote anterior al actual si no se especifica
        estado = cargar_estado()
        offset_actual = estado.get("offset_banco", 0)
        nro_lote_defecto = calcular_nro_lote(offset_actual) - 1
        
        nro_a_buscar = request.args.get('nro', default=max(1, nro_lote_defecto), type=int)

        client = MongoClient(current_app.config['MONGO_URI'])
        db = client[current_app.config['DB_NAME']]
        coleccion = db.perfiles_centralizados

        # Buscamos por el campo nro_lote en la metadata
        registros = list(coleccion.find(
            {"metadata.nro_lote": nro_a_buscar}
        ))

        for r in registros:
            r['_id'] = str(r['_id'])

        return jsonify({
            "status": "success",
            "lote_nro": nro_a_buscar,
            "cantidad": len(registros),
            "registros": registros
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    finally:
        if client: client.close()