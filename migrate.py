# migrate.py
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from app.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS

# crear engine con las opciones definidas en config
engine = create_engine(SQLALCHEMY_DATABASE_URI, **(SQLALCHEMY_ENGINE_OPTIONS or {}))

# ejemplo de bind del metadata o creación de sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData(bind=engine)

if __name__ == "__main__":
    # prueba simple: listar tablas
    print("URI actual:", SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print("Tablas:", [r[0] for r in result.fetchall()])
