from flask import Flask
from .config import Config
from .extensions import db, migrate, cors
from .routes.health import health_bp
from .routes.dataset import dataset_bp
from .routes.lote import lote_bp
from .routes.perfil import perfil_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(dataset_bp, url_prefix="/api")
    app.register_blueprint(lote_bp, url_prefix="/api")
    app.register_blueprint(perfil_bp, url_prefix="/api")

    return app