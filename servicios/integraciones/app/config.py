import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATASET_PATH = os.path.join(os.getcwd(), 'data', 'banco_datos.csv')
    SERVICE_NAME = os.getenv("SERVICE_NAME", "service")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DB_NAME = 'integraciones'
    DEBUG = True