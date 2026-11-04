"""Licencias firmadas con HMAC: OBR<V>-YYYYMMDD-RAND6-FIRMA12 (V: M=Maestro, A=Arquitecto).

La firma y la fecha de expiración viajan dentro del código, por lo que la validación
no depende de que la BD sobreviva (Render sin disco persistente).
"""
import hashlib
import hmac
import os
import secrets
import string
from datetime import datetime, timedelta

import db

VERSIONES = {"M": "maestro", "A": "arquitecto"}
LETRA = {v: k for k, v in VERSIONES.items()}
# El arquitecto incluye todo lo del maestro
NIVEL = {"maestro": 1, "arquitecto": 2}


def _seed():
    return os.environ.get("LIC_SECRET_SEED", "")


def firma_habilitada():
    return _seed() not in ("", "CAMBIAR_EN_PRODUCCION")


def _firmar(cuerpo):
    return hmac.new(_seed().encode(), cuerpo.encode(), hashlib.sha256).hexdigest()[:12].upper()


def _dev_activo():
    return os.environ.get("DEV_MODE", "false").strip().lower() == "true"


def _dev_licencia():
    return os.environ.get("DEV_LICENCIA_MAESTRA", "").strip()


def generar_licencia(version, dias, email):
    """Devuelve el código firmado. Requiere LIC_SECRET_SEED real."""
    if version not in LETRA:
        raise ValueError("Versión inválida (maestro o arquitecto)")
    if not firma_habilitada():
        raise RuntimeError("Falta LIC_SECRET_SEED: no se pueden emitir licencias")
    inicio = datetime.now().date()
    expira = inicio + timedelta(days=int(dias))
    azar = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    cuerpo = f"OBR{LETRA[version]}-{expira.strftime('%Y%m%d')}-{azar}"
    codigo = f"{cuerpo}-{_firmar(cuerpo)}"
    db.guardar_licencia(codigo, email, version, inicio.isoformat(), expira.isoformat())
    return {"codigo": codigo, "version": version, "fecha_expiracion": expira.isoformat(), "dias": int(dias)}


def validar(codigo, version_requerida="maestro", dispositivo=None, ip=None):
    """Retorna (ok, mensaje, dias_restantes, version)."""
    codigo = (codigo or "").strip()
    if not codigo:
        return False, "Licencia vacía", 0, None

    if _dev_activo() and _dev_licencia() and hmac.compare_digest(codigo, _dev_licencia()):
        return True, "Licencia de desarrollo válida", 999, "arquitecto"

    partes = codigo.upper().split("-")
    if len(partes) != 4 or partes[0] not in ("OBRM", "OBRA") or not (len(partes[1]) == 8 and partes[1].isdigit()):
        return False, "Formato de licencia inválido", 0, None
    if not firma_habilitada():
        return False, "Licencias no disponibles: falta LIC_SECRET_SEED", 0, None
    if not hmac.compare_digest(_firmar("-".join(partes[:3])), partes[3]):
        return False, "Licencia modificada o corrupta (firma no válida)", 0, None
    try:
        expira = datetime.strptime(partes[1], "%Y%m%d").date()
    except ValueError:
        return False, "Licencia inválida", 0, None

    version = VERSIONES[partes[0][3]]
    dias = (expira - datetime.now().date()).days
    canonico = "-".join(partes)
    if dias < 0:
        resultado = ("expirada", f"Licencia expirada el {expira.isoformat()}", False)
    elif db.licencia_desactivada(canonico):
        resultado = ("desactivada", "Esta licencia ha sido desactivada", False)
    elif NIVEL[version] < NIVEL.get(version_requerida, 1):
        resultado = ("version_insuficiente", f"Tu licencia {version} no incluye la versión {version_requerida}", False)
    else:
        resultado = ("valida", f"Licencia {version} activa. Restan {dias} días.", True)

    db.registrar_validacion(canonico, dispositivo, resultado[0], ip)
    ok = resultado[2]
    return ok, resultado[1], dias if ok else 0, version
