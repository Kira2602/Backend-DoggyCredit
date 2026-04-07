import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class UsuarioRol(db.Model):
    __tablename__ = "usuarios_roles"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column(UUID(as_uuid=True), db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    rol_id = db.Column(UUID(as_uuid=True), db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "rol_id", name="uq_usuario_rol"),
    )

    rol = db.relationship("Rol")