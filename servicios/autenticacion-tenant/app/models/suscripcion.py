import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class Suscripcion(db.Model):
    __tablename__ = "suscripciones"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id = db.Column(UUID(as_uuid=True), db.ForeignKey("instituciones.id", ondelete="CASCADE"), nullable=False)
    plan_id = db.Column(UUID(as_uuid=True), db.ForeignKey("planes.id", ondelete="CASCADE"), nullable=False)
    estado = db.Column(db.String(50), nullable=False, default="activo")
    
    institucion = db.relationship("Institucion", backref="suscripciones")
    plan = db.relationship("Plan", backref="suscripciones")