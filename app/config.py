# app/config.py
import os
import toml

# Intentamos cargar un secrets.toml; si no existe, pasamos a variables de entorno
try:
    _conf = toml.load(os.path.join(os.path.dirname(__file__), "..", "secrets.toml"))
except FileNotFoundError:
    _conf = {}

MP_ACCESS_TOKEN = _conf.get("MP_ACCESS_TOKEN") or os.getenv("MP_ACCESS_TOKEN", "")
CBU_ALIAS       = _conf.get("CBU_ALIAS")       or os.getenv("CBU_ALIAS", "")
BASE_URL        = _conf.get("BASE_URL")        or os.getenv("BASE_URL", "http://localhost:8000")