# app/main.py
import os
import subprocess
import sys
import traceback
import importlib.util

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine
from . import models          # Asegura que los modelos se registren en Base
from .routes import landing, admin
from .auth import router as auth_router

app = FastAPI()

# ---------- 1) Ejecutar migraciones pendientes (intento principal + fallback) ----------
migrate_script = os.path.join(os.getcwd(), "migrate.py")
migration_ok = False

if os.path.isfile(migrate_script):
    print(f"🔎 Se encontró migrate.py en: {migrate_script}")
    # Intento con subprocess (no levantar excepción automática)
    try:
        proc = subprocess.run(
            [sys.executable, migrate_script],
            capture_output=True,
            text=True,
            check=False
        )
        print("---- salida stdout de migrate.py ----")
        print(proc.stdout or "<vacío>")
        print("---- salida stderr de migrate.py ----")
        print(proc.stderr or "<vacío>")
        if proc.returncode == 0:
            print("✅ Migraciones ejecutadas correctamente (subprocess).")
            migration_ok = True
        else:
            print(f"⚠️ migrate.py retornó código {proc.returncode}. Intentando fallback importando el módulo migrate.py ...")
    except Exception:
        print("❌ Error ejecutando migrate.py via subprocess:")
        print(traceback.format_exc())

    # Fallback: intentar importar migrate.py y llamar a funciones (get_engine/listar_tablas)
    if not migration_ok:
        try:
            spec = importlib.util.spec_from_file_location("migrate", migrate_script)
            migrate = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migrate)
            print("🔁 migrate.py importado. Intentando usar migrate.get_engine() y migrate.listar_tablas() ...")
            try:
                eng = migrate.get_engine()
            except AttributeError:
                eng = None
            if eng is not None:
                tablas = migrate.listar_tablas(eng)
                print("✅ Fallback: tablas encontradas:", tablas)
                migration_ok = True
            else:
                # Si migrate no provee get_engine, aún puede exponer una función principal
                if hasattr(migrate, "__main__") or hasattr(migrate, "main"):
                    # intentar llamar main() si existe
                    try:
                        if hasattr(migrate, "main"):
                            migrate.main()
                        else:
                            # no hay main, no hacemos nada
                            pass
                        migration_ok = True
                        print("✅ Fallback: migrate.main() ejecutado.")
                    except Exception:
                        print("❌ Fallback: migrate.main() falló:")
                        print(traceback.format_exc())
                else:
                    print("⚠️ Fallback no pudo determinar engine ni main en migrate.py.")
        except Exception:
            print("❌ Error importando/ejecutando migrate.py como módulo:")
            print(traceback.format_exc())
else:
    print("ℹ️ No se encontró migrate.py; se omite paso de migraciones.")

# ---------- 2) Crear tablas nuevas (no toca columnas existentes) ----------
# Si migrate falló, seguiremos, pero si create_all falla, ahí sí abortamos
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Base.metadata.create_all() completado.")
except Exception:
    print("❌ Error en Base.metadata.create_all():")
    print(traceback.format_exc())
    # Es razonable detener aquí porque sin DB funcional la app no puede levantar
    raise RuntimeError("Error creando tablas en la base de datos (ver logs arriba).")

# ---------- 3) Middleware de sesiones (necesario para autenticación en /admin) ----------
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "CAMBIÁ_ESTA_CLAVE_POR_ALGO_AZAR")
)

# ---------- 4) Archivos estáticos (CSS, JS, imágenes, etc.) ----------
# asegurarse que la carpeta exista o StaticFiles fallará al arrancar
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(static_dir):
    print(f"⚠️ static directory no encontrado en {static_dir} — verifica la ruta.")
else:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print(f"📂 Montado /static -> {static_dir}")

# ---------- 5) Registrar routers ----------
app.include_router(landing.router)
app.include_router(auth_router)
app.include_router(admin.router)

@app.get("/", include_in_schema=False)
async def root_redirect():
    return {"message": "Visita / para ir a la página principal de AlmaPaid."}



