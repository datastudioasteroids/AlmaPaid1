# migrate.py
"""
Script mínimo y seguro que asegura que la columna `last_paid_date` exista en la tabla `students`.
Idempotente: si la columna ya existe no hace nada.
Hace backup del archivo sqlite antes de modificarlo.
"""

import os
import shutil
import datetime
import traceback
import pathlib

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Intentar importar la configuración SQLALCHEMY_DATABASE_URI y opciones
try:
    from app.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS
except Exception:
    # Fallback: intentar leer DATABASE_URL de env si config no existe
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_ENGINE_OPTIONS = {}

def get_engine():
    opts = SQLALCHEMY_ENGINE_OPTIONS or {}
    engine = create_engine(SQLALCHEMY_DATABASE_URI, **opts)
    return engine

def backup_sqlite_if_file(engine):
    try:
        url = str(engine.url)
        if url.startswith("sqlite:///") or url.startswith("sqlite:////"):
            db_path = engine.url.database
            if db_path and os.path.isfile(db_path):
                ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                p = pathlib.Path(db_path)
                backup = p.with_name(p.name + f".backup.{ts}")
                shutil.copy2(p, backup)
                print(f"[migrate] Backup creado: {backup}")
                return str(backup)
            else:
                print(f"[migrate] No existe archivo sqlite en: {db_path}")
        else:
            print(f"[migrate] Engine no es sqlite (url={url}), no se hace backup de archivo).")
    except Exception:
        print("[migrate] Error creando backup:")
        print(traceback.format_exc())
    return None

def pragma_table_info(conn, table_name):
    q = text(f"PRAGMA table_info('{table_name}')")
    try:
        res = conn.execute(q).all()
        return {row[1] for row in res}  # row[1] es el nombre de la columna
    except Exception:
        return set()

def add_column_if_missing(conn, table_name, column_name, column_type_sql="TEXT"):
    existing = pragma_table_info(conn, table_name)
    print(f"[migrate] Columnas existentes en `{table_name}`: {existing}")
    if column_name in existing:
        print(f"[migrate] La columna `{column_name}` ya existe en `{table_name}`. Nada que hacer.")
        return False
    # construir SQL seguro y ejecutarlo
    sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_type_sql};'
    print(f"[migrate] Ejecutando: {sql}")
    try:
        conn.execute(text(sql))
        print(f"[migrate] Columna `{column_name}` agregada a `{table_name}` correctamente.")
        return True
    except Exception:
        print(f"[migrate] ERROR al agregar columna `{column_name}` a `{table_name}`:")
        print(traceback.format_exc())
        raise

def main():
    print("[migrate] Iniciando migrate.py")
    engine = get_engine()
    try:
        print(f"[migrate] Engine URL: {engine.url}")
    except Exception:
        print("[migrate] Engine creada (no se pudo mostrar URL).")

    backup_sqlite_if_file(engine)

    with engine.connect() as conn:
        # Aseguramos solo la columna que está dando problemas
        table = "students"
        col = "last_paid_date"
        try:
            added = add_column_if_missing(conn, table, col, column_type_sql="TEXT")
            if added:
                print(f"[migrate] Migración: la columna `{col}` fue añadida.")
            else:
                print(f"[migrate] Migración: no hubo cambios para `{col}`.")
        except SQLAlchemyError:
            print("[migrate] Error SQL al intentar migración (ver arriba).")
            raise
        except Exception:
            print("[migrate] Error inesperado (ver traza):")
            print(traceback.format_exc())
            raise
    print("[migrate] Fin.")

if __name__ == "__main__":
    main()
