import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institucion_id = db.Column(UUID(as_uuid=True), db.ForeignKey("instituciones.id", ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="activo")

    roles = db.relationship("UsuarioRol", backref="usuario", lazy=True, cascade="all, delete-orphan")