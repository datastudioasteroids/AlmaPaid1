# migrate.py
"""
Migraciones mínimas y seguras para sqlite del repo AlmaPaid1.

Qué hace:
- hace backup del archivo sqlite (si existe)
- importa los modelos (app.models) para poblar Base.metadata
- por cada tabla en metadata:
    - obtiene columnas actuales via PRAGMA table_info(table)
    - detecta columnas faltantes respecto a metadata
    - ejecuta ALTER TABLE ADD COLUMN ... para cada columna faltante
Nota: ALTER TABLE ADD COLUMN en SQLite solo permite añadir columnas; no permite eliminar o renombrar.
Si necesitas migraciones más complejas, usa alembic o manual SQL fuera de este script.
"""
import os
import shutil
import pathlib
import datetime
import traceback

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import SQLAlchemyError

# IMPORTS DEPENDIENTES DEL PROYECTO
# Asegúrate de que app.database y app.models se resuelvan correctamente desde la raíz del proyecto.
try:
    # importa configuración y Base/engine si las tienes definidas ahí
    from app.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS
    from app.database import Base  # Base declarative (si tu repo lo tiene)
except Exception as e:
    # Si la estructura es distinta, intenta importarlas de otra forma o fallar con mensaje claro.
    print("Error importando app.config/app.database:", e)
    raise

def get_engine():
    opts = SQLALCHEMY_ENGINE_OPTIONS or {}
    engine = create_engine(SQLALCHEMY_DATABASE_URI, **opts)
    return engine

def backup_sqlite(db_path: str):
    try:
        if os.path.isfile(db_path):
            fname = pathlib.Path(db_path).name
            ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            backup_name = f"{fname}.backup.{ts}"
            backup_path = pathlib.Path(db_path).with_name(backup_name)
            shutil.copy2(db_path, backup_path)
            print(f"Backup creado: {backup_path}")
            return str(backup_path)
        else:
            print("No existe el archivo sqlite para backup:", db_path)
            return None
    except Exception:
        print("Error creando backup:")
        print(traceback.format_exc())
        raise

def get_existing_columns(conn, table_name: str):
    """Devuelve set de nombres de columnas existentes en la tabla (sqlite PRAGMA)."""
    q = text(f"PRAGMA table_info('{table_name}')")
    res = conn.execute(q).all()
    # PRAGMA table_info returns rows: cid, name, type, notnull, dflt_value, pk
    return {row[1] for row in res}

def map_sqla_type_to_sqlite(col):
    """
    Map simple de tipos SQLAlchemy a tipos SQLite para ADD COLUMN.
    col: sqlalchemy Column object
    """
    typename = type(col.type).__name__.lower()
    # heurística simple
    if "integer" in typename or "int" in typename:
        return "INTEGER"
    if "float" in typename or "numeric" in typename or "decimal" in typename:
        return "REAL"
    if "bool" in typename:
        return "INTEGER"
    if "date" in typename and "time" in typename:
        return "TEXT"
    if "date" in typename or "time" in typename:
        return "TEXT"
    if "string" in typename or "char" in typename or "text" in typename or "varchar" in typename:
        return "TEXT"
    # fallback
    return "TEXT"

def add_column_sqlite(conn, table_name: str, col_name: str, col_type_sql: str, nullable=True, default=None):
    """
    Ejecuta ALTER TABLE ADD COLUMN para sqlite.
    Si default es None y nullable is False, añadimos DEFAULT '' para evitar error.
    """
    # construimos la definición
    parts = [f'"{col_name}"', col_type_sql]
    if not nullable:
        # SQLite requires a default when adding NOT NULL column; mejor forzar NULLABLE en migración
        parts.append("NULL")
    if default is not None:
        # default as literal
        parts.append(f"DEFAULT {default}")
    sql = f'ALTER TABLE "{table_name}" ADD COLUMN ' + " ".join(parts) + ";"
    print("Ejecutando:", sql)
    conn.execute(text(sql))

def run_migrations():
    print("Starting migration script...")
    engine = get_engine()

    # si es sqlite file, hacemos backup
    url = str(engine.url)
    if url.startswith("sqlite:///") or url.startswith("sqlite:////"):
        # obtener path físico del archivo sqlite
        # engine.url.database puede devolver path
        db_path = engine.url.database
        print("DB sqlite detectada en:", db_path)
        backup_sqlite(db_path)
    else:
        print("DB no es sqlite (url):", url)
        # aún así intentamos correr checks contra la DB en el engine

    # IMPORTAR modelos para poblar metadata
    # Importante: el import debe ejecutar definiciones de modelos que registran en Base
    try:
        import app.models as _models_module  # solo para poblar Base.metadata
        print("app.models importado.")
    except Exception:
        print("Aviso: no se pudo importar app.models. Asegurate que el módulo exista y no falle en import.")
        print(traceback.format_exc())

    # asegurarse de que metadata tenga las tablas de models
    metadata: MetaData = Base.metadata
    if not metadata.tables:
        print("Warning: Base.metadata.tables está vacío. Verifica que app.models defina clases ORM y las importe correctamente.")
    else:
        print("Tablas definidas en metadata:", list(metadata.tables.keys()))

    # Abrir conexión y revisar por tabla
    with engine.connect() as conn:
        for table in metadata.sorted_tables:
            tname = table.name
            print(f"\n---- Procesando tabla: {tname} ----")
            try:
                existing_cols = get_existing_columns(conn, tname)
                print("Columnas existentes:", existing_cols)
            except SQLAlchemyError:
                print(f"Error consultando PRAGMA table_info para {tname}. Quizá la tabla no existe aún.")
                existing_cols = set()

            # por cada columna en la metadata revisar existencia
            for col in table.columns:
                cname = col.name
                if cname in existing_cols:
                    continue  # ya existe
                # decidir tipo sqlite
                col_type_sql = map_sqla_type_to_sqlite(col)
                nullable = col.nullable
                # si la columna tiene default en server_default, intentar usarlo (cuidado con tipos)
                default = None
                if col.server_default is not None:
                    # servidor default puede ser SQL expression; para simplicidad lo omitimos o lo convertimos a literal si es simple
                    try:
                        default_val = str(col.server_default.arg)
                        # envolvemos en comillas si parece texto
                        if not default_val.isnumeric():
                            default = f"'{default_val.strip(\"'\")}'"
                        else:
                            default = default_val
                    except Exception:
                        default = None

                # For safety, add new columns as NULLABLE (SQLite permits it)
                try:
                    print(f"--> Columna faltante detectada: {cname} (type {col_type_sql}) - agregando...")
                    add_column_sqlite(conn, tname, cname, col_type_sql, nullable=True, default=default)
                    print(f"  OK: columna {cname} agregada a {tname}.")
                except Exception:
                    print(f"  ERROR al añadir columna {cname} a {tname}:")
                    print(traceback.format_exc())

        # opcional: listar tablas finales
        try:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            print("Tablas finales en DB:", [r[0] for r in res.fetchall()])
        except Exception:
            print("No se pudo listar tablas al final de migración.")
    print("Migración finalizada.")

if __name__ == "__main__":
    run_migrations()

