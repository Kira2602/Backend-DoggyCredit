from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import PerfilCliente, DatosFinancieros, Institucion
from ..services import DatasetParser
import logging

dataset_bp = Blueprint('dataset', __name__)
logger = logging.getLogger(__name__)


@dataset_bp.route('/upload-dataset', methods=['POST'])
def upload_dataset():
    """
    POST /api/upload-dataset
    Recibe un archivo CSV/XLSX con datos de clientes
    Parsea, valida y mapea a los modelos (perfiles_clientes, datos_financieros)
    """
    try:
        # Validar que venga archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Validar que venga institucion_id
        institucion_id = request.form.get('institucion_id')
        if not institucion_id:
            return jsonify({'error': 'institucion_id required'}), 400
        
        # Verificar que la institución existe
        institucion = Institucion.query.get(institucion_id)
        if not institucion:
            return jsonify({'error': 'Institution not found'}), 404
        
        # Parsear archivo
        file_content = file.read()
        df = DatasetParser.parse_file(file_content, file.filename)
        
        # Validar columnas
        is_valid, missing_cols = DatasetParser.validate_columns(df)
        if not is_valid:
            return jsonify({
                'error': 'Invalid columns',
                'missing_columns': missing_cols
            }), 400
        
        # Mapear datos
        perfiles_data, datos_fin_data = DatasetParser.map_to_models(df, institucion_id)
        
        # Guardar en BD
        try:
            insertados_perfiles = 0
            insertados_datos = 0
            actualizados_perfiles = 0
            actualizados_datos = 0
            
            for perfil_data in perfiles_data:
                perfil_existente = PerfilCliente.query.filter_by(
                    documento_id=perfil_data['documento_id'],
                    id_institucion=institucion_id
                ).first()
                
                if perfil_existente:
                    # Actualizar
                    for key, value in perfil_data.items():
                        if key not in ['documento_id', 'id_institucion']:
                            setattr(perfil_existente, key, value)
                    actualizados_perfiles += 1
                else:
                    # Crear nuevo
                    perfil = PerfilCliente(**perfil_data)
                    db.session.add(perfil)
                    insertados_perfiles += 1
            
            db.session.commit()
            
            # Guardar datos financieros
            for datos_data in datos_fin_data:
                datos_existentes = DatosFinancieros.query.filter_by(
                    documento_id=datos_data['documento_id']
                ).first()
                
                if datos_existentes:
                    # Actualizar versión
                    datos_existentes.version_data = (datos_existentes.version_data or 0) + 1
                    for key, value in datos_data.items():
                        if key != 'documento_id':
                            setattr(datos_existentes, key, value)
                    actualizados_datos += 1
                else:
                    # Crear nuevo
                    datos = DatosFinancieros(**datos_data)
                    db.session.add(datos)
                    insertados_datos += 1
            
            db.session.commit()
            
            return jsonify({
                'message': 'Dataset uploaded successfully',
                'institucion_id': institucion_id,
                'perfiles': {
                    'insertados': insertados_perfiles,
                    'actualizados': actualizados_perfiles
                },
                'datos_financieros': {
                    'insertados': insertados_datos,
                    'actualizados': actualizados_datos
                },
                'total_registros': len(perfiles_data)
            }), 201
        
        except Exception as db_error:
            db.session.rollback()
            logger.error(f"Database error: {str(db_error)}")
            return jsonify({'error': f'Database error: {str(db_error)}'}), 500
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
