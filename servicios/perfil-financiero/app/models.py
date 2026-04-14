from .extensions import db
from datetime import datetime

class Institucion(db.Model):
    __tablename__ = 'instituciones'
    
    id = db.Column(db.String(36), primary_key=True)
    nombre_fintech = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f'<Institucion {self.nombre_fintech}>'


class PerfilCliente(db.Model):
    __tablename__ = 'perfiles_clientes'
    
    documento_id = db.Column(db.String(50), primary_key=True)
    id_institucion = db.Column(db.String(36), db.ForeignKey('instituciones.id'), nullable=False)
    nombre_completo = db.Column(db.String(255), nullable=False)
    edad = db.Column(db.Integer)
    educacion = db.Column(db.String(50))
    estado_civil = db.Column(db.String(50))
    sex = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    institucion = db.relationship('Institucion', backref='clientes')
    datos_financieros = db.relationship('DatosFinancieros', backref='cliente', uselist=False)
    
    def __repr__(self):
        return f'<PerfilCliente {self.documento_id}>'


class DatosFinancieros(db.Model):
    __tablename__ = 'datos_financieros_limpios'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento_id = db.Column(db.String(50), db.ForeignKey('perfiles_clientes.documento_id'), nullable=False)
    promedio_pay = db.Column(db.Numeric(15, 2))
    promedio_bill = db.Column(db.Numeric(15, 2))
    limit_bal = db.Column(db.Numeric(15, 2))
    comportamiento_pagos = db.Column(db.JSON)  # [PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6]
    riesgo_default = db.Column(db.Integer)  # 0 o 1
    version_data = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DatosFinancieros {self.documento_id}>'


class AnalisisNecesidades(db.Model):
    __tablename__ = 'analisis_necesidades'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento_id = db.Column(db.String(50), nullable=False)
    etiqueta_interes = db.Column(db.String(255))
    fuente_data = db.Column(db.String(255))
    fecha_deteccion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalisisNecesidades {self.documento_id}>'


class MetricasFinancieras(db.Model):
    __tablename__ = 'metricas_financieras'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento_id = db.Column(db.String(50), db.ForeignKey('perfiles_clientes.documento_id'), nullable=False)
    ratio_utilizacion = db.Column(db.Numeric(5, 2))
    ratio_pago = db.Column(db.Numeric(5, 2))
    ciclo_deuda = db.Column(db.Numeric(15, 2))
    volatilidad_gastos = db.Column(db.Numeric(5, 2))
    tendencia_pagos = db.Column(db.Integer)  # -1, 0, 1
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MetricasFinancieras {self.documento_id}>'


class AlertasCliente(db.Model):
    __tablename__ = 'alertas_cliente'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento_id = db.Column(db.String(50), db.ForeignKey('perfiles_clientes.documento_id'), nullable=False)
    tipo_alerta = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    severidad = db.Column(db.String(20))  # info, warning, critical
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AlertasCliente {self.documento_id}>'
