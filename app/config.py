# app/config.py
import os

# Directorio base (carpeta raíz del repo)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Path al archivo sqlite incluido en el repo
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "alma_paid.db")

# URI: primero intenta leer env var DATABASE_URL (por compatibilidad),
# si no existe usa la DB sqlite local (archivo en el repo)
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{DEFAULT_SQLITE_PATH}"

# Opciones recomendadas para SQLite con SQLAlchemy
# check_same_thread False es necesario si usas threads (gunicorn/uvicorn)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}

# Otros settings que puedas necesitar
DEBUG = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
SECRET_KEY = os.getenv("SECRET_KEY", "cámbiala_por_una_secreta_en_producción")
