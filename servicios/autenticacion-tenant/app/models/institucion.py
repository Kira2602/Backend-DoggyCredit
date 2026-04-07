import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class Institucion(db.Model):
    __tablename__ = "instituciones"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    nombre = db.Column(db.String(150), nullable=False)
    tipo_institucion = db.Column(db.String(100))
    email = db.Column(db.String(150))
    telefono = db.Column(db.String(30))
    estado = db.Column(db.String(20), nullable=False, default="activo")

    usuarios = db.relationship("Usuario", backref="institucion", lazy=True, cascade="all, delete-orphan")