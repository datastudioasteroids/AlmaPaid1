# app/schemas.py

from pydantic import BaseModel
from datetime import date
from typing import Optional, List

# --- Student ---
class StudentBase(BaseModel):
    name: str
    email: Optional[str] = ""
    dni: Optional[str] = ""
    status: Optional[str] = "activo"

class StudentCreate(StudentBase):
    pass

class StudentUpdate(StudentBase):
    id: int
    last_paid_date: Optional[date] = None   # <-- Permitimos recibir/actualizar esta fecha

    class Config:
        from_attributes = True

class StudentOut(StudentBase):
    id: int
    last_paid_date: Optional[date]

    class Config:
        from_attributes = True


# --- Course ---
class CourseBase(BaseModel):
    title: str
    monthly_fee: float

class CourseCreate(CourseBase):
    pass

class CourseUpdate(CourseBase):
    id: int

    class Config:
        from_attributes = True

class CourseOut(CourseBase):
    id: int

    class Config:
        from_attributes = True


# --- Enrollment ---
class EnrollmentBase(BaseModel):
    student_id: int
    course_id: int
    status: Optional[str] = "activo"

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentOut(EnrollmentBase):
    id: int

    class Config:
        from_attributes = True


# --- Due (para mostrar totales en facturación) ---
class DueOut(BaseModel):
    subtotal: float
    recargo: float
    total: float

    class Config:
        from_attributes = True


# --- Payment ---
class PaymentBase(BaseModel):
    student_id: int
    amount: float
    paid_date: date

class PaymentCreate(PaymentBase):
    pass

class PaymentOut(PaymentBase):
    id: int

    class Config:
        from_attributes = True
