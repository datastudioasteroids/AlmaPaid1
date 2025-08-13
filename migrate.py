# migrate.py
"""
Script simple de migración/prueba para conectarse a la DB y listar tablas.
Compatible con SQLAlchemy 1.x y 2.x (forma recomendada para 2.x).
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
from app.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS

def get_engine():
    opts = SQLALCHEMY_ENGINE_OPTIONS or {}
    # create_engine aceptará kwargs vacíos si opts == {}
    engine = create_engine(SQLALCHEMY_DATABASE_URI, **opts)
    return engine

def get_session(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def listar_tablas(engine):
    metadata = MetaData()  # NO usar bind=engine
    # opcional: metadata.reflect(bind=engine)  # si quieres poblar metadata
    with engine.connect() as conn:
        # usar text() para compatibilidad con SQLAlchemy 2.x
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tablas = [row[0] for row in result.fetchall()]
    return tablas

if __name__ == "__main__":
    engine = get_engine()
    SessionLocal = get_session(engine)
    print("Usando URI:", SQLALCHEMY_DATABASE_URI)
    try:
        tablas = listar_tablas(engine)
        print("Tablas encontradas:", tablas)
    except Exception as e:
        print("Error al listar tablas:", e)
        raise
