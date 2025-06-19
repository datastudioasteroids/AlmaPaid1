# app/main.py

import os
import subprocess
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine
from . import models          # Asegura que los modelos se registren en Base
from .routes import landing, admin
from .auth import router as auth_router

# 1) Ejecutar migraciones pendientes
migrate_script = os.path.join(os.getcwd(), "migrate.py")
if os.path.isfile(migrate_script):
    try:
        subprocess.run(
            ["python", migrate_script],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("✅ Migraciones ejecutadas correctamente.")
    except subprocess.CalledProcessError as e:
        print("❌ Error al ejecutar migraciones:")
        print(e.stdout)
        print(e.stderr)
        raise RuntimeError(f"Migración fallida (ver logs arriba)")

# 2) Crear tablas nuevas (no toca columnas existentes)
Base.metadata.create_all(bind=engine)
print("✅ Base.metadata.create_all() completado.")

app = FastAPI()

# 3) Middleware de sesiones (necesario para autenticación en /admin)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "CAMBIÁ_ESTA_CLAVE_POR_ALGO_AZAR")
)

# 4) Archivos estáticos (CSS, JS, imágenes, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 5) Registrar routers
app.include_router(landing.router)
app.include_router(auth_router)
app.include_router(admin.router)

@app.get("/", include_in_schema=False)
async def root_redirect():
    return {"message": "Visita / para ir a la página principal de AlmaPaid."}




