from .extensions import db
from datetime import datetime

class Score(db.Model):
    __tablename__ = 'scores'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    # Relación lógica con el microservicio de perfilamiento
    documento_id = db.Column(db.String(50), nullable=False, index=True)
    # Identificador de la Fintech/Banco (Tenant)
    tenant_id = db.Column(db.String(36), nullable=False, index=True)
    
    scoring = db.Column(db.Float, nullable=False)
    # False = Básico (Reglas), True = Avanzado (IA)
    tipo_plan = db.Column(db.Boolean, default=False)
    
    # Campos específicos para el modelo de ML
    probabilidad_default = db.Column(db.Numeric(5, 4)) # E.g., 0.1234
    nivel_riesgo = db.Column(db.String(20)) # 'Bajo', 'Medio', 'Alto'
    
    fecha = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relación con las recomendaciones
    recomendaciones = db.relationship('Recomendacion', backref='score_rel', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Score {self.scoring} for {self.documento_id}>'


class Recomendacion(db.Model):
    __tablename__ = 'recomendacion'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    score_id = db.Column(db.BigInteger, db.ForeignKey('scores.id'), nullable=False)
    
    # Categorías: 'Microcrédito', 'Ecológico', 'PYME'
    categoria = db.Column(db.String(100), nullable=False)
    # Probabilidad de que el cliente acepte o necesite el producto
    probabilidad = db.Column(db.Numeric(5, 4))
    
    # Justificación generada por la IA para el dashboard
    insight_ia = db.Column(db.Text)

    def __repr__(self):
        return f'<Recomendacion {self.categoria} for Score {self.score_id}>'