import csv
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient

integracion_bp = Blueprint('integracion', __name__)


MAPEO_BANCOS = {
    "BANCO FREE": 1,
    "BANCO PAGA": 2,
    "Banco Solidario": 3,
    "Banco Mercantil": 4,
    "Banco Union": 5
}


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
# --- ENDPOINTS ---

@integracion_bp.route('/sincronizar-lote', methods=['POST'])
def sincronizar_lote():
    client = None
    try:
        body = request.get_json() or {}
        
        # 1. Ahora extraemos el nombre del banco
        nombre_banco = body.get('nombre_banco')

        if not nombre_banco:
            return jsonify({"error": "Falta el 'nombre_banco' en el cuerpo de la petición"}), 400

        # 2. Buscamos el ID interno usando el diccionario
        id_banco = MAPEO_BANCOS.get(nombre_banco)
        
        # Si envían un banco que no está en la lista, rechazamos la petición
        if not id_banco:
            return jsonify({"error": f"El banco '{nombre_banco}' no está registrado en el sistema"}), 404

        # --- A partir de aquí, la lógica sigue usando id_banco como antes ---
        estado = cargar_estado()
        clave_offset = f"offset_banco_{id_banco}"
        offset = estado.get(clave_offset, 0)
        nro_lote_actual = calcular_nro_lote(offset)
        limit = 10

        client = MongoClient(current_app.config['MONGO_URI'])
        db = client[current_app.config['DB_NAME']]
        coleccion = db.perfiles_centralizados

        tienda_data = cargar_datos_tienda(dias_relevancia=30)
        
        nombre_archivo = f'dataset_banco{id_banco}.csv'
        path_banco = os.path.join(current_app.root_path, '..', 'data', nombre_archivo)
        
        if not os.path.exists(path_banco):
            return jsonify({"error": f"Archivo {nombre_archivo} no encontrado"}), 404

        with open(path_banco, mode='r', encoding='utf-8') as file:
            primera_linea = file.readline()
            delimitador = ';' if ';' in primera_linea else ','
            file.seek(0)
            
            reader = list(csv.DictReader(file, delimiter=delimitador, skipinitialspace=True))

        lote_csv = reader[offset:offset + limit]
        
        if not lote_csv:
            return jsonify({"status": "fin", "mensaje": f"No hay más datos para {nombre_banco}"}), 200

        perfiles_enriquecidos = []

        for row in lote_csv:
            row_limpia = {str(k).strip(): v for k, v in row.items() if k is not None}
            
            carnet_cliente = row_limpia.get('carnet')
            if carnet_cliente:
                carnet_cliente = str(carnet_cliente).strip()
                
            if not carnet_cliente or carnet_cliente == "": 
                continue

            historial_tienda = tienda_data.get(carnet_cliente, [])
            for item in historial_tienda:
                item.pop('carnet', None)
                item.pop('nombre_completo', None)
                item.pop('customer_id', None)

            datos_banco_raw = dict(row_limpia)
            nombre = datos_banco_raw.pop('nombre_completo', 'Sin Nombre')
            
            # 3. Usamos el nombre real del banco para guardarlo en la base de datos
            entidad = nombre_banco 
            datos_banco_raw.pop('carnet', None)

            perfil_360 = {
                "identidad": {
                    "nombre_completo": nombre,
                    "carnet": carnet_cliente,
                    "entidad_origen": entidad, # Guarda "Banco Free" en lugar de "Banco 1"
                    "id_tenant": id_banco
                },
                "datos_banco_raw": datos_banco_raw,
                "datos_tienda_raw": historial_tienda,
                "metadata": {
                    "estado": "ingestado_crudo",
                    "fecha_sincronizacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "num_interacciones_tienda": len(historial_tienda),
                    "nro_lote": nro_lote_actual 
                }
            }
            perfiles_enriquecidos.append(perfil_360)

        for perfil in perfiles_enriquecidos:
            coleccion.update_one(
                {"identidad.carnet": perfil['identidad']['carnet']},
                {"$set": perfil},
                upsert=True
            )

        estado[clave_offset] = offset + limit
        guardar_estado(estado)

        return jsonify({
            "status": "success",
            "mensaje": f"Lote {nro_lote_actual} de {nombre_banco} procesado con éxito",
            "registros_procesados": len(perfiles_enriquecidos),
            "registros": perfiles_enriquecidos
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    finally:
        if client: client.close()

@integracion_bp.route('/obtener-lote', methods=['GET'])
def obtener_lote_db():
    """
    Obtiene los registros de un lote específico para un banco específico.
    Uso: /obtener-lote?id_banco=1&nro=1
    """
    client = None
    try:
        # --- SOLUCIÓN DEL GET: Leer el tenant correcto ---
        id_banco = request.args.get('id_banco', default=1, type=int)
        
        estado = cargar_estado()
        clave_offset = f"offset_banco_{id_banco}"
        offset_actual = estado.get(clave_offset, 0)
        nro_lote_defecto = max(1, calcular_nro_lote(offset_actual) - 1)
        
        nro_a_buscar = request.args.get('nro', default=nro_lote_defecto, type=int)

        client = MongoClient(current_app.config['MONGO_URI'])
        db = client[current_app.config['DB_NAME']]
        coleccion = db.perfiles_centralizados

        # Buscamos por nro_lote Y por id_tenant para no mezclar datos de distintos bancos
        registros = list(coleccion.find(
            {
                "metadata.nro_lote": nro_a_buscar,
                "identidad.id_tenant": id_banco
            }
        ))

        for r in registros:
            r['_id'] = str(r['_id'])

        return jsonify({
            "status": "success",
            "banco": id_banco,
            "lote_nro": nro_a_buscar,
            "cantidad": len(registros),
            "registros": registros
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500
    finally:
        if client: client.close()