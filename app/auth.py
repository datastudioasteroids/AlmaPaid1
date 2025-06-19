# app/auth.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_get(request: Request):
    """
    Muestra el formulario de login.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_post(request: Request, 
               username: str = Form(...), 
               password: str = Form(...)):
    """
    Procesa el formulario de login. Si las credenciales coinciden, guarda en la sesión 
    request.session["admin"] = username, y redirige a /admin. 
    En caso contrario, vuelve a mostrar login con mensaje de error.
    """
    # Reemplazá estas credenciales con las tuyas:
    ADMIN_USER = "gravinadavilafederico@gmail.com"
    ADMIN_PASS = "@Apolito213"

    if username == ADMIN_USER and password == ADMIN_PASS:
        # Guardamos en la sesión que este usuario está autenticado
        request.session["admin"] = username
        # Redirigimos al dashboard de admin
        return RedirectResponse(url="/admin", status_code=302)
    else:
        # Credenciales inválidas: devolvemos la página de login con mensaje de error
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Usuario o contraseña inválidos."}
        )


@router.get("/logout")
def logout(request: Request):
    """
    Borra la sesión y redirige a login.
    """
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
