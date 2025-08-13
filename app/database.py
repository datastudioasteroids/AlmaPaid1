# app/database.py
"""
Inicialización del engine/Session/Meta para la app.
Prioriza SQLite (archivo alma_paid.db en la raíz del repo) salvo que
se indique explícitamente usar Postgres vía USE_POSTGRES=1 y DATABASE_URL.
"""

import os
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import SQLALCHEMY_ENGINE_OPTIONS, SQLALCHEMY_DATABASE_URI

# Ruta base del repo (un nivel arriba de app/)
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

# Flags de control de comportamiento (entorno)
USE_POSTGRES = os.getenv("USE_POSTGRES", "0").lower() in ("1", "true", "yes")
FORCE_SQLITE = os.getenv("FORCE_SQLITE", "0").lower() in ("1", "true", "yes")

# Default sqlite path (archivo incluido en el repo)
DEFAULT_SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "alma_paid.db"))
DEFAULT_SQLITE_URI = f"sqlite:///{DEFAULT_SQLITE_PATH}"

# Lógica para elegir URI:
# - Si FORCE_SQLITE está activo, usamos sqlite independientemente de DATABASE_URL
# - Si USE_POSTGRES está activo y DATABASE_URL está presente, usamos DATABASE_URL
# - Si no, usamos la URI de config (que debería caer en sqlite si no hay DATABASE_URL)
env_db = os.getenv("DATABASE_URL", "").strip()

if FORCE_SQLITE:
    DATABASE_URL = DEFAULT_SQLITE_URI
elif USE_POSTGRES and env_db:
    DATABASE_URL = env_db
elif env_db and env_db.startswith("sqlite"):
    # si el env var ya apunta a sqlite, respetarlo
    DATABASE_URL = env_db
else:
    # fallback a la configuración (config.py puede usar DATABASE_URL o sqlite por defecto)
    DATABASE_URL = SQLALCHEMY_DATABASE_URI or DEFAULT_SQLITE_URI

# Engine (pasa las engine options definidas en config)
engine = create_engine(DATABASE_URL, **(SQLALCHEMY_ENGINE_OPTIONS or {}))

# Declarative base y session factory
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DEBUG: imprime la DB que se está usando (ver logs de Render)
try:
    print(f"[database] Usando DB -> driver: {engine.url.drivername}, url: {str(engine.url)}")
except Exception:
    print("[database] Usando DB (no se pudo mostrar URL completa por seguridad).")



