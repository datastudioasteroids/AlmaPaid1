# migrate.py

import os
from sqlalchemy import create_engine, text

# 1) URL de Render (por ENV o fallback)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://almapaid_user:7iXZmLPXzDBuDg9u8Lxa5O8xWkELLvg7@dpg-d11bhhumcj7s73a2g1og-a.oregon-postgres.render.com/almapaid"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

migrations = [
    # Añadir columna description a courses
    ("courses", "description TEXT DEFAULT ''"),
    # Añadir columna last_paid_date a students
    ("students", "last_paid_date TIMESTAMP")
]

with engine.connect() as conn:
    for table, ddl in migrations:
        try:
            sql = text(f"ALTER TABLE {table} ADD COLUMN {ddl};")
            conn.execute(sql)
            print(f"✅ Columna añadida: {table}.{ddl.split()[0]}")
        except Exception as e:
            # Si ya existe, se ignora
            print(f"⚠️ No se pudo añadir {table}.{ddl.split()[0]} (quizá ya existe): {e}")

    # Finalmente, crear tablas nuevas si faltan
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Base.metadata.create_all() ejecutado correctamente.")
