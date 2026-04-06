from flask import Flask
from .config import Config
from .extensions import db, migrate, cors
from .routes.health import health_bp
from .routes.db_test import db_test_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(db_test_bp, url_prefix="/api")

    return app