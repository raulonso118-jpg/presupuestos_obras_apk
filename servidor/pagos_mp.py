"""Mercado Pago: planes por versión (maestro/arquitecto) y consulta de pagos."""
import os
import uuid

import requests

# Precios en MXN: valores iniciales, ajustar antes de lanzar.
PLANES = {
    "maestro_mensual": {"version": "maestro", "precio": 99.0, "dias": 30, "titulo": "Presupuestos Obra Maestro - Mensual"},
    "maestro_anual": {"version": "maestro", "precio": 799.0, "dias": 365, "titulo": "Presupuestos Obra Maestro - Anual"},
    "arquitecto_mensual": {"version": "arquitecto", "precio": 199.0, "dias": 30, "titulo": "Presupuestos Obra Arquitecto - Mensual"},
    "arquitecto_anual": {"version": "arquitecto", "precio": 1599.0, "dias": 365, "titulo": "Presupuestos Obra Arquitecto - Anual"},
}


def _token():
    token = os.environ.get("MP_ACCESS_TOKEN", "").strip()
    if not token:
        raise ValueError("Falta MP_ACCESS_TOKEN en variables de entorno")
    return token


def _base_url():
    base = os.environ.get("APP_BASE_URL", "").strip()
    if not base:
        raise ValueError("Falta APP_BASE_URL en variables de entorno")
    return base.rstrip("/")


def obtener_plan(plan):
    clave = (plan or "").strip().lower()
    if clave not in PLANES:
        raise ValueError("Plan inválido. Usa: " + ", ".join(PLANES))
    return clave, PLANES[clave]


def crear_preferencia(email, plan):
    import mercadopago

    if not email or "@" not in email:
        raise ValueError("Email inválido")
    clave, datos = obtener_plan(plan)
    base = _base_url()
    referencia = f"orden_{clave}_{uuid.uuid4().hex[:16]}"
    body = {
        "items": [{"title": datos["titulo"], "quantity": 1, "currency_id": "MXN", "unit_price": datos["precio"]}],
        "payer": {"email": email},
        "external_reference": referencia,
        "notification_url": f"{base}/api/pagos/webhook",
        "back_urls": {"success": f"{base}/pago-exito", "failure": f"{base}/pago-fallo", "pending": f"{base}/pago-pendiente"},
        "auto_return": "approved",
        "metadata": {"email": email, "plan": clave},
    }
    resp = mercadopago.SDK(_token()).preference().create(body)
    data = resp.get("response", {}) if isinstance(resp, dict) else {}
    if not data.get("init_point") or not data.get("id"):
        raise ValueError(f"No se pudo crear preferencia MP: {resp}")
    return {
        "init_point": data["init_point"],
        "preference_id": data["id"],
        "external_reference": referencia,
        "plan": clave,
        "version": datos["version"],
        "precio": datos["precio"],
        "dias": datos["dias"],
    }


def _get(url, **kwargs):
    r = requests.get(url, headers={"Authorization": f"Bearer {_token()}"}, timeout=20, **kwargs)
    if r.status_code >= 400:
        raise ValueError(f"Error consultando Mercado Pago: {r.status_code}")
    return r.json()


def obtener_pago(payment_id):
    return _get(f"https://api.mercadopago.com/v1/payments/{payment_id}")


def extraer_data_pago(pago):
    metadata = pago.get("metadata") or {}
    plan = str(metadata.get("plan") or "").lower()
    if plan not in PLANES:
        raise ValueError("El pago no trae un plan válido")
    return {
        "payment_id": str(pago.get("id", "")),
        "status": str(pago.get("status", "")).lower(),
        "email": (pago.get("payer") or {}).get("email") or metadata.get("email"),
        "plan": plan,
        "version": PLANES[plan]["version"],
        "dias": PLANES[plan]["dias"],
        "external_reference": pago.get("external_reference"),
    }


def buscar_pago_aprobado(referencia):
    res = _get(
        "https://api.mercadopago.com/v1/payments/search",
        params={"external_reference": referencia, "status": "approved", "limit": 1},
    ).get("results") or []
    return str(res[0]["id"]) if res else None
