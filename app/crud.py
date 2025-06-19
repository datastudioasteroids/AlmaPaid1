from datetime import date
from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional, List, Dict
from sqlalchemy import func, or_
from .models import Student, Enrollment, Course

# -------- ESTUDIANTES --------
def get_student(db: Session, student_id: int):
    return db.query(models.Student).filter(models.Student.id == student_id).first()

def list_students(db: Session):
    return db.query(models.Student).all()

def create_student(db: Session, data: schemas.StudentCreate):
    s = models.Student(
        name=data.name,
        email=data.email,
        dni=data.dni,
        status=data.status
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def update_student(db: Session, data: schemas.StudentUpdate):
    s = get_student(db, data.id)
    if s:
        s.name           = data.name
        s.email          = data.email
        s.dni            = data.dni
        s.status         = data.status
        s.last_paid_date = data.last_paid_date  # <-- Consideramos la fecha de pago si se envía
        db.commit()
        db.refresh(s)
    return s

def delete_student(db: Session, student_id: int):
    s = get_student(db, student_id)
    if s:
        db.delete(s)
        db.commit()
        return True
    return False


# -------- CURSOS --------
def get_course(db: Session, course_id: int):
    return db.query(models.Course).filter(models.Course.id == course_id).first()

def list_courses(db: Session):
    return db.query(models.Course).all()

def create_course(db: Session, data: schemas.CourseCreate):
    c = models.Course(
        title=data.title,
        monthly_fee=data.monthly_fee
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def update_course(db: Session, data: schemas.CourseUpdate):
    c = get_course(db, data.id)
    if c:
        c.title       = data.title
        c.monthly_fee = data.monthly_fee
        db.commit()
        db.refresh(c)
    return c

def delete_course(db: Session, course_id: int):
    c = get_course(db, course_id)
    if c:
        db.delete(c)
        db.commit()
        return True
    return False


# -------- INSCRIPCIONES --------
def get_enrollment(db: Session, enrollment_id: int):
    return db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()

def list_enrollments(db: Session):
    return db.query(models.Enrollment).all()

def create_enrollment(db: Session, data: schemas.EnrollmentCreate):
    e = models.Enrollment(
        student_id=data.student_id,
        course_id=data.course_id,
        status=data.status
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e

def delete_enrollment(db: Session, enrollment_id: int):
    e = get_enrollment(db, enrollment_id)
    if e:
        db.delete(e)
        db.commit()
        return True
    return False

# — NUEVA FUNCIÓN: Obtener cursos de un estudiante —
def get_courses_for_student(db: Session, student_id: int):
    """
    Devuelve una lista de objetos Course para el estudiante dado,
    buscando en la tabla Enrollment los cursos asociados.
    """
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == student_id
    ).all()
    return [en.course for en in enrollments]


# -------- FACTURACIÓN (Due) --------
def calculate_due_for_student(db: Session, student_id: int):
    s = get_student(db, student_id)
    if not s:
        return 0.0, 0.0, 0.0
    fees = [en.course.monthly_fee for en in s.enrollments]
    subtotal = sum(fees)
    today = date.today()
    cutoff = date(2025, 6, 10)
    surcharge = 2000.0 if today >= cutoff else 0.0
    total = subtotal + surcharge
    return subtotal, surcharge, total

def calculate_next_month_due_for_student(db: Session, student_id: int):
    # (Supone misma lógica para el próximo mes, igual que el mes actual)
    return calculate_due_for_student(db, student_id)


# -------- PAYMENTS (nuevo) --------
def create_payment(db: Session, data: schemas.PaymentCreate):
    """
    Crea un registro en la tabla 'payments' con un pago nuevo.
    """
    p = models.Payment(
        student_id = data.student_id,
        amount     = data.amount,
        paid_date  = data.paid_date
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

def mark_student_paid(db: Session, student_id: int, paid_date: date):
    """
    Actualiza el campo 'last_paid_date' del estudiante para indicar que pagó.
    """
    s = get_student(db, student_id)
    if s:
        s.last_paid_date = paid_date
        db.commit()
        db.refresh(s)
    return s

def get_payments_summary(db: Session, course_id: Optional[int] = None) -> Dict[str, int]:
    """
    Devuelve conteos de estudiantes pagados vs no pagados.
    Si se pasa course_id, filtra sólo dentro de ese taller.
    """
    q = db.query(Student)
    if course_id is not None:
        q = q.join(Enrollment).filter(Enrollment.course_id == course_id)

    paid_count   = q.filter(Student.last_paid_date.isnot(None)).distinct().count()
    unpaid_count = q.filter(Student.last_paid_date.is_(None)).distinct().count()
    return {"paid": paid_count, "unpaid": unpaid_count}


def search_students(
    db: Session,
    name: Optional[str]        = None,
    course_id: Optional[int]   = None,
    paid: Optional[bool]       = None
) -> List[Student]:
    """
    Busca estudiantes por nombre (ILIKE), taller y estado de pago.
    """
    q = db.query(Student)
    if name:
        q = q.filter(Student.name.ilike(f"%{name}%"))
    if course_id:
        q = q.join(Enrollment).filter(Enrollment.course_id == course_id)
    if paid is True:
        q = q.filter(Student.last_paid_date.isnot(None))
    elif paid is False:
        q = q.filter(Student.last_paid_date.is_(None))

    return q.order_by(Student.name).all()
