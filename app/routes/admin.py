# app/routes/admin.py
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List

from ..crud import (
    get_student, list_students, create_student, update_student, delete_student,
    get_course, list_courses, create_course, update_course, delete_course,
    list_enrollments, create_enrollment, delete_enrollment,
    calculate_due_for_student, calculate_next_month_due_for_student,
    get_payments_summary, search_students
)
from ..deps import get_db, ensure_admin
from ..schemas import (
    StudentCreate, StudentUpdate,
    CourseCreate, CourseUpdate,
    EnrollmentCreate,
    StudentOut
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


# — DASHBOARD —
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user

    total_students = len(list_students(db))
    total_courses  = len(list_courses(db))
    courses = list_courses(db)

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "total_students": total_students,
        "total_courses": total_courses,
        "courses": courses
    })


# — ESTUDIANTES — (gestión + AJAX-loaded list)
@router.get("/students", response_class=HTMLResponse)
def admin_manage_students(
    request: Request,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    courses = list_courses(db)
    return templates.TemplateResponse("admin/students.html", {
        "request": request,
        "courses": courses
    })


@router.post("/students", response_class=RedirectResponse)
def admin_post_student(
    id:     int    = Form(None),
    name:   str    = Form(...),
    email:  str    = Form(""),
    dni:    str    = Form(""),
    status: str    = Form("activo"),
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user

    if id:
        update_student(db, StudentUpdate(id=id, name=name, email=email, dni=dni, status=status))
    else:
        create_student(db, StudentCreate(name=name, email=email, dni=dni, status=status))

    return RedirectResponse(url="/admin/students", status_code=302)


@router.get("/students/delete/{student_id}", response_class=RedirectResponse)
def admin_delete_student(
    student_id: int,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    delete_student(db, student_id)
    return RedirectResponse(url="/admin/students", status_code=302)


# — CURSOS —
@router.get("/courses", response_class=HTMLResponse)
def admin_manage_courses(
    request: Request,
    edit_id: Optional[int] = None,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    courses = list_courses(db)
    course_to_edit = get_course(db, edit_id) if edit_id else None
    return templates.TemplateResponse("admin/courses.html", {
        "request": request,
        "courses": courses,
        "course_to_edit": course_to_edit
    })


@router.post("/courses", response_class=RedirectResponse)
def admin_post_course(
    id:          int     = Form(None),
    title:       str     = Form(...),
    monthly_fee: float   = Form(15000.0),
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user

    if id:
        update_course(db, CourseUpdate(id=id, title=title, monthly_fee=monthly_fee))
    else:
        create_course(db, CourseCreate(title=title, monthly_fee=monthly_fee))

    return RedirectResponse(url="/admin/courses", status_code=302)


@router.get("/courses/delete/{course_id}", response_class=RedirectResponse)
def admin_delete_course(
    course_id: int,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    delete_course(db, course_id)
    return RedirectResponse(url="/admin/courses", status_code=302)


# — INSCRIPCIONES —
@router.get("/enrollments", response_class=HTMLResponse)
def admin_manage_enrollments(
    request: Request,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    students    = list_students(db)
    courses     = list_courses(db)
    enrollments = list_enrollments(db)
    return templates.TemplateResponse("admin/enrollments.html", {
        "request": request,
        "students": students,
        "courses": courses,
        "enrollments": enrollments
    })


@router.post("/enrollments", response_class=RedirectResponse)
def admin_post_enrollment(
    student_id: int    = Form(...),
    course_id:  int    = Form(...),
    status:     str    = Form("activo"),
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    create_enrollment(db, EnrollmentCreate(student_id=student_id, course_id=course_id, status=status))
    return RedirectResponse(url="/admin/enrollments", status_code=302)


@router.get("/enrollments/delete/{enrollment_id}", response_class=RedirectResponse)
def admin_delete_enrollment(
    enrollment_id: int,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user
    delete_enrollment(db, enrollment_id)
    return RedirectResponse(url="/admin/enrollments", status_code=302)


# — FACTURACIÓN (PAGOS) —
@router.get("/invoices", response_class=HTMLResponse)
def admin_invoices(
    request: Request,
    user=Depends(ensure_admin),
    db: Session = Depends(get_db)
):
    if hasattr(user, "status_code"):
        return user

    students = list_students(db)
    dues_data = []
    for s in students:
        sub, rec, tot   = calculate_due_for_student(db, s.id)
        next_sub, next_rec, next_tot = calculate_next_month_due_for_student(db, s.id)
        dues_data.append({
            "student": s, "subtotal": sub, "recargo": rec, "total": tot,
            "next_sub": next_sub, "next_rec": next_rec, "next_total": next_tot
        })

    return templates.TemplateResponse("admin/invoices.html", {
        "request": request,
        "dues_data": dues_data
    })


# — API: Resumen de pagos para Chart.js —
@router.get("/api/payments-summary")
def api_payments_summary(
    course_id: Optional[int] = Query(None, description="Filtrar por ID de taller"),
    db: Session            = Depends(get_db),
    user=Depends(ensure_admin)
):
    if hasattr(user, "status_code"):
        return user
    return JSONResponse(content=get_payments_summary(db, course_id))


# — API: Búsqueda de estudiantes —
@router.get("/api/students", response_model=List[StudentOut])
def api_search_students(
    name:      Optional[str] = Query(None, description="Buscar por nombre"),
    course_id: Optional[int] = Query(None, description="Filtrar por ID de taller"),
    paid:      Optional[bool]= Query(None, description="True=pagado, False=no pagado"),
    db: Session            = Depends(get_db),
    user=Depends(ensure_admin)
):
    if hasattr(user, "status_code"):
        return user
    return search_students(db, name, course_id, paid)
