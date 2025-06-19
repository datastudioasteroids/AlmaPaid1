# app/routes/landing.py

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import requests
import os

from ..crud import (
    list_students,
    get_courses_for_student,
)
from ..deps import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- Variables de entorno de Mercado Pago ---
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
BASE_URL        = os.getenv("BASE_URL")  # e.g. "https://tu-dominio.com/"


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    """
    Muestra el formulario inicial de búsqueda.
    """
    return templates.TemplateResponse("landing.html", {"request": request})


@router.post("/create_preference", response_class=HTMLResponse)
def create_preference(
    request: Request,
    action: str = Form(...),        # "search" o "pay"
    term: str = Form(None),         # busqueda inicial
    student_id: int = Form(None),   # para el paso de pago
    db: Session = Depends(get_db)
):
    """
    Dos modos, dependiendo de `action`:
      - action=="search": busca alumno y renderiza datos + botón de pagar.
      - action=="pay": crea la preferencia de Mercado Pago y redirige.
    """
    # 1) MODO BÚSQUEDA
    if action == "search":
        if not term or not term.strip():
            return templates.TemplateResponse(
                "landing.html",
                {
                    "request": request,
                    "error": "Debes ingresar un término de búsqueda."
                }
            )

        q = term.strip().lower()
        alumnos = list_students(db)
        matches = []
        for s in alumnos:
            for campo in (s.name or "", s.dni or "", s.email or "", s.status or ""):
                if q in campo.lower():
                    matches.append(s)
                    break

        if not matches:
            return templates.TemplateResponse(
                "landing.html",
                {
                    "request": request,
                    "error": "No se encontraron alumnos con ese término."
                }
            )
        if len(matches) > 1:
            return templates.TemplateResponse(
                "landing.html",
                {
                    "request": request,
                    "multiple": matches
                }
            )

        # Encontramos exactamente uno
        alumno = matches[0]
        cursos = get_courses_for_student(db, alumno.id)
        subtotal = sum(c.monthly_fee for c in cursos)
        today = date.today()
        cutoff = date(2025, 6, 10)
        surcharge = 2000.0 if today >= cutoff else 0.0
        total = subtotal + surcharge

        return templates.TemplateResponse(
            "landing.html",
            {
                "request":  request,
                "student":  alumno,
                "courses":  [c.title for c in cursos],
                "subtotal": subtotal,
                "surcharge": surcharge,
                "total":    total
            }
        )

    # 2) MODO PAGO
    elif action == "pay":
        if not student_id:
            raise HTTPException(400, "Falta student_id para procesar el pago.")

        # Recalcular montos por seguridad
        alumno = next((s for s in list_students(db) if s.id == student_id), None)
        if not alumno:
            raise HTTPException(404, "Alumno no encontrado.")

        cursos = get_courses_for_student(db, alumno.id)
        subtotal = sum(c.monthly_fee for c in cursos)
        today = date.today()
        cutoff = date(2025, 6, 10)
        surcharge = 2000.0 if today >= cutoff else 0.0
        total = subtotal + surcharge

        # Preparamos el payload a Mercado Pago
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
        resp = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=payload,
            headers=headers
        )
        data = resp.json()

        if resp.status_code != 201 and data.get("error"):
            return templates.TemplateResponse(
                "landing.html",
                {
                    "request": request,
                    "error_mp": data
                }
            )

        link_mp = data.get("response", {}).get("init_point") or data.get("sandbox_init_point")
        return RedirectResponse(url=link_mp)

    else:
        raise HTTPException(400, "Acción inválida.")

