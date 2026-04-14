import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class Plan(db.Model):
    __tablename__ = "planes"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(100), nullable=False, unique=True)