# app/deps.py

from fastapi import Request
from fastapi.responses import RedirectResponse
from .database import SessionLocal

def get_db():
    """
    Abre una sesión de DB usando SessionLocal (que ya apunta a Postgres).
    La cede (yield) para que FastAPI la injete en dependencias, y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_admin(request: Request):
    """
    Comprueba si existe request.session['admin'].
    - Si no existe, redirige a /login.
    - Si existe, devuelve el valor (por ejemplo, el email del admin).
    """
    admin_user = request.session.get("admin")
    if not admin_user:
        return RedirectResponse(url="/login", status_code=302)
    return admin_user

