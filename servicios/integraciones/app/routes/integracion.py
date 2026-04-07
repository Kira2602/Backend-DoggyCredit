import csv
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient

integracion_bp = Blueprint('integracion', __name__)

def cargar_estado():
    path_estado = os.path.join(current_app.root_path, '..', 'data', 'estado.json')
    
    if not os.path.exists(path_estado):
        return {"offset_banco": 0}

    with open(path_estado, 'r') as f:
        return json.load(f)

def guardar_estado(estado):
    path_estado = os.path.join(current_app.root_path, '..', 'data', 'estado.json')
    with open(path_estado, 'w') as f:
        json.dump(estado, f)

def cargar_datos_tienda(dias_relevancia=90):
    tienda_dict = {}
    path = os.path.join(current_app.root_path, '..', 'data', 'dataset_tienda.csv')
    
    if not os.path.exists(path):
        return None

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

@integracion_bp.route('/sincronizar-lote', methods=['POST'])
def sincronizar_lote():
    client = None
    try:
        # 🔹 1. Estado de lote
        estado = cargar_estado()
        offset = estado.get("offset_banco", 0)
        limit = 10

        # 🔹 2. Mongo
        client = MongoClient(current_app.config['MONGO_URI'])
        db = client[current_app.config['DB_NAME']]
        coleccion = db.perfiles_centralizados

        # 🔹 3. Tienda
        tienda_data = cargar_datos_tienda(dias_relevancia=30)
        if tienda_data is None:
            return jsonify({"error": "Archivo de tienda no encontrado"}), 404
        
        # 🔹 4. Banco
        path_banco = os.path.join(current_app.root_path, '..', 'data', 'dataset_bancario.csv')
        if not os.path.exists(path_banco):
            return jsonify({"error": "Archivo bancario no encontrado"}), 404

        perfiles_enriquecidos = []

        with open(path_banco, mode='r', encoding='utf-8') as file:
            reader = list(csv.DictReader(file))

        # 🔥 AQUÍ ESTÁ EL CAMBIO IMPORTANTE
        lote = reader[offset:offset + limit]

        if not lote:
            return jsonify({
                "status": "fin",
                "mensaje": "No hay más datos para procesar"
            }), 200

        for row in lote:
            carnet_cliente = row.get('carnet')
            if not carnet_cliente:
                continue

            # --- A. TIENDA ---
            historial_tienda = tienda_data.get(carnet_cliente, [])
            for item in historial_tienda:
                item.pop('carnet', None)
                item.pop('nombre_completo', None)
                item.pop('customer_id', None)

            # --- B. BANCO ---
            datos_banco_raw = dict(row)
            nombre = datos_banco_raw.pop('nombre_completo', 'Sin Nombre')
            entidad = datos_banco_raw.pop('nombre_banco', 'Entidad Desconocida')
            datos_banco_raw.pop('carnet', None)

            # --- C. PERFIL ---
            perfil_360 = {
                "identidad": {
                    "nombre_completo": nombre,
                    "carnet": carnet_cliente
                },
                "datos_banco_raw": datos_banco_raw,
                "datos_tienda_raw": historial_tienda,
                "metadata": {
                    "estado": "ingestado_crudo",
                    "fecha_sincronizacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "num_interacciones_tienda": len(historial_tienda),
                    "lote_offset": offset
                }
            }

            perfiles_enriquecidos.append(perfil_360)

        # 🔹 5. Guardar en Mongo
        for perfil in perfiles_enriquecidos:
            coleccion.update_one(
                {"identidad.carnet": perfil['identidad']['carnet']},
                {"$set": perfil},
                upsert=True
            )

        # 🔹 6. Actualizar estado
        estado["offset_banco"] = offset + limit
        guardar_estado(estado)

        return jsonify({
            "status": "success",
            "mensaje": f"Lote procesado desde {offset} hasta {offset + len(perfiles_enriquecidos)}",
            "procesados": len(perfiles_enriquecidos)
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    
    finally:
        if client:
            client.close()