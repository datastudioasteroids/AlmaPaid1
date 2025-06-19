# app/services/payments.py
import mercadopago
import datetime
from app.config import MP_ACCESS_TOKEN, BASE_URL

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

def calculate_total(subtotal: float) -> (float, float):
    today = datetime.date.today()
    cutoff = datetime.date(2025, 6, 10)
    recargo = 2000.0 if today >= cutoff else 0.0
    return recargo, subtotal + recargo

def create_payment_preference(
    student_id: int,
    student_name: str,
    total_amount: float
) -> str:
    # Si no hay ACCESS_TOKEN, no podemos seguir
    if not MP_ACCESS_TOKEN:
        raise ValueError("MP_ACCESS_TOKEN no configurado en app/config.py")

    ref_code = f"{student_id}-{datetime.date.today().isoformat()}"
    preference_data = {
        "items": [
            {
                "title": f"Pago de {student_name} (ID: {student_id})",
                "quantity": 1,
                "unit_price": float(total_amount),
            }
        ],
        "external_reference": ref_code,
        "back_urls": {
            "success": f"{BASE_URL}/payment_success?ref={ref_code}&id={student_id}",
            "failure": f"{BASE_URL}/payment_failure?ref={ref_code}&id={student_id}",
            "pending": f"{BASE_URL}/payment_pending?ref={ref_code}&id={student_id}",
        },
        "auto_return": "approved",
        # "sandbox_mode": True,  # descomentá si querés obligar sandbox
    }

    pref = sdk.preference().create(preference_data)
    resp = pref.get("response", {}) or {}

    # Para debug: imprimimos en stdout la respuesta completa
    print("=== MercadoPago preference response =====")
    print(resp)

    # Retornamos init_point (producción) o sandbox_init_point (sandbox)
    init = resp.get("init_point") or resp.get("sandbox_init_point")
    return init or ""
