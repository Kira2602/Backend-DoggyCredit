from flask import Flask
from .config import Config
from .extensions import cors
from .routes.health import health_bp
from .routes.integracion import integracion_bp
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    
    cors.init_app(app)


    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(integracion_bp, url_prefix="/api")

    return app