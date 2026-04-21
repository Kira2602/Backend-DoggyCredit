# app/models.py
from .extensions import db
from datetime import datetime

class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Text, nullable=False)
    documento_id = db.Column(db.String, nullable=False)
    scoring = db.Column(db.Float, nullable=False)
    tipo_plan = db.Column(db.Boolean, default=False)
    probabilidad_default = db.Column(db.Numeric)
    nivel_riesgo = db.Column(db.Text)
    fecha = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relación opcional para acceder a recomendaciones desde el score
    recomendaciones = db.relationship('Recomendacion', backref='score', lazy=True)

class Recomendacion(db.Model):
    __tablename__ = 'recomendacion'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    score_id = db.Column(db.BigInteger, db.ForeignKey('scores.id'), nullable=False)
    categoria = db.Column(db.Text, nullable=False)
    probabilidad_afinidad = db.Column(db.Numeric)