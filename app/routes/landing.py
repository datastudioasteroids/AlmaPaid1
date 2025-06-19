# app/routes/landing.py

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import requests
import os

from ..crud import (
    list_students,            # Usar la función de crud en lugar de models.Student
    get_courses_for_student,
    create_payment,
    mark_student_paid,
)
from ..deps import get_db
from ..schemas import PaymentCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- Variables de entorno de Mercado Pago ---
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
BASE_URL        = os.getenv("BASE_URL")  # Ejemplo: "https://tu-dominio.com/"


# -----------------------------------------------------------
# 1) GET "/" → Muestra el formulario de búsqueda (landing page)
@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request
        }
    )


# -----------------------------------------------------------
# 2) POST "/create_preference" → Busca al estudiante y redirige al link de Mercado Pago
@router.post("/create_preference", response_class=HTMLResponse)
def create_preference(
    request: Request,
    term: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    - Recibe un término de búsqueda (nombre, correo, DNI o estado).
    - Filtra la lista de estudiantes en la base.
    - Si hay exactamente uno, calcula el monto, crea la preferencia en Mercado Pago y redirige.
    - Si no hay o hay varios, vuelve a mostrar landing.html con el mensaje apropiado.
    """
    term_l = term.strip().lower()

    # 2.1) Listar todos los estudiantes con crud.list_students()
    alumnos = list_students(db)
    matches = []
    for s in alumnos:
        # Revisar si term_l está en alguno de los campos relevantes
        for campo in (s.name or "", s.dni or "", s.email or "", s.status or ""):
            if term_l in campo.lower():
                matches.append(s)
                break

    # 2.2) Si no hay coincidencias
    if not matches:
        return templates.TemplateResponse(
            "landing.html",
            {
                "request": request,
                "error": "No se encontraron alumnos con ese término."
            }
        )

    # 2.3) Si hay más de una coincidencia
    if len(matches) > 1:
        return templates.TemplateResponse(
            "landing.html",
            {
                "request": request,
                "multiple": matches
            }
        )

    # 2.4) Solo hay un estudiante: calcular monto a pagar
    alumno = matches[0]
    cursos = get_courses_for_student(db, alumno.id)  # Función de crud que devuelve objetos Course
    subtotal = sum(c.monthly_fee for c in cursos)
    today = date.today()
    cutoff = date(2025, 6, 10)
    surcharge = 2000.0 if today >= cutoff else 0.0
    total = subtotal + surcharge

    # 2.5) Preparar payload de Mercado Pago
    payload = {
        "items": [
            {
                "title": f"Pago cuota {today.isoformat()} - {alumno.name}",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": total
            }
        ],
        "external_reference": f"{alumno.id}-{today.isoformat()}",
        "back_urls": {
            "success": f"{BASE_URL}payment/success",
            "failure": f"{BASE_URL}payment/failed",
            "pending": f"{BASE_URL}payment/pending"
        },
        "auto_return": "approved"
    }

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    r = requests.post(
        "https://api.mercadopago.com/checkout/preferences",
        json=payload,
        headers=headers
    )
    data = r.json()

    # 2.6) Si Mercado Pago devolvió error
    if r.status_code != 201 and data.get("error"):
        return templates.TemplateResponse(
            "landing.html",
            {
                "request": request,
                "error_mp": data
            }
        )

    # 2.7) Obtener el init_point y redirigir al usuario
    link_mp = data.get("response", {}).get("init_point") or data.get("sandbox_init_point")
    return RedirectResponse(url=link_mp)


# -----------------------------------------------------------
# 3) GET "/payment/success" → Callback de pago exitoso
@router.get("/payment/success", response_class=HTMLResponse)
def payment_success(
    request: Request,
    paid: str = None,
    ref: str = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint invocado por Mercado Pago cuando el pago es aprobado.
    Se espera: /payment/success?paid=true&ref=<studentId>-<fecha>
    """
    # 3.1) Validar parámetros
    if not paid or paid.lower() != "true" or not ref:
        return templates.TemplateResponse(
            "payment_failed.html",
            {"request": request}
        )

    # 3.2) Extraer student_id y fecha de la referencia
    try:
        student_id_str, fecha_str = ref.split("-", 1)
        student_id = int(student_id_str)
        paid_date = date.fromisoformat(fecha_str)
    except Exception:
        return templates.TemplateResponse(
            "payment_failed.html",
            {
                "request": request,
                "error": "Referencia inválida."
            }
        )

    # 3.3) Recalcular el monto por seguridad
    cursos = get_courses_for_student(db, student_id)
    subtotal = sum(c.monthly_fee for c in cursos)
    surcharge = 2000.0 if paid_date >= date(2025, 6, 10) else 0.0
    total = subtotal + surcharge

    # 3.4) Registrar pago en la tabla payments y actualizar last_paid_date del estudiante
    payment_data = PaymentCreate(
        student_id = student_id,
        amount     = total,
        paid_date  = paid_date
    )
    create_payment(db, payment_data)
    mark_student_paid(db, student_id, paid_date)

    # 3.5) Renderizar página de éxito
    return templates.TemplateResponse(
        "payment_success.html",
        {
            "request": request,
            "student_id": student_id,
            "paid_date": paid_date,
            "amount": total
        }
    )


# -----------------------------------------------------------
# 4) GET "/payment/failed" → Pago fallido
@router.get("/payment/failed", response_class=HTMLResponse)
def payment_failed(request: Request):
    return templates.TemplateResponse(
        "payment_failed.html",
        {"request": request}
    )


# -----------------------------------------------------------
# 5) GET "/payment/pending" → Pago pendiente (opcional)
@router.get("/payment/pending", response_class=HTMLResponse)
def payment_pending(request: Request):
    return templates.TemplateResponse(
        "payment_pending.html",
        {"request": request}
    )

